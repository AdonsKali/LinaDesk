import asyncio
import contextlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    entry, function = sys.argv[1:3]
    sys.path.insert(0, str(Path(entry).parent))
    arguments = json.load(sys.stdin)
    with contextlib.redirect_stdout(sys.stderr):
        spec = importlib.util.spec_from_file_location("lina_plugin", entry)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = getattr(module, function)(**arguments)
        if inspect.isawaitable(result):
            result = asyncio.run(result)
    print(json.dumps({"type": "result", "result": result}, ensure_ascii=False, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
