import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from uuid import UUID

from src.core.application.ports.repositories import EmotionHistoryRepositoryPort
from src.core.domain.value_objects.emotion import Emotion, EmotionType, Valence
from src.core.domain.value_objects.emotion import EmotionRecord

logger = logging.getLogger(__name__)


class FileEmotionHistoryRepository(EmotionHistoryRepositoryPort):
    """
    История эмоций в JSON-файле.
    Хранит эмоции Лины для расчёта mood.
    Ограничивает размер файла (max_records), удаляя самые старые.
    """

    def __init__(
        self,
        data_dir: str = "data/emotions",
        max_records: int = 1000,
    ):
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._max_records = max_records
        if max_records < 1:
            raise ValueError("max_records must be positive")

    def _path(self, lina_id: UUID) -> Path:
        return self._dir / f"{lina_id}.json"

    def _load(self, lina_id: UUID) -> list[dict]:
        path = self._path(lina_id)
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            logger.exception(f"Failed to load emotion history for {lina_id}")
            return []

    def _save(self, lina_id: UUID, records: list[dict]) -> None:
        # Обрезаем до max_records (оставляем последние)
        if len(records) > self._max_records:
            records = records[-self._max_records:]

        path = self._path(lina_id)
        try:
            temporary = path.with_suffix(".tmp")
            with open(temporary, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False, indent=2)
            temporary.replace(path)
        except Exception:
            logger.exception(f"Failed to save emotion history for {lina_id}")
            raise

    @staticmethod
    def _record_to_dict(record: EmotionRecord) -> dict:
        e = record.emotion
        return {
            "id": str(record.id),
            "emotion_type": e.type.value,
            "intensity": e.intensity,
            "valence": e.valence.value,
            "label": e.label,
            "recorded_at": record.recorded_at.isoformat(),
            "trigger": record.trigger,
            "trigger_text": record.trigger_text,
            "metadata": record.metadata,
        }

    @staticmethod
    def _dict_to_record(data: dict) -> Optional[EmotionRecord]:
        try:
            etype = EmotionType(data["emotion_type"])
            emotion = Emotion(
                type=etype,
                intensity=float(data["intensity"]),
                valence=Valence(data["valence"]),
                label=data.get("label", etype.value.capitalize()),
            )
            return EmotionRecord(
                id=UUID(data["id"]),
                emotion=emotion,
                recorded_at=datetime.fromisoformat(data["recorded_at"]),
                trigger=data.get("trigger", ""),
                trigger_text=data.get("trigger_text", ""),
                metadata=data.get("metadata", {}),
            )
        except Exception:
            logger.exception(f"Failed to parse emotion record: {data}")
            return None

    async def add(self, lina_id: UUID, record: EmotionRecord) -> None:
        records = self._load(lina_id)
        records.append(self._record_to_dict(record))
        self._save(lina_id, records[-2000:])

    async def get_last_days(
        self,
        lina_id: UUID,
        days: int = 3,
    ) -> list[EmotionRecord]:
        records = self._load(lina_id)
        threshold = datetime.now(timezone.utc) - timedelta(days=days)

        result: list[EmotionRecord] = []
        for data in records:
            record = self._dict_to_record(data)
            if record is None:
                continue
            # Приводим к UTC
            recorded = record.recorded_at
            if recorded.tzinfo is None:
                recorded = recorded.replace(tzinfo=timezone.utc)
            if recorded >= threshold:
                result.append(record)
        return result

    async def get_recent(
        self,
        lina_id: UUID,
        limit: int = 20,
    ) -> list[EmotionRecord]:
        if limit <= 0:
            return []
        records = self._load(lina_id)
        result: list[EmotionRecord] = []
        for data in records[-limit:]:
            record = self._dict_to_record(data)
            if record is not None:
                result.append(record)
        return result

    async def clear(self, lina_id: UUID) -> None:
        path = self._path(lina_id)
        if path.exists():
            path.unlink()
