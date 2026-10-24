import asyncio
import json
import os
from unittest.mock import AsyncMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from src.core.application.subsystems.tools.permissions import ToolPermissions
from src.core.application.subsystems.tools.engine import ToolEngine
from src.core.domain.entities.user import User
from src.core.domain.events.tool_events import ToolPermissionRequested, ToolPermissionRequestClosed
from src.core.domain.value_objects.tool import ToolSpec, ToolCall, ToolPermission
from src.core.infrastructure.providers.event_bus import EventBus
from src.core.infrastructure.services.tools.permission_store import FileToolPermissionStore
from src.core.infrastructure.services.tools.in_memory_tool_registry import InMemoryToolRegistry


def spec(permissions=(ToolPermission.NETWORK, ToolPermission.WRITE), plugin="sample"):
    return ToolSpec(plugin + "__run", "test", {}, permissions, plugin)


async def pending(permissions):
    async with asyncio.timeout(3):
        while not permissions._pending:
            await asyncio.sleep(.001)
    return next(iter(permissions._pending))


async def test_denied_and_invalid_calls_never_run_handler(tmp_path):
    bus = AsyncMock()
    permissions = ToolPermissions(FileToolPermissionStore(tmp_path / "permissions.json"), bus)
    registry = InMemoryToolRegistry()
    handler = AsyncMock(return_value="result")
    registry.register_spec(spec(), handler)
    engine = ToolEngine(registry, bus, permissions=permissions)
    user = User("test")
    assert spec().name in {s.name for s in await engine.get_available_tools()}
    assert not (await engine.execute(ToolCall(spec().name, {"extra": True}), user)).success
    assert not permissions._pending
    task = asyncio.create_task(engine.execute(ToolCall(spec().name), user))
    request_id = await pending(permissions)
    request = bus.publish.await_args_list[0].args[0]
    assert request.permissions == ["network", "write"]
    assert request.plugin_name == "sample"
    assert not handler.called
    permissions.resolve(request_id, False)
    assert not (await task).success
    handler.assert_not_called()
    assert not permissions._pending
    assert isinstance(bus.publish.await_args_list[-1].args[0], ToolPermissionRequestClosed)


async def test_one_time_remember_reload_and_revoke(tmp_path):
    path = tmp_path / "permissions.json"
    store = FileToolPermissionStore(path)
    permissions = ToolPermissions(store, AsyncMock())
    requested = spec()
    task = asyncio.create_task(permissions.authorize(requested, "u"))
    permissions.resolve(await pending(permissions), True)
    assert await task
    assert permissions.granted(requested.name) == []
    task = asyncio.create_task(permissions.authorize(requested, "u"))
    permissions.resolve(await pending(permissions), True, remember=True)
    assert await task
    reloaded = ToolPermissions(FileToolPermissionStore(path), AsyncMock())
    assert await reloaded.authorize(requested, "u")
    assert set(reloaded.granted(requested.name)) == {"network", "write"}
    reloaded.set_grants(requested.name, ["network"])
    task = asyncio.create_task(reloaded.authorize(requested, "u"))
    request_id = await pending(reloaded)
    assert reloaded._pending[request_id][2] == ["write"]
    reloaded.resolve(request_id, False)
    assert not await task
    assert not reloaded.resolve(request_id, True, True)  # Stale approvals have no effect.


async def test_timeout_stop_corrupt_store_and_builtin_impersonation(tmp_path):
    path = tmp_path / "permissions.json"
    path.write_text('{"sample__run": ["network", "invalid"]}')
    permissions = ToolPermissions(FileToolPermissionStore(path), AsyncMock(), request_timeout=.02)
    assert permissions.granted(spec().name) == []
    assert not await permissions.authorize(spec(), "u")
    assert not permissions._pending
    task = asyncio.create_task(permissions.authorize(spec(plugin="builtin"), "u"))
    await pending(permissions)
    permissions.cancel_pending()
    assert not await task
    assert not permissions._pending
    path.write_text("invalid JSON")
    assert permissions.granted(spec().name) == []


async def test_read_permission_also_requires_explicit_consent(tmp_path):
    permissions = ToolPermissions(FileToolPermissionStore(tmp_path / "permissions.json"), AsyncMock())
    task = asyncio.create_task(permissions.authorize(spec((ToolPermission.READ,)), "u"))
    request_id = await pending(permissions)
    assert permissions._pending[request_id][2] == ["read"]
    permissions.resolve(request_id, True)
    assert await task


async def test_cancel_and_launcher_grant_resolve_pending_request(tmp_path):
    bus = AsyncMock()
    permissions = ToolPermissions(FileToolPermissionStore(tmp_path / "permissions.json"), bus)
    task = asyncio.create_task(permissions.authorize(spec(), "u"))
    await pending(permissions)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not permissions._pending
    assert isinstance(bus.publish.await_args_list[-1].args[0], ToolPermissionRequestClosed)
    task = asyncio.create_task(permissions.authorize(spec(), "u"))
    await pending(permissions)
    permissions.set_grants(spec().name, ["network", "write"])
    assert await task
    assert not permissions._pending


async def test_background_job_not_queued_until_permission_is_granted(tmp_path):
    from dataclasses import replace
    from src.core.application.subsystems.tools.jobs import BackgroundJobs
    bus = AsyncMock()
    permissions = ToolPermissions(FileToolPermissionStore(tmp_path / "permissions.json"), bus)
    jobs = BackgroundJobs(bus)
    registry = InMemoryToolRegistry()
    called = asyncio.Event()
    async def handler():
        called.set()
        return "done"
    requested = replace(spec(), background=True)
    registry.register_spec(requested, handler)
    engine = ToolEngine(registry, bus, jobs=jobs, permissions=permissions)
    user = User("u")
    task = asyncio.create_task(engine.execute(ToolCall(requested.name), user))
    try:
        request_id = await pending(permissions)
        assert jobs.list(user.id) == [] and not called.is_set()
        permissions.resolve(request_id, True)
        result = await task
        job_id = json.loads(result.output)["job_id"]
        await asyncio.wait_for(called.wait(), 3)
        assert jobs.status(user.id, job_id)["tool_name"] == requested.name
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await jobs.close()


async def test_launcher_commands_validate_declared_rights(tmp_path):
    from src.core.application.handlers.settings_handler import ToolPermissionsHandler
    from src.core.application.commands.settings_commands import SetToolPermissionsCommand
    store = FileToolPermissionStore(tmp_path / "permissions.json")
    permissions = ToolPermissions(store, AsyncMock())
    catalog = AsyncMock()
    catalog.list_plugins.return_value = [{"name": "sample", "tool_specs": [dict(name="sample__run", permissions=["network"])]}]
    handler = ToolPermissionsHandler(catalog, permissions, AsyncMock())
    await handler.handle(SetToolPermissionsCommand("sample__run", ["network"]))
    assert store.get("sample__run") == ["network"]
    with pytest.raises(ValueError):
        await handler.handle(SetToolPermissionsCommand("sample__run", ["execute"]))
    with pytest.raises(ValueError):
        await handler.handle(SetToolPermissionsCommand("missing", ["network"]))
    await handler.handle(SetToolPermissionsCommand("sample__run", []))
    assert store.get("sample__run") == []


async def test_real_launcher_permission_prompt_and_live_controls(tmp_path):
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtCore import QCoreApplication, QEvent
    from src.core.infrastructure.providers.command_bus import CommandBus
    from src.core.application.handlers.settings_handler import ToolPermissionsHandler, GetPluginListHandler
    from src.core.application.commands.settings_commands import SetToolPermissionsCommand, ResolveToolPermissionCommand, GetPluginListCommand
    from src.core.presentation.desktop.qt.launcher.viewmodel import LauncherViewModel
    from src.core.presentation.desktop.qt.launcher.widgets.launcher_window import LauncherWindow
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    bus, commands = EventBus(), CommandBus()
    permissions = ToolPermissions(FileToolPermissionStore(tmp_path / "permissions.json"), bus)
    catalog = AsyncMock()
    catalog.list_plugins.return_value = [dict(name="sample", enabled=True, status="ready", tools=["sample__run"],
        tool_specs=[dict(name="sample__run", permissions=["network", "write"], description="Test tool")])]
    command_handler = ToolPermissionsHandler(catalog, permissions, bus)
    for command in (SetToolPermissionsCommand, ResolveToolPermissionCommand):
        commands.register(command, command_handler)
    commands.register(GetPluginListCommand, GetPluginListHandler(catalog, bus, permissions))
    vm = LauncherViewModel(commands, bus)
    window = LauncherWindow(vm)
    registry = InMemoryToolRegistry()
    handler = AsyncMock(return_value="worked")
    registry.register_spec(spec(), handler)
    engine = ToolEngine(registry, bus, permissions=permissions)
    await bus.start()
    task = None
    async def until(predicate):
        async with asyncio.timeout(5):
            while not predicate():
                app.processEvents()
                await asyncio.sleep(.01)
    try:
        task = asyncio.create_task(engine.execute(ToolCall(spec().name), User("u")))
        await until(lambda: bool(window._permission_dialogs))
        dialog = next(iter(window._permission_dialogs.values()))
        assert dialog.isVisible() and not dialog.isModal()
        assert "Плагин 'sample' требует разрешение" in dialog.text()
        assert "Доступ к сети" in dialog.text() and "Изменение файлов" in dialog.text()
        handler.assert_not_called()
        dialog.remember.setChecked(True)
        dialog.button(QMessageBox.StandardButton.Yes).click()
        assert (await asyncio.wait_for(task, 5)).success
        await bus.drain()
        assert not window._permission_dialogs
        assert handler.await_count == 1
        panel = window.settings_panel.advanced_panel
        assert panel.permission_checks["network"].isChecked()
        assert panel.permission_checks["write"].isChecked()
        assert not panel.permission_checks["execute"].isEnabled()
        panel.permission_checks["write"].click()
        await until(lambda: permissions.granted("sample__run") == ["network"])
        await bus.drain()
        # The next call prompts only for the right revoked in the launcher.
        task = asyncio.create_task(engine.execute(ToolCall(spec().name), User("u")))
        await until(lambda: bool(window._permission_dialogs))
        dialog = next(iter(window._permission_dialogs.values()))
        assert "Изменение файлов" in dialog.text() and "Доступ к сети" not in dialog.text()
        dialog.close()
        assert not (await asyncio.wait_for(task, 5)).success
        assert handler.await_count == 1
        task = asyncio.create_task(engine.execute(ToolCall(spec().name), User("u")))
        await until(lambda: bool(window._permission_dialogs))
        task.cancel()  # Stop cancels the active chat call in the same way.
        await asyncio.gather(task, return_exceptions=True)
        await bus.drain()
        assert not window._permission_dialogs and not permissions._pending
    finally:
        if task is not None and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        await bus.drain()
        window._is_closing = True
        vm.close()
        window.tray.hide()
        window.deleteLater()
        await bus.stop()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
