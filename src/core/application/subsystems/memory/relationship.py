import math
from datetime import datetime, timezone
from src.core.domain.value_objects.emotion import Valence


def relationship_score(lina, user_id, policy):
    """Derived, bounded attitude; one contribution per real user turn."""
    now = datetime.now(timezone.utc)
    total = 0.0
    seen = set()
    for f in lina.memory.all():
        if f.metadata.get("user_id") != str(user_id) or "emotional_episode" not in f.tags:
            continue
        turn = f.metadata.get("message_id")
        if turn in seen:
            continue
        seen.add(turn)
        age = max(0, (now - f.created_at).total_seconds() / 86400)
        decay = 0.5 ** (age / policy.relationship_half_life_days)
        sign = 1 if f.emotional_valence == Valence.POSITIVE else -1 if f.emotional_valence == Valence.NEGATIVE else 0
        weight = f.metadata.get("relationship_weight", 1.0)
        if not isinstance(weight, (float, int)) or not math.isfinite(weight):
            weight = 1.0
        total += sign * f.emotional_intensity * policy.relationship_step * decay * max(0.0, min(1.0, weight))
    return math.tanh(total)


def relationship_section(lina, user, policy):
    value = relationship_score(lina, user.id, policy)
    label = "осторожное, дистанцированное" if value < -0.2 else "тёплое, доверительное" if value > 0.2 else "нейтральное, открытое"
    return (
        f"=== RELATIONSHIP ===\nAttitude toward this user: {value:.3f} [-1, 1]; {label}.\n"
        "Use this as a tone tendency, not as evidence of malicious intent. "
        "Allow trust to recover. Never fabricate shared events."
    )
