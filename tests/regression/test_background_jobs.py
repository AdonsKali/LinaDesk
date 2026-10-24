import asyncio
import json
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.core.application.subsystems.tools.jobs import BackgroundJobs
from src.core.application.subsystems.tools.engine import ToolEngine
from src.core.domain.entities.user import User
from src.core.domain.value_objects.tool import ToolSpec, ToolCall, ToolPermission
from src.core.infrastructure.services.tools.in_memory_tool_registry import InMemoryToolRegistry
from src.core.infrastructure.services.tools.plugins import Worker, discover


async def settle(jobs, owner, job_id):
    async def wait():
        while jobs.status(owner, job_id)["status"] in {"queued", "running"}:
            await asyncio.sleep(.01)
        return jobs.status(owner, job_id)
    return await asyncio.wait_for(wait(), 5)


async def test_parallel_slots_queue_limit_and_cancel():
    jobs = BackgroundJobs(AsyncMock(), concurrency=2, capacity=3)
    started = []
    release = asyncio.Event()
    async def work(progress):
        started.append(True)
        progress(25, "Working")
        await release.wait()
        return "done"
    ids = [jobs.submit("user", "slow", work, 10)["job_id"] for _ in range(3)]
    try:
        await asyncio.sleep(.02)
        assert len(started) == 2
        assert jobs.status("user", ids[0])["progress"] == 25
        assert jobs.status("user", ids[2])["status"] == "queued"
        with pytest.raises(RuntimeError, match="full"):
            jobs.submit("user", "overflow", work, 10)
        assert (await jobs.cancel("user", ids[2]))["status"] == "cancelled"
        assert len(started) == 2
        release.set()
        assert (await settle(jobs, "user", ids[0]))["result"] == "done"
    finally:
        await jobs.close()
    assert not jobs._tasks


async def test_ownership_timeout_failure_and_bounded_history():
    bus = AsyncMock()
    jobs = BackgroundJobs(bus, history=2)
    async def slow(progress):
        await asyncio.sleep(10)
    job_id = jobs.submit("a", "slow", slow, .02)["job_id"]
    with pytest.raises(ValueError, match="not found"):
        await jobs.cancel("b", job_id)
    with pytest.raises(ValueError):
        jobs.status("b", job_id)
    assert jobs.list("b") == []
    assert (await settle(jobs, "a", job_id))["status"] == "timed_out"
    async def bad(progress):
        raise ValueError("broken")
    failed = jobs.submit("a", "bad", bad, 1)["job_id"]
    assert (await settle(jobs, "a", failed))["error"] == "broken"
    async def ok(progress):
        return "x" * 10000
    final = jobs.submit("a", "ok", ok, 1)["job_id"]
    assert len((await settle(jobs, "a", final))["result"]) == 4000
    assert len(jobs.list("a")) == 2
    assert len(bus.publish.await_args_list) == 3
    await jobs.close()


async def test_immediate_stop_and_restart_rejects_new_jobs():
    jobs = BackgroundJobs(AsyncMock())
    async def slow(progress):
        await asyncio.sleep(10)
    job_id = jobs.submit("a", "slow", slow, 10)["job_id"]
    await jobs.close()
    assert jobs.status("a", job_id)["status"] == "cancelled"
    with pytest.raises(RuntimeError, match="stopping"):
        jobs.submit("a", "slow", slow, 10)


async def test_container_reset_drains_jobs_and_rebinds_engine():
    from dependency_injector import providers
    from src.bootstrap.di import ApplicationContainer
    from src.core.domain.value_objects.settings import Settings
    container = ApplicationContainer()
    container.set_settings(Settings.default())
    container.container.llm.override(providers.Object(AsyncMock()))
    container.container.embeddings.override(providers.Object(AsyncMock()))
    previous = container.container.background_jobs()
    old_engine = container.container.tool_engine()
    async def slow(progress):
        await asyncio.sleep(30)
    job_id = previous.submit("u", "slow", slow, 60)["job_id"]
    await container.reset()
    assert previous.status("u", job_id)["status"] == "cancelled"
    current = container.container.background_jobs()
    assert current is not previous and not current._closing
    assert container.container.tool_engine() is not old_engine
    assert container.container.tool_engine()._jobs is current
    await current.close()


async def test_engine_keeps_dialogue_tools_available_and_scopes_controls():
    registry = InMemoryToolRegistry()
    release = asyncio.Event()
    async def slow():
        await release.wait()
        return "finished"
    async def fast():
        return "instant"
    for name, handler, background in [("slow", slow, True), ("fast", fast, False)]:
        registry.register_spec(ToolSpec(name, name, {}, (ToolPermission.READ,), "test",
                                        background=background, timeout_seconds=5), handler)
    bus = AsyncMock()
    jobs = BackgroundJobs(bus)
    engine = ToolEngine(registry, bus, jobs=jobs)
    user, other = User("owner"), User("other")
    try:
        result = await engine.execute(ToolCall("slow"), user)
        assert result.success
        job_id = json.loads(result.output)["job_id"]
        assert (await engine.execute(ToolCall("fast"), user)).output == "instant"
        assert not (await engine.execute(ToolCall("jobs_status", {"job_id": job_id}), other)).success
        listed = await engine.execute(ToolCall("jobs_list"), user)
        assert json.loads(listed.output)[0]["job_id"] == job_id
        cancelled = await engine.execute(ToolCall("jobs_cancel", {"job_id": job_id}), user)
        assert json.loads(cancelled.output)["status"] == "cancelled"
        assert "jobs_status" in {s.name for s in await engine.get_available_tools()}
    finally:
        await jobs.close()


async def test_real_worker_progress_and_stop_cleanup(tmp_path):
    entry = tmp_path / "plugin.py"
    entry.write_text('from lina_plugin_sdk import report_progress\nimport time\n'
                     'def run():\n    report_progress(25, "Hello")\n    return {"done": True}\n'
                     'def slow():\n    report_progress(10, "Started")\n    time.sleep(30)\n', encoding="utf-8")
    updates = []
    assert await Worker(Path(sys.executable), entry, "run").run({}, lambda *args: updates.append(args)) == {"done": True}
    assert updates == [(25, "Hello")]
    bus = AsyncMock()
    jobs = BackgroundJobs(bus)
    worker = Worker(Path(sys.executable), entry, "slow")
    async def operation(progress):
        return await worker.run({}, progress)
    job_id = jobs.submit("u", "slow", operation, 10)["job_id"]
    async def running():
        while jobs.status("u", job_id)["progress"] != 10:
            await asyncio.sleep(.01)
    await asyncio.wait_for(running(), 5)
    await asyncio.wait_for(jobs.close(), 8)
    assert jobs.status("u", job_id)["status"] == "cancelled"
    assert not jobs._tasks


@pytest.mark.skipif(os.name != "nt", reason="Windows process tree cleanup")
async def test_stop_terminates_plugin_child_process(tmp_path):
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    entry = tmp_path / "plugin.py"
    entry.write_text('import subprocess, sys, time\nfrom lina_plugin_sdk import report_progress\n'
                     'def run():\n    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"], creationflags=0x08000000)\n'
                     '    report_progress(1, str(child.pid))\n    time.sleep(30)\n', encoding="utf-8")
    jobs = BackgroundJobs(AsyncMock())
    worker = Worker(Path(sys.executable), entry, "run")
    async def operation(progress):
        return await worker.run({}, progress)
    job_id = jobs.submit("u", "tree", operation, 10)["job_id"]
    handle = None
    try:
        async def reported():
            while not jobs.status("u", job_id)["message"]:
                await asyncio.sleep(.01)
        await asyncio.wait_for(reported(), 5)
        child_pid = int(jobs.status("u", job_id)["message"])
        handle = kernel.OpenProcess(0x00100000, False, child_pid)
        assert handle
        assert kernel.WaitForSingleObject(handle, 0) == 258  # Still running.
        await asyncio.wait_for(jobs.close(), 8)
        assert kernel.WaitForSingleObject(handle, 1000) == 0  # Exited.
    finally:
        await jobs.close()
        if handle:
            kernel.CloseHandle(handle)


@pytest.mark.parametrize("background,timeout", [("yes", 10), (True, True), (True, 3601), (False, 0)])
async def test_invalid_manifest_job_options(tmp_path, background, timeout):
    folder = tmp_path / "test_plugin"
    folder.mkdir()
    (folder / "plugin.py").write_text("def run(): return 1")
    data = dict(sdk_version=1, id="test_plugin", tools=[dict(name="run", description="Test",
                    background=background, timeout_seconds=timeout)])
    (folder / "plugin.json").write_text(json.dumps(data))
    registry = InMemoryToolRegistry()
    discover(registry, tmp_path, tmp_path / "envs")
    assert await registry.get_available() == []


async def test_manifest_background_defaults_and_permissions_preserved(tmp_path):
    folder = tmp_path / "test_plugin"
    folder.mkdir()
    (folder / "plugin.py").write_text("def run(): return 1")
    data = dict(sdk_version=1, id="test_plugin", tools=[dict(name="run", description="Test",
                    background=True, permissions=["network"])])
    (folder / "plugin.json").write_text(json.dumps(data))
    registry = InMemoryToolRegistry()
    discover(registry, tmp_path, tmp_path / "envs")
    spec = await registry.get_spec("test_plugin__run")
    assert spec.background and spec.timeout_seconds == 3600
    jobs = BackgroundJobs(AsyncMock())
    engine = ToolEngine(registry, AsyncMock(), jobs=jobs)
    assert not (await engine.execute(ToolCall(spec.name), User("u"))).success
    assert not jobs._tasks
    await jobs.close()
