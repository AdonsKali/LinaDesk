import json
from paths import MODELS
import asyncio
from .functions import tools
import ast
from ...logger import logger
from llama_cpp import Llama


class Inference():
    def __init__(self):
        super(Inference, self).__init__()
        self.answer = ""
        self.token_interval: float = 0.01
    
        self.llm: Llama = Llama(
            model_path=f"{MODELS}/model.gguf",
            n_ctx=4096,
            n_threads=6,
            n_gpu_layers=15,
            verbose=False,
            flash_attn=True,
            offload_kqv=True,
            last_n_tokens_size=0,
        )

    async def generate(self, prompt: dict):
        try:
            self.answer = ""
            response = self.llm.create_chat_completion(
                messages=prompt,
                max_tokens=2048,
                stream=True,
                frequency_penalty=0.2,
                tool_choice="auto",
                tools=tools
            )
            tool_buffer = ""
            in_tool_block = False

            for chunk in response:
                delta = chunk["choices"][0].get("delta", {}) or {}
                if not delta:
                    delta = chunk["choices"][0].get("text", "")
                
                if "content" in delta:
                    new_text = delta["content"]
                else:
                    continue
                
                if "<tool_call>" in new_text:
                    in_tool_block = True
                    before_tool = new_text.split("<tool_call>")[0]
                    if before_tool:
                        self.answer += before_tool
                        yield {"type": "token", "content": before_tool}
                        await asyncio.sleep(0.01) 
                    
                    part = new_text.split("<tool_call>", 1)[1]
                    tool_buffer += part
                    continue

                if in_tool_block:
                    if "</tool_call>" in new_text:
                        part, remainder = new_text.split("</tool_call>", 1)
                        tool_buffer += part
                        in_tool_block = False
                        try:
                            json_str = tool_buffer.strip()
                            try:
                                parsed = ast.literal_eval(json_str)
                            except Exception as e:
                                json_str = json_str.replace("'", '"')
                                parsed = json.loads(json_str)
                                
                            valid_json = json.dumps(parsed, ensure_ascii=False)
                            yield {"type": "tool_calls", "data": [valid_json]}
                            await asyncio.sleep(self.token_interval) 

                            tool_buffer = ""
                            if remainder.strip():
                                self.answer += remainder
                                yield {"type": "token", "content": remainder}
                                await asyncio.sleep(self.token_interval) 
                                
                        except Exception as e:
                            logger.error(f"Error parsing tool_call: {e} | raw: {tool_buffer}")
                            tool_buffer = ""
                            if remainder.strip():
                                self.answer += remainder
                                yield {"type": "token", "content": remainder}
                                await asyncio.sleep(self.token_interval) 
                                
                        continue
                    else:
                        tool_buffer += new_text
                        continue

                if new_text:
                    self.answer += new_text
                    yield {"type": "token", "content": new_text}
                    await asyncio.sleep(self.token_interval) 

            yield {"type": "end", "content": ""}
            await asyncio.sleep(self.token_interval) 

        except Exception as e:
            yield {"type": "error", "content": f"{e}"}