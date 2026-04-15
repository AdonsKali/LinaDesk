import json
from typing import AsyncGenerator, List, Union

from backend.application.interfaces.inferenceABC import InferenceABC
import asyncio

from backend.core.schemas.streaming import (
    TokenChunk,
    ToolCallChunk,
    StreamComplete,
    StreamError,
)
from backend.core.schemas.message_schema import MessageHistory
from backend.core.schemas.tool_schema import ToolCall
from .functions import tools
from llama_cpp import Llama


class LlamaCppInference(InferenceABC):

    def __init__(self, model_path: str, n_ctx: int, n_threads: int, n_gpu_layers: int):

        self.answer = ""
        self.token_interval = 0.01

        self.llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_threads=n_threads,
            n_gpu_layers=n_gpu_layers,
            verbose=False,
            flash_attn=True,
            offload_kqv=True,
            last_n_tokens_size=0,
        )

    def generate(self, prompt: List[MessageHistory]) -> str:
        return "Generate method is not realized yet"

    async def stream(
        self,
        prompt: List[MessageHistory]
    ) -> AsyncGenerator:

        try:

            response = self.llm.create_chat_completion(
                messages=prompt, # type: ignore
                tools=tools,  # type: ignore
                stream=True,
                tool_choice="auto",
                max_tokens=2048,
                temperature=0.7,
                top_p=0.8,
                top_k=20,
                min_p=0.0,
            )

            tool_buffer = ""
            in_tool_block = False

            for chunk in response:
                delta = chunk["choices"][0].get("delta", {}) or {} # type: ignore
                text = delta.get("content")

                if not text:
                    continue

                if "<tool_call>" in text:

                    before = text.split("<tool_call>")[0]

                    if before:
                        yield TokenChunk(
                            type="token",
                            content=before
                        )

                    in_tool_block = True
                    tool_buffer = text.split("<tool_call>", 1)[1]
                    continue

                if in_tool_block:
                    if "</tool_call>" in text:

                        part, remainder = text.split("</tool_call>", 1)
                        tool_buffer += part
                        in_tool_block = False

                        parsed = json.loads(tool_buffer)

                        yield ToolCallChunk(
                            type="tool_call",
                            tool=ToolCall(
                                name=parsed["name"],
                                arguments=parsed.get("arguments", {})
                            )
                        )

                        tool_buffer = ""

                        if remainder:
                            yield TokenChunk(
                                type="token",
                                content=remainder
                            )

                    else:
                        tool_buffer += text
                    continue

                yield TokenChunk(
                    type="token",
                    content=text
                )

                await asyncio.sleep(self.token_interval)

            yield StreamComplete(type="complete")

        except Exception as e:
            yield StreamError(
                type="error",
                message=str(e)
            )