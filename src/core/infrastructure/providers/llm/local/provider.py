"""llama-cpp-python adapter: one native worker and one inference at a time."""
import asyncio
import importlib
import inspect
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import aclosing
from pathlib import Path
from src.core.application.ports.llm_port import LLMPort, ChatResponse
from .native_runtime import register_runtime_directories, verify_cuda_library


class _VisibleText:
    """Keep partial delimiters between chunks; suppress model thinking."""
    def __init__(self):
        self.pending = ""
        self.end = None

    def feed(self, text, final=False):
        self.pending += text
        output = ""
        starts = {"<think>": "</think>", "<|channel>": "<channel|>"}
        while self.pending:
            markers = (self.end,) if self.end else tuple(starts)
            found = [(self.pending.find(m), m) for m in markers if m in self.pending]
            if found:
                index, marker = min(found)
                if not self.end:
                    output += self.pending[:index]
                self.pending = self.pending[index + len(marker):]
                self.end = None if self.end else starts[marker]
                continue
            keep = 0
            if not final:
                for marker in markers:
                    for n in range(1, len(marker)):
                        if self.pending.endswith(marker[:n]):
                            keep = max(keep, n)
            end = len(self.pending) - keep
            if not self.end:
                output += self.pending[:end]
            self.pending = self.pending[end:]
            break
        return output


class LlamaCppProvider(LLMPort):
    def __init__(self, model_path, mmproj_path=None, n_ctx=8192, n_threads=4,
                 n_gpu_layers=0, enable_thinking=False, flash_attn=False,
                 offload_kqv=True, economy_mode=False, embedding_dim=768,
                 chat_handler="gemma4"):
        self.model_path = model_path
        self.mmproj_path = mmproj_path
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.n_gpu_layers = n_gpu_layers
        self.flash_attn = flash_attn
        self.offload_kqv = offload_kqv
        self.economy_mode = economy_mode
        self.embedding_dim = embedding_dim
        self.chat_handler = chat_handler
        self._llm = None
        self._handler = None
        self._lock = asyncio.Lock()
        self._executor = None
        self._native_audio = False

    async def _native(self, fn):
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lina-llm")
        future = asyncio.get_running_loop().run_in_executor(self._executor, fn)
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:
            # Never release the model lock while native code still uses it,
            # including when multiple owners request cancellation.
            while not future.done():
                try:
                    await asyncio.shield(future)
                except asyncio.CancelledError:
                    continue
                except Exception:
                    break
            if not future.cancelled():
                future.exception()
            raise

    def _load(self):
        register_runtime_directories()
        try:
            import llama_cpp
        except ImportError as exc:
            raise RuntimeError(
                f"Не удалось загрузить llama-cpp-python в {sys.executable}. "
                "Установите совместимую сборку с нужным GPU/backend в это окружение. "
                f"Причина: {exc}") from exc
        Llama = llama_cpp.Llama
        if self.n_gpu_layers != 0:
            verify_cuda_library(llama_cpp)
        if not self.model_path or not Path(self.model_path).is_file():
            raise ValueError("Укажите существующий GGUF-файл модели в настройках llm.")
        supports_gpu = getattr(llama_cpp, "llama_supports_gpu_offload", None)
        logging.getLogger("LinaAI").info(
            "Loading llama-cpp from %s; n_gpu_layers=%s, n_ctx=%s",
            getattr(llama_cpp, "__file__", "unknown"), self.n_gpu_layers, self.n_ctx)
        handler = None
        if self.mmproj_path:
            if not Path(self.mmproj_path).is_file():
                raise ValueError("Не найден mmproj-файл, соответствующий модели.")
            names = {"gemma4": "Gemma4ChatHandler", "mtmd": "MTMDChatHandler",
                     "llava15": "Llava15ChatHandler", "qwen25vl": "Qwen25VLChatHandler"}
            name = names.get(self.chat_handler)
            if name is None:
                raise ValueError(f"Неизвестный chat_handler: {self.chat_handler}")
            cls = None
            for module in ("llama_cpp.llama_multimodal", "llama_cpp.llama_chat_format"):
                try:
                    cls = getattr(importlib.import_module(module), name, None)
                except ImportError:
                    continue
                if cls:
                    break
            if cls is None:
                raise RuntimeError(f"Установленная сборка llama-cpp-python не содержит {name}. "
                                   "Установите сборку с поддержкой выбранной модели.")
            parameters = inspect.signature(cls).parameters
            # Gemma4 accepts mmproj_path through **kwargs in the original fork.
            # Inspecting only explicitly named parameters selected its deprecated alias.
            parameter = "mmproj_path" if self.chat_handler == "gemma4" or "mmproj_path" in parameters else "clip_model_path"
            options = {parameter: self.mmproj_path}
            if "use_gpu" in parameters:
                options["use_gpu"] = self.n_gpu_layers != 0
            handler = cls(**options)
            self._native_audio = module == "llama_cpp.llama_multimodal" and self.chat_handler in ("gemma4", "mtmd")
        try:
            model = Llama(model_path=self.model_path, chat_handler=handler, n_ctx=self.n_ctx,
                          n_threads=self.n_threads, n_gpu_layers=self.n_gpu_layers,
                          flash_attn=self.flash_attn, offload_kqv=self.offload_kqv, last_n_tokens_size=0, verbose=True)
            # Dynamic CUDA backends are registered by Llama's constructor.
            if self.n_gpu_layers != 0 and (supports_gpu is None or not supports_gpu()):
                model.close()
                raise RuntimeError("Загруженный backend llama-cpp-python не поддерживает GPU offload.")
        except BaseException:
            if handler and hasattr(handler, "close"):
                handler.close()
            raise
        self._handler = handler
        self._llm = model

    async def initialize(self):
        async with self._lock:
            if self._llm is None:
                await self._native(self._load)

    def is_initialized(self):
        return self._llm is not None

    def _messages(self, messages):
        result = [{"role": "user", "content": messages}] if isinstance(messages, str) else [
            {"role": m.role, "content": m.content} for m in messages]
        for message in result:
            if not isinstance(message["content"], list):
                continue
            for part in message["content"]:
                kind = part.get("type")
                if kind in ("image_url", "input_audio") and self._handler is None:
                    raise ValueError("Для изображений и аудио требуется мультимодальная модель и mmproj.")
                if kind == "input_audio" and not self._native_audio:
                    raise ValueError("В этой сборке нет native audio. Для голоса установите сборку "
                                     "JamePeng/llama-cpp-python с llama_multimodal и аудиосовместимые GGUF/mmproj.")
        return result

    def _complete(self, messages, temperature, max_tokens, stream, kwargs):
        # Exact text token counts plus a conservative chat-template reserve.
        # Multimodal token counts are model-dependent and validated by the handler.
        def cost(message):
            content = message["content"]
            if isinstance(content, list):
                content = "\n".join(part.get("text", "") for part in content)
            return len(self._llm.tokenize(content.encode("utf-8"), add_bos=False)) + 32
        budget = self.n_ctx - max_tokens - 256
        costs = [cost(m) for m in messages]
        total = sum(costs)
        # Preserve the current real user message and all subsequent tool exchanges.
        # Synthetic tool results use a user role for the current Gemma handler.
        anchor = max((i for i, m in enumerate(messages) if m["role"] == "user"
                      and not (isinstance(m["content"], str)
                               and m["content"].startswith("<|turn>tool\n"))), default=len(messages) - 1)
        removed = 0
        while anchor > 1 and total > budget:
            end = 2
            while end < anchor and messages[end]["role"] != "user":
                end += 1
            total -= sum(costs[1:end])
            removed += end - 1
            del messages[1:end]
            del costs[1:end]
            anchor -= end - 1
        if total > budget:
            raise ValueError("Контекст переполнен. Сократите сообщение или увеличьте размер контекста модели.")
        logging.getLogger("LinaAI").debug(
            "LLM context: text_tokens_with_reserve=%d budget=%d removed_history_messages=%d output_limit=%d",
            total, budget, removed, max_tokens)
        return self._llm.create_chat_completion(
            messages=messages, temperature=temperature, max_tokens=max_tokens,
            stream=stream, **kwargs)

    async def _chunks(self, messages, temperature, max_tokens, kwargs):
        # Cancellation is observed between native calls, never inside a ctypes
        # sampler callback. Keep the lock until the iterator has been closed.
        async with self._lock:
            if self._llm is None:
                await self._native(self._load)
            formatted = self._messages(messages)
            streams = []
            def open_stream():
                streams.append(self._complete(
                    formatted, temperature, min(max_tokens, 600 if self.economy_mode else 1200), True, kwargs))
            try:
                await self._native(open_stream)
                while True:
                    chunk = await self._native(lambda: next(streams[0], None))
                    if chunk is None:
                        break
                    yield chunk
            finally:
                if streams and hasattr(streams[0], "close"):
                    await self._native(streams[0].close)

    async def generate(self, messages, temperature=0.7, max_tokens=1000, tools=None, **kwargs):
        parts, usage, finish_reason = [], {}, "stop"
        async with aclosing(self._chunks(messages, temperature, max_tokens, kwargs)) as chunks:
            async for chunk in chunks:
                usage.update(chunk.get("usage") or {})
                for choice in chunk.get("choices", []):
                    parts.append(choice.get("delta", {}).get("content") or "")
                    finish_reason = choice.get("finish_reason") or finish_reason
        return ChatResponse(content=_VisibleText().feed("".join(parts), final=True),
                            usage=usage, model=Path(self.model_path).stem,
                            finish_reason=finish_reason)

    async def stream_generate(self, messages, temperature=0.7, max_tokens=1000, tools=None, **kwargs):
        visible = _VisibleText()
        async with aclosing(self._chunks(messages, temperature, max_tokens, kwargs)) as chunks:
            async for chunk in chunks:
                for choice in chunk.get("choices", []):
                    output = visible.feed(choice.get("delta", {}).get("content") or "")
                    if output:
                        yield output
            tail = visible.feed("", final=True)
            if tail:
                yield tail

    async def embed(self, text):
        raise NotImplementedError("Vector memory uses a dedicated embedding provider, not the conversational LLM.")

    async def embed_batch(self, texts):
        return [await self.embed(text) for text in texts]

    def get_embedding_dim(self):
        return self.embedding_dim

    async def close(self):
        async with self._lock:
            def release():
                model, handler = self._llm, self._handler
                self._llm = None
                self._handler = None
                self._native_audio = False
                try:
                    if handler and hasattr(handler, "close"):
                        handler.close()
                finally:
                    if model:
                        model.close()
            if self._executor:
                try:
                    await self._native(release)
                finally:
                    self._executor.shutdown(wait=True)
                    self._executor = None
