from pathlib import Path
from src.bootstrap.di import ApplicationContainer
from src.core.domain.value_objects.settings import Settings
from src.core.infrastructure.repositories.file_settings_repository import FileSettingsRepository
from local_paths import LLM_MODEL, MMPROJ


async def test_custom_model_paths_survive_save_and_configure_runtime(tmp_path):
    settings = Settings.default()
    settings.llm.model_path = str(tmp_path / "custom.gguf")
    settings.llm.mmproj_path = str(tmp_path / "projector.gguf")
    settings.vosk_model_path = str(tmp_path / "vosk")
    settings.embedding_model_path = str(tmp_path / "embeddings")
    settings.on_economy = True
    repo = FileSettingsRepository(str(tmp_path / "settings.json"))
    await repo.save(settings)
    restored = await repo.get()
    container = ApplicationContainer()
    container.set_settings(restored)
    config = container.container.config
    assert config.llm.model_path() == settings.llm.model_path
    assert config.llm.mmproj_path() == settings.llm.mmproj_path
    assert config.vosk_model_path() == settings.vosk_model_path
    assert config.embedding_model_path() == settings.embedding_model_path
    assert config.economy_mode() is True
    assert container.container.embeddings().model_path == Path(settings.embedding_model_path)


def test_existing_model_defaults_still_work():
    container = ApplicationContainer()
    container.set_settings(Settings.default())
    assert container.container.config.llm.model_path() == str(LLM_MODEL)
    assert container.container.config.llm.mmproj_path() == str(MMPROJ)
