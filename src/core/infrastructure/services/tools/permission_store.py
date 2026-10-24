import json
from pathlib import Path
from src.core.domain.value_objects.tool import ToolPermission


class FileToolPermissionStore:
    def __init__(self, path):
        self.path = Path(path)

    def _read(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {}
            valid = {p.value for p in ToolPermission}
            return {key: value for key, value in data.items()
                    if isinstance(value, list) and all(isinstance(p, str) and p in valid for p in value)}
        except (OSError, ValueError):
            return {}

    def get(self, tool_name):
        return list(self._read().get(tool_name, []))

    def set(self, tool_name, permissions):
        data = self._read()
        if permissions:
            data[tool_name] = list(permissions)
        else:
            data.pop(tool_name, None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.path)
