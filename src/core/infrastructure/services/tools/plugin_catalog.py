import json
from pathlib import Path
from .plugins import manifest, contained, NAME, discover
from .in_memory_tool_registry import InMemoryToolRegistry


class FilePluginCatalog:
    def __init__(self, directory, environments):
        self.directory, self.environments = Path(directory), Path(environments)

    async def list_plugins(self):
        registry = InMemoryToolRegistry()
        discover(registry, self.directory, self.environments, include_disabled=True)
        specs = await registry.get_available()
        result = []
        for path in sorted(self.directory.glob("*/plugin.json")):
            name = path.parent.name
            try:
                folder = contained(self.directory, name)
                data = manifest(folder)
                enabled = data.get("enabled", True)
                tools = [s.name for s in specs if s.plugin_name == name]
                status = "disabled" if not enabled else "ready" if tools else "unavailable"
                result.append({"name": name, "version": str(data.get("version", "1")),
                               "enabled": enabled, "status": status, "editable": True,
                               "description": data.get("description", ""), "tools": tools,
                               "tool_specs": [{"name": s.name, "description": s.description,
                                               "permissions": [p.value for p in s.permissions]}
                                              for s in specs if s.plugin_name == name],
                               "requirements": data.get("requirements"),
                               "install_command": f".venv/Scripts/python.exe tools/manage_plugin.py install {name}"})
            except Exception as exc:
                result.append({"name": name, "enabled": False, "status": "invalid",
                               "editable": False, "description": str(exc), "tools": []})
        return result

    async def set_enabled(self, name, enabled):
        if not isinstance(name, str) or not NAME.fullmatch(name) or type(enabled) is not bool:
            raise ValueError("Invalid plugin toggle")
        folder = contained(self.directory, name)
        data = manifest(folder)
        data["enabled"] = enabled
        path = contained(folder, "plugin.json")
        temporary = contained(folder, "plugin.json.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
