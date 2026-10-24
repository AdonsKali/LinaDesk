from src.core.domain.entities.lina import Lina


def build_mood_section(lina: Lina) -> str:
    m = lina.current_mood
    return (
        f"=== CURRENT MOOD ===\n"
        f"{m.type.value} (intensity {m.intensity:.1f})"
    )