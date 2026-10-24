import json
import sys
import threading
from types import SimpleNamespace

from src.core.infrastructure.providers.stt.local.vosk_recognize import VoskRecognizer
from src.core.infrastructure.repositories.file_settings_repository import FileSettingsRepository
from src.bootstrap.di import ApplicationContainer


async def test_legacy_behavior_migrates_once_and_runtime_uses_settings(tmp_path):
    data = tmp_path / "data"
    config = tmp_path / "config"
    data.mkdir()
    config.mkdir()
    path = data / "settings.json"
    path.write_text(json.dumps({"username": "owner", "llm": {"n_gpu_layers": 10}}))
    legacy = config / "behavior.json"
    legacy.write_text(json.dumps({"identity": ["original identity"], "idle_seconds": 12}))
    repository = FileSettingsRepository(str(path))
    settings = await repository.get()
    assert settings.behavior.identity == ("original identity",)
    assert settings.llm.n_gpu_layers == 10
    legacy.write_text(json.dumps({"identity": ["obsolete identity"]}))
    settings = await repository.get()
    assert settings.behavior.identity == ("original identity",)
    container = ApplicationContainer()
    container.set_settings(settings)
    assert container.container.policy().idle_seconds == 12
    assert json.loads(path.read_text())["behavior"]["identity"] == ["original identity"]


async def test_vosk_combines_segments_and_reuses_model_off_ui_thread(tmp_path, monkeypatch):
    loads, worker_threads = [], []
    main_thread = threading.get_ident()
    class Recognizer:
        def __init__(self, model, rate):
            assert rate == 16000
            self.calls = 0
        def AcceptWaveform(self, data):
            worker_threads.append(threading.get_ident())
            self.calls += 1
            return self.calls == 1
        def Result(self):
            return '{"text": "hello"}'
        def FinalResult(self):
            return '{"text": "world"}'
    monkeypatch.setitem(sys.modules, "vosk", SimpleNamespace(
        Model=lambda path: loads.append(path) or object(), KaldiRecognizer=Recognizer))
    recognizer = VoskRecognizer(tmp_path)
    try:
        assert await recognizer.transcribe(bytes(16000), 16000) == "hello world"
        assert await recognizer.transcribe(bytes(16000), 16000) == "hello world"
        assert len(loads) == 1
        assert worker_threads and all(t != main_thread for t in worker_threads)
    finally:
        await recognizer.close()
    assert recognizer._model is None and recognizer._executor is None
