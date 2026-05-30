from typing import AsyncGenerator, List, Dict
from backend.application.interfaces.inferenceABC import InferenceABC
import asyncio
import json
from backend.core.schemas.streaming import (
    TokenChunk,
    ToolCallChunk,
    StreamComplete,
    StreamError,
)
from backend.core.schemas.tool_schema import ToolCall
from llama_cpp import Llama
from llama_cpp.llama_chat_format import Gemma4ChatHandler
from .gemma4_parser import parse_gemma4_native_tool_calls


class LlamaCppInference(InferenceABC):

    def __init__(self, model_path: str, 
                n_ctx: int,
                n_threads: int,
                n_gpu_layers: int | str,
                clip_model_path: str):

        self.answer = ""
        self.token_interval = 0.01

        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers, #type: ignore
            chat_handler=Gemma4ChatHandler(
                clip_model_path=clip_model_path, 
                enable_thinking=False
            ),
            verbose=False,
            flash_attn=True,
            offload_kqv=True,
            last_n_tokens_size=0,
        )

    def generate(self, prompt: List[Dict]) -> str:
        return "Generate method is not realized yet"
    
    async def stream(
        self,
        prompt: List[Dict],
        tools: List[dict],
        generation_params: dict,
    ) -> AsyncGenerator:
        """
        Стриминг с буферизацией и фильтрацией tool_call блоков.
        """
        try:
            response = self.llm.create_chat_completion(
                messages=prompt, #type: ignore
                tools=tools if tools else None, #type: ignore
                stream=True,
                tool_choice="auto",
                **generation_params
            )
            
            full_text = ""
            in_tool_block = False
            tool_block_buffer = ""
            
            for chunk in response:
                delta = chunk["choices"][0].get("delta", {}) #type: ignore
                
                if delta.get("content"):
                    text = delta.get("content", "") #type: ignore
                    full_text += text #type: ignore
                    
                    # Отслеживаем начало и конец tool_call блока
                    if "<|tool_call>" in text: #type: ignore
                        in_tool_block = True
                        # Отправляем текст ДО tool_call
                        before = text.split("<|tool_call>")[0] #type: ignore
                        if before:
                            yield TokenChunk(type="token", content=before)
                        tool_block_buffer = text.split("<|tool_call>", 1)[1] #type: ignore
                        continue
                    
                    if in_tool_block:
                        tool_block_buffer += text #type: ignore
                        if "<tool_call|>" in text: #type: ignore
                            # Конец tool_call блока - НЕ отправляем клиенту
                            in_tool_block = False
                            tool_block_buffer = ""
                        continue
                    
                    # Обычный текст вне tool_call - отправляем
                    yield TokenChunk(type="token", content=text) #type: ignore
                    await asyncio.sleep(self.token_interval)
                
                if chunk.get("choices")[0].get("finish_reason"): #type: ignore
                    # Парсим tool calls из собранного текста
                    _, tool_calls = parse_gemma4_native_tool_calls(full_text)
                    
                    if tool_calls:
                        for tool_call in tool_calls:
                            args = json.loads(tool_call["function"]["arguments"])
                            yield ToolCallChunk(
                                type="tool_call",
                                tool=ToolCall(
                                    name=tool_call["function"]["name"],
                                    arguments=args
                                )
                            )
                    
                    yield StreamComplete(type="complete")
                    return
            
        except Exception as e:
            print(f"Stream error: {e}")
            yield StreamError(type="error", message=str(e))