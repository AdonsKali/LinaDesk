import json
from pathlib import Path
from typing import Optional
from src.core.application.ports.repositories import SettingsRepository
from src.core.domain.value_objects.settings import Settings
from src.core.utils.logger import logger


class FileSettingsRepository(SettingsRepository):
    """Репозиторий настроек"""

    def __init__(self, file_path: str = "data/settings.json"):
        self._file_path = Path(file_path)
        self._file_path.parent.mkdir(parents=True, exist_ok=True)

    async def get(self) -> Optional[Settings]:
        if not self._file_path.exists():
            return None
        try:
            with open(self._file_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
            # Import the old policy once; subsequent reads use only settings.json.
            legacy = self._file_path.parent.parent / "config" / "behavior.json"
            migrate = "behavior" not in data
            if migrate and legacy.is_file():
                data["behavior"] = json.loads(legacy.read_text(encoding="utf-8-sig"))
            settings = Settings.from_dict(data)
            if migrate:
                await self.save(settings)
            return settings
        except Exception as exc:
            raise ValueError(f"Не удалось прочитать настройки {self._file_path}: {exc}") from exc

    async def save(self, settings: Settings) -> None:
        temporary = self._file_path.with_suffix(".tmp")
        with open(temporary, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)
        temporary.replace(self._file_path)
