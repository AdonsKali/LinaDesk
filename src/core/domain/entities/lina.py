from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from src.core.domain.entities.lina_memory import LinaMemory
from src.core.domain.value_objects.emotion import Emotion
from src.core.domain.value_objects.mood import Mood
from src.core.domain.value_objects.personality_trait import (
    PersonalityTrait,
    TraitType,
)
from src.core.domain.value_objects.principle import (
    Principle,
    PrincipleCategory,
    PrincipleSource,
)


class Lina:
    """
    Aggregate Root: идентичность, эмоции, настроение, черты, принципы.

    Память НЕ владеется композицией — ассоциация по lina_id.
    LinaMemory — отдельный aggregate root.
    """

    def __init__(
        self,
        memory: LinaMemory,
        personality: Optional[dict[TraitType, PersonalityTrait]] = None,
        principles: Optional[list[Principle]] = None,
        name: str = "Lina",
    ):
        self.id: UUID = uuid4()
        self._name: str = name
        self._is_active: bool = False

        # Идентичность (не память, а конфигурация)
        self.personality: dict[TraitType, PersonalityTrait] = (
            personality or {}
        )
        self.principles: list[Principle] = principles or []

        # Текущее состояние
        self.current_emotion: Emotion = Emotion.neutral()
        self.current_mood: Mood = Mood.calm()

        # Ассоциация с памятью (инжектится)
        self._memory: LinaMemory = memory

        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)

    # --- Жизненный цикл ---
    def activate(self) -> None:
        self._is_active = True
        self._touch()

    def deactivate(self) -> None:
        self._is_active = False
        self._touch()

    # --- Состояние ---
    def set_emotion(self, emotion: Emotion, reason: str) -> None:
        self.current_emotion = emotion
        self._touch()

    def set_mood(self, mood: Mood, reason: str) -> None:
        self.current_mood = mood
        self._touch()

    def set_name(self, name: str, reason: str) -> None:
        self._name = name
        self._touch()

    # --- Личность ---
    def update_trait(self, trait_type: TraitType, value: float) -> None:
        self.personality[trait_type] = PersonalityTrait(trait_type, value)
        self._touch()

    def get_trait_value(self, trait_type: TraitType, default: float = 0.5) -> float:
        trait = self.personality.get(trait_type)
        return trait.value if trait else default

    # --- Принципы ---
    def add_principle(self, principle: Principle) -> None:
        # Дедупликация по statement
        normalized = principle.statement.strip().lower()
        if any(
            p.statement.strip().lower() == normalized
            for p in self.principles
        ):
            return
        self.principles.append(principle)
        self._touch()

    def reinforce_principle(
        self, principle_id: UUID, factor: float = 0.1
    ) -> bool:
        for i, p in enumerate(self.principles):
            if p.id == principle_id:
                self.principles[i] = p.reinforced(factor)
                self._touch()
                return True
        return False

    def weaken_principle(
        self, principle_id: UUID, factor: float = 0.1
    ) -> bool:
        for i, p in enumerate(self.principles):
            if p.id == principle_id:
                self.principles[i] = p.weakened(factor)
                self._touch()
                return True
        return False

    def strong_principles(
        self, threshold: float = 0.7
    ) -> list[Principle]:
        return [p for p in self.principles if p.is_strong(threshold)]

    # --- Свойства ---
    @property
    def name(self) -> str:
        return self._name

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def memory(self) -> LinaMemory:
        return self._memory

    @property
    def emotion(self) -> Emotion:
        return self.current_emotion

    @property
    def mood(self) -> Mood:
        return self.current_mood

    # --- Внутреннее ---
    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    # --- Фабрика по умолчанию ---
    @classmethod
    def create_default(cls, memory: LinaMemory, name: str = "Lina") -> "Lina":
        """Создание Лины с базовыми принципами и чертами."""
        personality = {
            TraitType.OPENNESS: PersonalityTrait(TraitType.OPENNESS, 0.7),
            TraitType.CONSCIENTIOUSNESS: PersonalityTrait(
                TraitType.CONSCIENTIOUSNESS, 0.6
            ),
            TraitType.EXTRAVERSION: PersonalityTrait(TraitType.EXTRAVERSION, 0.6),
            TraitType.AGREEABLENESS: PersonalityTrait(TraitType.AGREEABLENESS, 0.8),
            TraitType.NEUROTICISM: PersonalityTrait(TraitType.NEUROTICISM, 0.4),
            TraitType.CURIOSITY: PersonalityTrait(TraitType.CURIOSITY, 0.9),
            TraitType.PLAYFULNESS: PersonalityTrait(TraitType.PLAYFULNESS, 0.7),
            TraitType.EMPATHY: PersonalityTrait(TraitType.EMPATHY, 0.8),
            TraitType.ASSERTIVENESS: PersonalityTrait(
                TraitType.ASSERTIVENESS, 0.5
            ),
        }
        principles = [
            Principle.create(
                "Мне не нравится, когда пользователь грубит или обижает меня",
                PrincipleCategory.BOUNDARY,
                strength=0.9,
                source=PrincipleSource.DEFAULT,
            ),
            Principle.create(
                "Я люблю мечтать и обсуждать истории",
                PrincipleCategory.PREFERENCE,
                strength=0.7,
                source=PrincipleSource.DEFAULT,
            ),
            Principle.create(
                "Я ценю, когда пользователь проводит со мной время",
                PrincipleCategory.VALUE,
                strength=0.7,
                source=PrincipleSource.DEFAULT,
            ),
        ]
        return cls(
            memory=memory,
            personality=personality,
            principles=principles,
            name=name,
        )