from src.core.domain.value_objects.tool import ToolSpec
TOOLS_INSTRUCTION = """
=== AVAILABLE TOOLS ===
{tools_description}
"""


def build_tools_section(tools: list[ToolSpec]) -> str:
    if not tools:
        return ""
    desc = "\n".join(f"- {t.name}: {t.description}; background={t.background}; permissions={[p.value for p in t.permissions]}; parameters={t.parameters}" for t in tools)
    return TOOLS_INSTRUCTION.format(tools_description=desc)
