"""Sentence Transformers adapter, independent from the conversational LLM."""
import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from local_paths import BASE_DIR, EMBEDDING_MODEL


class SentenceTransformerEmbeddings:
    def __init__(self, model_path=None):
        path = Path(model_path) if model_path else EMBEDDING_MODEL
        self.model_path = path if path.is_absolute() else BASE_DIR / path
        self.model_id = self.model_path.name + ":" + str(self.model_path.resolve())
        self._model = None
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()
        self._executor = None

    def _load_model(self, sentence_transformer):
        try:
            return sentence_transformer(str(self.model_path), device="cpu",
                                        trust_remote_code=False, local_files_only=True)
        except TypeError as exc:
            if "word_embedding_dimension" not in str(exc) or "Pooling" not in str(exc):
                raise
            return self._load_pooling_compatible_model(sentence_transformer)

    def _load_pooling_compatible_model(self, sentence_transformer):
        from sentence_transformers import models

        manifest = json.loads((self.model_path / "modules.json").read_text(encoding="utf-8"))
        types = [entry["type"] for entry in manifest]
        expected = ["sentence_transformers.models.Transformer", "sentence_transformers.models.Pooling"]
        if types not in (expected, expected + ["sentence_transformers.models.Normalize"]):
            raise RuntimeError("Несовместимая конфигурация Pooling: ожидаются Transformer, Pooling и необязательный Normalize")

        paths = [(self.model_path / entry["path"]).resolve() for entry in manifest]
        if any(not path.is_relative_to(self.model_path.resolve()) for path in paths):
            raise RuntimeError("Путь модуля выходит за пределы каталога embedding-модели")
        config = json.loads((paths[1] / "config.json").read_text(encoding="utf-8"))
        transformer = models.Transformer(str(paths[0]),
            model_args={"local_files_only": True, "trust_remote_code": False},
            tokenizer_args={"local_files_only": True, "trust_remote_code": False},
            config_args={"local_files_only": True, "trust_remote_code": False})
        # Preserve the saved sequence length and lower-casing options.
        transformer_config = paths[0] / "sentence_bert_config.json"
        if transformer_config.is_file():
            saved = json.loads(transformer_config.read_text(encoding="utf-8"))
            if "max_seq_length" in saved:
                transformer.max_seq_length = saved["max_seq_length"]
            if "do_lower_case" in saved:
                transformer.do_lower_case = saved["do_lower_case"]
        config.setdefault("word_embedding_dimension", transformer.get_word_embedding_dimension())
        modules = [transformer, models.Pooling(**config)]
        if len(paths) == 3:
            modules.append(models.Normalize())
        return sentence_transformer(modules=modules, device="cpu", trust_remote_code=False)

    def _encode(self, texts):
        with self._lock:
            if self._model is None:
                if not self.model_path.is_dir():
                    raise RuntimeError(f"Не найдена локальная embedding-модель: {self.model_path}. Задайте embedding_model_path в data/settings.json.")
                try:
                    from sentence_transformers import SentenceTransformer
                except ImportError as exc:
                    raise RuntimeError("Для векторной памяти установите зависимости из requirements-prototype.txt (sentence-transformers)") from exc
                self._model = self._load_model(SentenceTransformer)
            return self._model.encode(texts, normalize_embeddings=True,
                                      batch_size=32, show_progress_bar=False).tolist()

    async def _native(self, operation):
        if self._executor is None:
            self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lina-embeddings")
        future = asyncio.get_running_loop().run_in_executor(self._executor, operation)
        try:
            return await asyncio.shield(future)
        except asyncio.CancelledError:
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

    async def embed_documents(self, texts):
        if not texts:
            return []
        async with self._async_lock:
            return await self._native(lambda: self._encode(texts))

    async def embed_query(self, text):
        return (await self.embed_documents([text]))[0]

    async def close(self):
        async with self._async_lock:
            if self._executor is not None:
                def release():
                    with self._lock:
                        self._model = None
                try:
                    await self._native(release)
                finally:
                    self._executor.shutdown(wait=True)
                    self._executor = None
