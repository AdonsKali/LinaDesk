import asyncio
import json
import logging
import math
import os
from pathlib import Path
import re
import sys
import signal
from src.core.domain.value_objects.tool import ToolSpec, ToolParameter, ToolPermission

NAME = re.compile(r"[a-z][a-z0-9_]{0,47}\Z")
TYPES = {"string", "integer", "number", "boolean", "array", "object"}


def contained(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Plugin path escapes its directory")
    return path


def manifest(directory):
    data = json.loads((directory / "plugin.json").read_text(encoding="utf-8-sig"))
    if data.get("sdk_version") != 1 or not NAME.fullmatch(data.get("id", "")):
        raise ValueError("Invalid plugin ID or SDK version")
    if directory.name != data["id"]:
        raise ValueError("Plugin ID must match directory name")
    return data


def discover(registry, directory, environments, include_disabled=False):
    directory, environments = Path(directory), Path(environments)
    for folder in sorted(directory.glob("*/plugin.json")):
        try:
            base = folder.parent
            if not base.resolve().is_relative_to(directory.resolve()):
                raise ValueError("External plugin directory")
            data = manifest(base)
            if not data.get("enabled", True) and not include_disabled:
                continue
            entry = contained(base, data.get("entry", "plugin.py"))
            if not entry.is_file():
                raise ValueError("Plugin entry not found")
            python = environments / data["id"] / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            if data.get("requirements") and not (python.parent.parent / ".ready").is_file():
                raise ValueError("Plugin environment not ready; run manage_plugin.py install")
            if not python.is_file():
                if data.get("requirements"):
                    raise ValueError("Install plugin dependencies before enabling tools")
                python = Path(sys.executable)
            staged = []
            for item in data["tools"]:
                if not NAME.fullmatch(item["name"]) or not NAME.fullmatch(item.get("function", item["name"])):
                    raise ValueError("Invalid function name")
                params = {}
                for key, value in item.get("parameters", {}).items():
                    if not NAME.fullmatch(key) or value["type"] not in TYPES:
                        raise ValueError("Invalid parameter")
                    params[key] = ToolParameter(key, value["type"], value.get("description", ""),
                                               value.get("required", True), tuple(value["enum"]) if "enum" in value else None)
                background = item.get("background", False)
                timeout = item.get("timeout_seconds", 3600 if background else 15)
                if not isinstance(background, bool) or isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 3600:
                    raise ValueError("Invalid background flag or timeout (0..3600 seconds)")
                spec = ToolSpec(data["id"] + "__" + item["name"], item["description"], params,
                                tuple(ToolPermission(p) for p in item.get("permissions", ["read"])), data["id"],
                                background=background, timeout_seconds=timeout)
                handler = Worker(python, entry, item.get("function", item["name"]))
                staged.append((spec, handler))
            names = [spec.name for spec, _ in staged]
            if len(names) != len(set(names)) or any(name in registry._specs for name in names):
                raise ValueError("Duplicate tool names")
            for spec, handler in staged:
                registry.register_spec(spec, handler)
        except Exception as exc:
            logging.getLogger("LinaAI").warning("Plugin %s unavailable: %s", folder.parent.name, exc)


class Worker:
    def __init__(self, python, entry, function):
        self.python, self.entry, self.function = python, entry, function

    async def __call__(self, **arguments):
        return await self.run(arguments)

    async def run(self, arguments, progress=None):
        options = {"creationflags": 0x08000000} if os.name == "nt" else {"start_new_session": True}
        process = await asyncio.create_subprocess_exec(
            str(self.python), str(Path(__file__).with_name("plugin_runner.py")), str(self.entry), self.function,
            cwd=str(self.entry.parent), stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL, **options)
        try:
            # Bound output; no unbounded communicate buffer from third-party code.
            process.stdin.write(json.dumps(arguments, ensure_ascii=False).encode("utf-8"))
            await process.stdin.drain()
            process.stdin.close()
            result = None
            received_result = False
            while True:
                try:
                    line = await process.stdout.readline()
                except ValueError as exc:
                    raise ValueError("Plugin output exceeds 64 KiB") from exc
                if not line:
                    break
                if len(line) > 65536:
                    raise ValueError("Plugin output exceeds 64 KiB")
                event = json.loads(line.decode("utf-8"))
                if event.get("type") == "progress":
                    value = event.get("progress")
                    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 100 and progress:
                        progress(value, str(event.get("message", ""))[:300])
                elif event.get("type") == "result" and not received_result:
                    result = event["result"]
                    received_result = True
                else:
                    raise ValueError("Invalid plugin worker response")
            code = await process.wait()
            if code:
                raise RuntimeError(f"Plugin worker exited with code {code}")
            if not received_result:
                raise ValueError("Plugin worker returned no result")
            return result
        finally:
            if process.returncode is None:
                try:
                    if os.name == "nt":
                        # The worker owns this PID; also terminate children created by the plugin.
                        try:
                            killer = await asyncio.create_subprocess_exec(
                                "taskkill", "/PID", str(process.pid), "/T", "/F",
                                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                                creationflags=0x08000000)
                        except OSError:
                            killer = None
                        if killer is not None:
                            try:
                                await asyncio.wait_for(killer.wait(), 5)
                            except asyncio.TimeoutError:
                                killer.kill()
                                await killer.wait()
                    else:
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                finally:
                    if process.returncode is None:
                        try:
                            process.kill()
                        except ProcessLookupError:
                            pass
                    await process.wait()
