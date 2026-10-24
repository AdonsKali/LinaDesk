from src.core.domain.entities.lina import Lina
from src.core.domain.entities.user import User


def build_identity_section(lina: Lina) -> str:
    traits = (
        ", ".join(f"{t.type.value}={t.value:.1f}" for t in lina.personality.values())
        if lina.personality else "(none)"
    )
    principles = (
        "\n".join(f"  - [{p.strength:.1f}] {p.statement}" for p in lina.principles)
        if lina.principles else "  (none)"
    )
    return (
        f"=== WHO I AM ===\n"
        f"Name: {lina.name}\n"
        f"Traits: {traits}\n"
        f"Principles:\n{principles}"
    )


def build_user_section(user: User) -> str:
    return (
        f"=== USER ===\n"
        f"Name: {user.name}\n"
        f"Language: {user.preferred_language}"
    )