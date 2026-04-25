import json
from typing import AsyncGenerator, List
from backend.core.schemas.client_schema import (
    ClientToken,
    ClientComplete,
    ClientError,
    ClientToolCall
)
from backend.core.schemas.streaming import (
    TokenChunk,
    ToolCallChunk,
    StreamComplete,
    StreamError,
)
from backend.core.schemas.message_schema import MessageHistory
from backend.application.interfaces.inferenceABC import InferenceABC
from backend.core.agent.agent import Agent
from backend.core.schemas.tool_schema import ToolCall
from backend.application.interfaces.rag_abc import RAGABC
from backend.application.interfaces.tool_managerABC import ToolManagerABC
from logger import log


class AgentController:
    def __init__(self, inference: InferenceABC, 
                 tool_manager: ToolManagerABC, 
                 agent: Agent, 
                 rag_service: RAGABC,
                 enable_rag=True
                 ):

        self.inference = inference
        self.tool_manager = tool_manager
        self.agent = agent
        self.rag_service = rag_service
        self.enable_rag = enable_rag

        self.running = False
        self.max_steps = 10


    def reset(self):
        self.agent.reset()
        self.running = False

    async def response(self, prompt: str) -> AsyncGenerator:

        if not prompt.strip():
            yield ClientError(type="error", message="Empty prompt")
            return

        rag_context = ""
        if self.enable_rag and self.rag_service:
            rag_results = self.rag_service.search(prompt, top_k=3)
            if rag_results:
                rag_context = "\n".join([f"Relevant info: {result['content']} (confidence: {result['score']:.2f})" for result in rag_results])
                
        self.agent.add_message(
            MessageHistory(role="user", content=f"Context for user query: {rag_context}\n{prompt}")
        )
        
        if self.enable_rag and self.rag_service:
            self.rag_service.add_document(
                content=prompt,
                metadata={
                    "type": "user_query",
                    "source": "agent_controller"
                }
            )
        
        async for event in self._run_agent_loop():
            if isinstance(event, ClientComplete) and self.enable_rag and self.rag_service:
                history = self.agent.get_history()
                
                if history and len(history) >= 2:
                    last_user_message = history[-2]
                    last_assistant_message = history[-1]
                    
                    interaction_content = f"User: {last_user_message.content}\nAssistant: {last_assistant_message.content}"
                    self.rag_service.add_document(
                        content=interaction_content,
                        metadata={
                            "type": "qa_pair",
                            "source": "agent_controller",
                            "user_query": last_user_message.content[:100]
                        }
                    )
                
                    self.rag_service.save_index()
            
            yield event


    async def _run_agent_loop(self):
        if self.running:
            return

        self.running = True
        previous_tool_calls = []

        try:
            for step in range(self.max_steps):
                history: List[MessageHistory] = self.agent.get_history()
                assistant_text = ""
                tool_calls: List[ToolCall] = []

                async for event in self.inference.stream(history): #type: ignore
                    if isinstance(event, TokenChunk):
                        assistant_text += event.content
                        yield ClientToken(
                            type="token",
                            content=event.content
                        )
                    elif isinstance(event, ToolCallChunk):
                        tool_calls.append(event.tool)
                        break

                    elif isinstance(event, StreamComplete):
                        if assistant_text.strip():
                            self.agent.add_message(
                            MessageHistory(
                                role="assistant",
                                content=assistant_text
                                )
                            )

                        yield ClientComplete(type="complete")
                        return
                    elif isinstance(event, StreamError):

                        yield ClientError(
                            type="error",
                            message=event.message
                        )
                        return

                if not tool_calls:
                    if assistant_text.strip():
                        self.agent.add_message(
                            MessageHistory(
                                role="assistant",
                                content=assistant_text
                            )
                        )

                    yield ClientComplete(type="complete")
                    return

                current_tool_calls = [(tc.name, tuple(sorted(tc.arguments.items()))) for tc in tool_calls]
                
                if current_tool_calls == previous_tool_calls:
                    log(f"Detected repeated tool calls: {current_tool_calls}, stopping to prevent infinite loop", 'warning', __name__)
                    yield ClientError(
                        type="error",
                        message="Stopping to prevent infinite loop: detected repeated tool calls"
                    )
                    return
                
                previous_tool_calls = current_tool_calls
                for tool_call in tool_calls:
                    try:
                        log(tool_call, 'debug', __name__)
                        yield ClientToolCall(type="tool_call", data={'name':  tool_call.name, 'arguments': tool_call.arguments})
                        result = self.tool_manager.execute(
                            tool_call.name,
                            tool_call.arguments
                        )

                    except Exception as e:
                        result = {"error": str(e)}
                    
                    log(f"Results: {result}", 'debug', __name__)
                    formatted_result = f"Tool '{tool_call.name}' completed. Result: {json.dumps(result, ensure_ascii=False)}"
                    self.agent.add_message(
                        MessageHistory(
                            role="assistant",
                            content=formatted_result
                        )
                    )
        finally:
            self.running = False