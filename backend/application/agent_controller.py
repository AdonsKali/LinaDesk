import json
from typing import AsyncGenerator, List
from numpy import datetime64
from backend.core.schemas.client_schema import (
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
from backend.application.tool_manager import ToolManager
from utils.logger import logger

log = logger.get(__name__)


class AgentController:
    def __init__(self, inference: InferenceABC, 
                 tool_manager: ToolManager, 
                 agent: Agent, 
                 rag_service: RAGABC,
                 ):

        self.inference = inference
        self.tool_manager = tool_manager
        self.agent = agent
        self.rag_service = rag_service

        self.running = False
        self.last_user_target = ""
        
        self.enable_rag = self.agent.rag
        self.max_steps = self.agent.max_steps


    def reset(self):
        self.agent.reset()
        self.running = False

    def _check_and_save_conversation(self, prompt: str):
        """
        Проверяет, нужно ли сохранить диалог в RAG, и сохраняет если нужно.
        """
        if not (self.enable_rag and self.rag_service):
            return False
            
        if hasattr(self.rag_service, 'should_remember_conversation'):
            should_remember = self.rag_service.should_remember_conversation(prompt, threshold=0.75)
            if should_remember:
                history = self.agent.history
                if history and len(history) >= 2:
                    last_user_message = history[-2]
                    last_assistant_message = history[-1]
                    
                    interaction_content = f"User: {last_user_message.content}\nAssistant: {last_assistant_message.content}"
                    
                    doc_id = self.rag_service.add_document(
                        content=interaction_content,
                        metadata={
                            "type": "qa_pair",
                            "source": "agent_controller",
                            "user_query": last_user_message.content[:100],
                            "remember_command": prompt[:100],
                            "timestamp": str(datetime64('now'))
                        }
                    )
                    
                    self.rag_service.save_index()
                    log.info(f"Saved conversation as document {doc_id} due to remember command")
                    return True
        return False

    async def response(self, prompt: str) -> AsyncGenerator:

        if not prompt.strip():
            yield ClientError(type="error", message="Empty prompt")
            return

        rag_context = ""
        if self.enable_rag and self.rag_service:
            rag_results = self.rag_service.search(prompt, top_k=3, similarity_threshold=0.33)
            if rag_results:
                rag_context = "\n".join([f"<relevant_info>: {result['content']}</relevant_info>" for result in rag_results])
                
        self.agent.add_message(
            MessageHistory(role="user", content=f"Context for user query: {rag_context}\n{prompt}")
        )
        original_prompt = prompt
  
        async for event in self._run_agent_loop():
            if isinstance(event, ClientComplete) and self.enable_rag and self.rag_service:
                self._check_and_save_conversation(original_prompt)
            yield event


    async def _run_agent_loop(self):
        if self.running:
            return

        self.running = True
        previous_tool_calls = []

        try:
            for step in range(self.max_steps):
                history: List[MessageHistory] = self.agent.history
                assistant_text = ""
                tool_calls: List[ToolCall] = []

                tool_descriptions = self.tool_manager.get_llm_descriptions_by_names(
                    self.agent.tools
                )

                async for event in self.inference.stream(
                    prompt=history,
                    tools=tool_descriptions,
                    generation_params=self.agent.generation_params,
                ): #type: ignore
                    if isinstance(event, TokenChunk):
                        assistant_text += event.content
                        yield TokenChunk(
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

                if assistant_text.strip():
                    self.agent.add_message(
                        MessageHistory(
                            role="assistant",
                            content=assistant_text
                        )
                    )

                if not tool_calls:
                    yield ClientComplete(type="complete")
                    return
                
                current_tool_calls = [(tc.name, tuple(sorted(tc.arguments.items()))) for tc in tool_calls]
                
                if current_tool_calls == previous_tool_calls:
                    log.warning(f"Detected repeated tool calls: {current_tool_calls}, stopping")
                    yield ClientError(
                        type="error",
                        message="Stopping to prevent infinite loop: detected repeated tool calls"
                    )
                    return
                
                previous_tool_calls = current_tool_calls
                
                for tool_call in tool_calls:
                    try:
                        log.debug(f"Executing tool: {tool_call.name} with args: {tool_call.arguments}")
                        yield ClientToolCall(type="tool_call", data={'name': tool_call.name, 'arguments': tool_call.arguments})
                    
                        result = self.tool_manager.execute(
                            tool_call.name,
                            **tool_call.arguments
                        )
                        agent_prompt = f"""Check the logic and execution status of the tool to see if the goal was achieved '{self.last_user_target}'
                        If yes, inform the user; if no, continue pursuing the goal. If the goal can no longer be achieved, inform the user and offer alternatives.\n"""
                        log.info(f"Tool call results: status={result.status}, msg={result.msg}")
                        yield ClientToolCall(type='tool_call_complete', data=None)
                        self.last_user_target = self.agent.get_last().content
                        self.agent.add_message(
                            MessageHistory(
                                role="assistant",
                                content=agent_prompt + self._format_tool_result(tool_call.name, result)
                            )
                        )
                    except Exception as e:
                        error_msg = f"Tool execution error: {str(e)}"
                        log.error(error_msg)
                        self.agent.add_message(
                            MessageHistory(
                                role="assistant",
                                content="<tool_result>\nTool: {tool_call.name}\nStatus: ERROR\nMessage: {str(e)}\n</tool_result>"
                            )
                        )
                        yield ClientError(type="error", message=error_msg)
                        return

        finally:
            log.info(self.agent.history)
            self.running = False

    def _format_tool_result(self, tool_name: str, result) -> str:
        """Форматирует результат инструмента в строку для модели"""
        if hasattr(result, 'status'):
            if result.status == 'ok':
                output = f"<tool_result>\nTool: {tool_name}\nStatus: SUCCESS\n"
                if result.msg:
                    output += f"Message: {result.msg}\n"
                if result.data:
                    output += f"Data: {json.dumps(result.data, ensure_ascii=False)[:500]}\n"
                output += "</tool_result>"
                return output
            else:
                return f"<tool_result>\nTool: {tool_name}\nStatus: ERROR\nMessage: {result.msg or 'Unknown error'}\n</tool_result>"
        return f"<tool_result>\nTool: {tool_name}\nResult: {str(result)}\n</tool_result>"