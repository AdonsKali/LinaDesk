import json
from typing import AsyncGenerator, List, Union
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
from logger import log


class AgentController:
    def __init__(self, inference: InferenceABC, tool_manager, agent: Agent, enable_rag=True):

        self.inference = inference
        self.tool_manager = tool_manager
        self.agent = agent
        # self.rag_service = rag_service
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
        
        # if self.enable_rag and self.rag_service:
        #     try:
        #         context_str = self.rag_service.get_context_for_query(prompt)
        #         if context_str:
        #             self.agent.add_message(
        #                 MessageHistory(
        #                     role="assistant",
        #                     content=f"Additional context for this conversation: {context_str}"
        #                 )
        #             )
        #     except Exception as e:
        #         log(f"RAG search error: {str(e)}", 'warning', __name__)

        self.agent.add_message(
            MessageHistory(role="user", content=prompt)
        )

        print(self.agent.history)

        async for event in self._run_agent_loop():
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
                            # if self.enable_rag and self.rag_service:
                            #     try:
                            #         # Save the full conversation context
                            #         user_messages = [msg.content for msg in history if msg.role == "user"]
                            #         if user_messages:
                            #             latest_user_msg = user_messages[-1]
                            #             self.rag_service.add_conversation(latest_user_msg, assistant_text)
                            #     except Exception as e:
                            #         log(f"RAG memory save error: {str(e)}", 'warning', __name__)

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

                        # # Save the conversation to RAG memory for future retrieval
                        # if self.enable_rag and self.rag_service:
                        #     try:
                        #         # Save the full conversation context
                        #         user_messages = [msg.content for msg in history if msg.role == "user"]
                        #         if user_messages:
                        #             latest_user_msg = user_messages[-1]
                        #             self.rag_service.add_conversation(latest_user_msg, assistant_text)
                        #     except Exception as e:
                        #         log(f"RAG memory save error: {str(e)}", 'warning', __name__)

                    yield ClientComplete(type="complete")
                    return

                current_tool_calls = [(tc.name, tuple(sorted(tc.arguments.items()))) for tc in tool_calls]
                
                # If we're calling the same tools with the same arguments as the previous step, break the loop
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
                    
                    # Format the result with explicit status indicator for the LLM
                    formatted_result = f"Tool '{tool_call.name}' completed. Result: {json.dumps(result, ensure_ascii=False)}"
                    
                    # Add the tool call result to history with clear status
                    self.agent.add_message(
                        MessageHistory(
                            role="assistant",
                            content=formatted_result
                        )
                    )

                    # # Save tool execution results to RAG memory for future retrieval
                    # if self.enable_rag and self.rag_service:
                    #     try:
                    #         self.rag_service.add_document(
                    #             f"Tool {tool_call.name} executed with result: {str(result)}", 
                    #             doc_type="tool_execution",
                    #             metadata={
                    #                 "tool_name": tool_call.name,
                    #                 "arguments": tool_call.arguments,
                    #                 "result": result
                    #             }
                    #         )
                    #     except Exception as e:
                    #         log(f"RAG memory save error: {str(e)}", 'warning', __name__)

        finally:
            self.running = False