import asyncio
import sys
import threading
import time
from types import SimpleNamespace

import pytest
from src.core.infrastructure.providers.llm.local.provider import LlamaCppProvider, _VisibleText


@pytest.mark.parametrize("split", range(1, 8))
def test_stream_thinking_markers_across_chunks(split):
    visible = _VisibleText()
    text = "hello <think>private reasoning</think> world"
    output = "".join(visible.feed(text[i:i+split]) for i in range(0, len(text), split))
    assert output + visible.feed("", final=True) == "hello  world"


async def test_gpu_build_is_required(tmp_path, monkeypatch):
    model = tmp_path / "model.gguf"
    model.touch()
    calls = []
    def construct(**kwargs):
        calls.append("loaded")
        return SimpleNamespace(close=lambda: calls.append("closed"))
    module = SimpleNamespace(Llama=construct, llama_supports_gpu_offload=lambda: False)
    monkeypatch.setitem(sys.modules, "llama_cpp", module)
    provider = LlamaCppProvider(str(model), n_gpu_layers=-1)
    with pytest.raises(RuntimeError, match="GPU offload"):
        await provider.initialize()
    await provider.close()
    assert calls == ["loaded", "closed"]


async def test_gpu_capability_is_checked_after_backend_registration(tmp_path, monkeypatch):
    model = tmp_path / "model.gguf"
    model.touch()
    initialized = False
    def construct(**kwargs):
        nonlocal initialized
        initialized = True
        return SimpleNamespace(close=lambda: None)
    monkeypatch.setitem(sys.modules, "llama_cpp", SimpleNamespace(
        Llama=construct, llama_supports_gpu_offload=lambda: initialized))
    provider = LlamaCppProvider(str(model), n_gpu_layers=-1)
    await provider.initialize()
    assert provider.is_initialized()
    await provider.close()


def test_missing_cuda_dependency_is_reported(tmp_path, monkeypatch):
    from src.core.infrastructure.providers.llm.local import native_runtime
    if native_runtime.os.name != "nt":
        pytest.skip("Windows DLL loading")
    lib = tmp_path / "lib"
    lib.mkdir()
    (lib / "ggml-cuda.dll").touch()
    def missing(path):
        raise OSError("missing dependency")
    monkeypatch.setattr(native_runtime.ctypes, "WinDLL", missing)
    with pytest.raises(RuntimeError, match="CUDA/cuBLAS"):
        native_runtime.verify_cuda_library(SimpleNamespace(__file__=str(tmp_path / "__init__.py")))


@pytest.mark.parametrize("layers", [0, -1, 10])
async def test_native_gpu_parameters(tmp_path, monkeypatch, layers):
    model = tmp_path / "model.gguf"
    model.touch()
    calls = []
    def construct(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(close=lambda: None)
    monkeypatch.setitem(sys.modules, "llama_cpp", SimpleNamespace(
        Llama=construct, llama_supports_gpu_offload=lambda: True))
    provider = LlamaCppProvider(str(model), n_gpu_layers=layers)
    await provider.initialize()
    await provider.close()
    assert calls[0]["n_gpu_layers"] == layers
    assert calls[0]["verbose"] is True


async def test_cancel_waits_for_native_worker_even_when_cancelled_twice():
    provider = LlamaCppProvider("unused")
    started, finished, release = threading.Event(), threading.Event(), threading.Event()
    def work():
        started.set()
        assert release.wait(2)
        time.sleep(.05)
        finished.set()
    async def operation():
        async with provider._lock:
            await provider._native(work)
    task = asyncio.create_task(operation())
    while not started.is_set():
        await asyncio.sleep(.001)
    task.cancel()
    await asyncio.sleep(.01)
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert finished.is_set()
    await provider.close()
    assert provider._executor is None


async def test_close_releases_model_if_handler_close_fails():
    provider = LlamaCppProvider("unused")
    calls = []
    def bad_close():
        calls.append("handler")
        raise RuntimeError("handler failure")
    provider._handler = SimpleNamespace(close=bad_close)
    provider._llm = SimpleNamespace(close=lambda: calls.append("model"))
    await provider._native(lambda: None)
    with pytest.raises(RuntimeError, match="handler failure"):
        await provider.close()
    assert calls == ["handler", "model"]
    assert provider._llm is None and provider._executor is None


@pytest.mark.parametrize("streaming", [False, True])
async def test_cancel_closes_iterator_before_model_without_sampler_callback(tmp_path, monkeypatch, streaming):
    model = tmp_path / "model.gguf"
    model.touch()
    started, release = threading.Event(), threading.Event()
    calls = []
    def complete(**kwargs):
        assert kwargs["stream"] is True
        assert "logits_processor" not in kwargs
        assert "stopping_criteria" not in kwargs
        try:
            started.set()
            assert release.wait(3)
            calls.append("native_finished")
            yield {"choices": [{"delta": {"content": "hello"}}]}
            pytest.fail("cancelled generation continued")
        finally:
            calls.append("iterator_closed")
    monkeypatch.setitem(sys.modules, "llama_cpp", SimpleNamespace(
        Llama=lambda **kw: SimpleNamespace(tokenize=lambda *a, **k: [],
            create_chat_completion=complete, close=lambda: calls.append("model_closed"))))
    provider = LlamaCppProvider(str(model))
    async def run():
        if streaming:
            async for _ in provider.stream_generate("hello"):
                pass
        else:
            await provider.generate("hello")
    task = asyncio.create_task(run())
    while not started.is_set():
        await asyncio.sleep(.001)
    task.cancel()
    close = asyncio.create_task(provider.close())
    await asyncio.sleep(.01)
    assert not close.done()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    await close
    assert calls == ["native_finished", "iterator_closed", "model_closed"]


async def test_generate_collects_stream_content_and_metadata():
    provider = LlamaCppProvider("model.gguf")
    provider._llm = SimpleNamespace(
        tokenize=lambda *a, **k: [], close=lambda: None,
        create_chat_completion=lambda **kw: iter([
            {"choices": [{"delta": {"content": "<think>hidden</think>hi"}}]},
            {"choices": [{"delta": {}, "finish_reason": "length"}]},
            {"choices": [], "usage": {"completion_tokens": 5}},
        ]))
    response = await provider.generate("hello")
    await provider.close()
    assert response.content == "hi"
    assert response.finish_reason == "length"
    assert response.usage == {"completion_tokens": 5}


async def test_gemma4_uses_original_mmproj_keyword_with_kwargs(tmp_path, monkeypatch):
    model, projector = tmp_path / "model.gguf", tmp_path / "mmproj.gguf"
    model.touch()
    projector.touch()
    options = []
    class Handler:
        def __init__(self, clip_model_path=None, **kwargs):
            assert clip_model_path is None
            options.append(kwargs)
        def close(self):
            pass
    monkeypatch.setitem(sys.modules, "llama_cpp.llama_multimodal", SimpleNamespace(Gemma4ChatHandler=Handler))
    monkeypatch.setitem(sys.modules, "llama_cpp", SimpleNamespace(
        Llama=lambda **kwargs: SimpleNamespace(close=lambda: None),
        llama_supports_gpu_offload=lambda: True))
    provider = LlamaCppProvider(str(model), str(projector), n_gpu_layers=-1)
    await provider.initialize()
    await provider.close()
    assert options == [{"mmproj_path": str(projector)}]
