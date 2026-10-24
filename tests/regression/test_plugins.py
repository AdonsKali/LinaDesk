import asyncio
import json
from pathlib import Path
import pytest
from src.core.infrastructure.services.tools.plugins import discover, Worker
from src.core.infrastructure.services.tools.in_memory_tool_registry import InMemoryToolRegistry


async def test_discovery_and_real_worker(tmp_path):
    root = Path(__file__).resolve().parents[2]
    registry = InMemoryToolRegistry()
    discover(registry, root / "plugins", tmp_path)
    handler = await registry.get_handler("text_utils__word_count")
    assert await handler(text="Привет мир") == {"words": 2, "characters": 10}


async def test_bad_plugin_does_not_break_other_plugins(tmp_path):
    folder = tmp_path / "broken"
    folder.mkdir()
    (folder / "plugin.json").write_text("invalid json")
    registry = InMemoryToolRegistry()
    discover(registry, tmp_path, tmp_path / "envs")
    assert await registry.get_available() == []


async def test_worker_cancellation_and_output_limit(tmp_path):
    import sys
    entry = tmp_path / "plugin.py"
    entry.write_text('import time\ndef slow():\n    time.sleep(30)\ndef huge():\n    return "x" * 100000\n')
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(Worker(Path(sys.executable), entry, "slow")(), .3)
    with pytest.raises(ValueError, match="64 KiB"):
        await Worker(Path(sys.executable), entry, "huge")()


async def test_catalog_toggle_preserves_manifest_and_detects_unavailable(tmp_path):
    import shutil
    from src.core.infrastructure.services.tools.plugin_catalog import FilePluginCatalog
    root = Path(__file__).resolve().parents[2]
    shutil.copytree(root / "plugins" / "text_utils", tmp_path / "plugins" / "text_utils")
    catalog = FilePluginCatalog(tmp_path / "plugins", tmp_path / "envs")
    assert (await catalog.list_plugins())[0]["status"] == "ready"
    await catalog.set_enabled("text_utils", False)
    assert (await catalog.list_plugins())[0]["status"] == "disabled"
    await catalog.set_enabled("text_utils", True)
    path = tmp_path / "plugins" / "text_utils" / "plugin.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["tools"][0]["name"] == "word_count"
    data["requirements"] = "requirements.txt"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert (await catalog.list_plugins())[0]["status"] == "unavailable"
    with pytest.raises(ValueError):
        await catalog.set_enabled("../text_utils", True)
