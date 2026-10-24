import asyncio
import os
import threading
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from dependency_injector import providers
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication, QEvent
from qasync import QEventLoop
from shiboken6 import isValid
from src.bootstrap.app import Application
from src.bootstrap.di import ApplicationContainer
from src.core.domain.events.system_events import SystemStopped, SystemStarted, SystemError
from src.core.domain.value_objects.settings import Settings
from src.core.application.commands.system_commands import StartSystemCommand, StopSystemCommand
from src.core.infrastructure.providers.event_bus import EventBus
from src.core.infrastructure.repositories.file_settings_repository import FileSettingsRepository
from src.core.infrastructure.repositories.json_state_repositories import JsonLinaRepository, JsonUserRepository, JsonSessionRepository
from src.core.infrastructure.repositories.sqlite_memory_repository import SQLiteMemoryRepository
from src.core.infrastructure.repositories.file_emotion_history_repository import FileEmotionHistoryRepository
from src.core.presentation.desktop.qt.launcher.viewmodel import LauncherViewModel


@pytest.fixture(scope="session")
def qt_app():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


@pytest.mark.parametrize("reason", ["stop", "user_request", "error", "exit"])
async def test_stopped_updates_model_for_every_reason(qt_app, reason):
    bus = EventBus()
    vm = LauncherViewModel(AsyncMock(), bus)
    signals = []
    vm.system_stopped.connect(lambda: signals.append("stopped"))
    vm.application_exit_requested.connect(lambda: signals.append("exit"))
    await vm._on_system_started(SystemStarted(boot_time_ms=0, components=[], settings={}))
    await vm._on_system_stopped(SystemStopped(uptime_seconds=0, reason=reason))
    assert not vm.is_system_running()
    assert signals == ["exit" if reason == "exit" else "stopped"]
    vm.close()
    assert bus.get_stats()["handlers_count"] == 0


async def test_event_bus_sync_handlers_stay_on_ui_thread():
    bus = EventBus()
    thread_ids = []
    bus.subscribe(SystemStopped, lambda _: thread_ids.append(threading.get_ident()))
    await bus.start()
    await bus.publish(SystemStopped(uptime_seconds=0, reason="stop"))
    await bus.drain()
    await bus.stop()
    assert thread_ids == [threading.get_ident()]


async def test_background_completion_notification_and_unsubscribe(qt_app):
    from src.core.domain.events.tool_events import BackgroundJobFinished
    bus = EventBus()
    vm = LauncherViewModel(AsyncMock(), bus)
    received = []
    vm.background_job_finished.connect(received.append)
    await bus.start()
    try:
        await bus.publish(BackgroundJobFinished(job_id="id", tool_name="test", user_id="u", status="succeeded"))
        await bus.publish(BackgroundJobFinished(job_id="cancel", tool_name="test", user_id="u", status="cancelled"))
        await bus.drain()
        assert len(received) == 1 and received[0]["status"] == "succeeded"
        vm.close()
        assert bus.get_stats()["handlers_count"] == 0
    finally:
        vm.close()
        await bus.stop()


@pytest.mark.parametrize("enabled,layers,expected", [(False, -1, 0), (True, 0, -1), (True, -1, -1), (True, 10, -1), (False, 10, 0)])
def test_gpu_configuration(enabled, layers, expected):
    settings = Settings.default()
    settings.on_gpu = enabled
    settings.llm.n_gpu_layers = layers
    container = ApplicationContainer()
    container.set_settings(settings)
    assert container.get_llm_client().n_gpu_layers == expected


def prepare(app, path, llm):
    container = app._container.container
    container.settings_repo.override(providers.Object(FileSettingsRepository(str(path / "settings.json"))))
    container.lina_repo.override(providers.Object(JsonLinaRepository(str(path / "lina.json"))))
    container.user_repo.override(providers.Object(JsonUserRepository(str(path / "user.json"))))
    container.session_repo.override(providers.Object(JsonSessionRepository(str(path / "sessions"))))
    container.memory_repo.override(providers.Object(SQLiteMemoryRepository(str(path / "memory.sqlite3"))))
    container.emotion_history_repo.override(providers.Object(FileEmotionHistoryRepository(data_dir=str(path / "emotions"))))
    container.llm.override(providers.Object(llm))


async def test_interface_and_diagnostics_without_starting_model(qt_app, tmp_path, monkeypatch):
    from . import local_paths
    monkeypatch.setattr(local_paths, "BASE_DIR", tmp_path)
    app = Application(qt_app=qt_app)
    llm = SimpleNamespace(initialize=AsyncMock(), close=AsyncMock())
    prepare(app, tmp_path, llm)
    running = asyncio.create_task(app.run())
    try:
        await until(lambda: app._interface_modes is not None)
        c = app._interface_modes
        window = app._launcher._window
        vm = app._launcher._viewmodel
        c.interface_combo.setCurrentIndex(c.interface_combo.findData("herta"))
        assert c.mode == "herta" and app._chibi_app is None
        c._settings_tabs.setCurrentIndex(1)
        window.settings_panel.cb_debug.setChecked(True)
        window.settings_panel.cb_logs.setChecked(True)
        await until(lambda: vm._settings.get("on_debug") and vm._settings.get("on_log"))
        saved = await app._container.get_settings_repo().get()
        assert saved.on_debug and saved.on_log
        c.interface_combo.setCurrentIndex(c.interface_combo.findData("lina_classic"))
        c.interface_combo.setCurrentIndex(c.interface_combo.findData("herta"))
        assert window.settings_panel.cb_debug.isChecked()
        assert window.settings_panel.cb_logs.isChecked()
        c.close_button.click()
        assert not window.isVisible()
        llm.initialize.assert_not_called()
        assert not vm.is_system_running()
        c.restart_button.click()
        c.restart_button.click()
        assert app.restart_requested
        assert not c.restart_button.isEnabled()
        await asyncio.wait_for(running, 8)
    finally:
        if not running.done():
            running.cancel()
            await asyncio.gather(running, return_exceptions=True)
        await app.shutdown()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        qt_app.processEvents()


async def until(predicate):
    async with asyncio.timeout(8):
        while not predicate():
            await asyncio.sleep(.01)


@pytest.mark.parametrize("scenario", ["restart", "exit_during_start", "exit_before_start", "failed_start", "exit_during_generation", "close_error", "autonomous"])
def test_real_qt_application_lifecycle(qt_app, tmp_path, scenario):
    loop = QEventLoop(qt_app)
    asyncio.set_event_loop(loop)

    async def run():
        app = Application(qt_app=qt_app)
        entered = asyncio.Event()

        async def initialize():
            entered.set()
            if scenario == "exit_during_start":
                await asyncio.Event().wait()
            if scenario == "failed_start":
                raise RuntimeError("bad model")

        llm = SimpleNamespace(initialize=initialize, close=AsyncMock())
        prepare(app, tmp_path, llm)
        if scenario == "close_error":
            llm.close.side_effect = RuntimeError("native close failed")
        if scenario == "autonomous":
            settings = Settings.default()
            settings.autonomy = "autonomous"
            await app._container.get_settings_repo().save(settings)
        running = asyncio.create_task(app.run())
        try:
            await until(lambda: app._launcher is not None)
            window = app._launcher._window
            # Do not open a blocking error dialog during headless regression tests.
            vm = app._launcher._viewmodel
            vm.system_error.disconnect(window._on_system_error)
            errors = []
            vm.system_error.connect(errors.append)
            bus = app._container.get_command_bus()
            if scenario != "exit_before_start":
                await bus.send(StartSystemCommand())
                await entered.wait()
            if scenario == "restart":
                for index in range(2):
                    await until(lambda: vm.is_system_running())
                    assert window.start_btn.text() == "Stop"
                    await bus.send(StopSystemCommand())
                    await until(lambda: app._stop_task is not None and app._stop_task.done())
                    assert not vm.is_system_running()
                    assert window.start_btn.text() == "Start"
                    assert window.isVisible()
                    assert app._chibi_app is None
                    if index == 0:
                        await bus.send(StartSystemCommand())
            if scenario == "failed_start":
                await until(lambda: bool(errors))
                assert "bad model" in errors[0]
                assert not vm.is_system_running()
            if scenario in ("exit_during_generation", "close_error", "autonomous"):
                await until(lambda: vm.is_system_running())
            if scenario == "exit_during_generation":
                api = app._chibi_app.coordinator.api_service
                active = asyncio.Event()
                drained = []
                async def generate():
                    async with app._container.container.gate().lock:
                        active.set()
                        try:
                            await asyncio.Event().wait()
                        finally:
                            await asyncio.sleep(.01)
                            drained.append(True)
                task = asyncio.create_task(generate())
                api._tasks.add(task)
                await active.wait()
            vm.exit_application()
            await asyncio.wait_for(running, 8)
            await app.shutdown()
            await app.shutdown()  # idempotent
            assert not isValid(window) or not window.tray.isVisible()
            assert not app.is_system_ready()
            assert not app._event_bus.get_stats()["is_running"]
            if scenario == "exit_during_generation":
                assert drained == [True] and task.cancelled()
        finally:
            if not running.done():
                running.cancel()
                await asyncio.gather(running, return_exceptions=True)
            await app.shutdown()

    try:
        loop.run_until_complete(run())
    finally:
        # Destroy deferred Qt objects while their owning qasync loop still exists.
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        qt_app.processEvents()
        loop.close()
        asyncio.set_event_loop(None)


def test_entrypoint_process_actually_exits(tmp_path):
    code = '''
import sys
import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
sys.path.insert(0, "tests/regression")
from test_runtime import prepare, until
import main
from src.core.application.commands.system_commands import StartSystemCommand
Base = main.Application
class SmokeApplication(Base):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        prepare(self, Path(sys.argv[1]), SimpleNamespace(initialize=AsyncMock(), close=AsyncMock()))
    async def run(self):
        async def exit_after_start():
            await until(lambda: self._launcher is not None)
            await self._container.get_command_bus().send(StartSystemCommand())
            await until(lambda: self._is_system_ready)
            self._launcher._viewmodel.exit_application()
        task = asyncio.create_task(exit_after_start())
        await super().run()
        await task
main.Application = SmokeApplication
main.main()
print("PROCESS_EXIT_OK")
'''
    result = subprocess.run([sys.executable, "-c", code, str(tmp_path)],
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"},
        capture_output=True, text=True, encoding="utf-8", timeout=20)
    assert result.returncode == 0, result.stderr
    assert "PROCESS_EXIT_OK" in result.stdout
    assert "Traceback" not in result.stderr


async def test_start_click_hides_launcher_before_initialized(qt_app, monkeypatch):
    from src.core.presentation.desktop.qt.launcher.widgets.launcher_window import LauncherWindow
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: None)
    vm = LauncherViewModel(AsyncMock(), EventBus())
    window = LauncherWindow(vm)
    window.show()
    assert window.isVisible()
    window.start_btn.click()
    assert not window.isVisible()
    assert not window.start_btn.isEnabled()
    await vm._on_system_error(SystemError(error="test failure"))
    assert window.isVisible()
    assert window.start_btn.isEnabled()
    assert not hasattr(window.settings_panel.advanced_panel, "model_path")
    assert window.settings_panel.cb_gpu.isVisible()
    assert window.settings_panel.cb_gpu.text() == "Видеокарта"
    window._close_app()
    window.close()
    vm.close()
    await asyncio.sleep(0)


async def test_camera_selection_persists_device_id(qt_app, monkeypatch):
    from PySide6.QtCore import QObject, Signal
    from src.core.presentation.desktop.qt.launcher.widgets.settings_panel import SettingsPanel
    class Devices(QObject):
        videoInputsChanged = Signal()
        @staticmethod
        def videoInputs():
            return [SimpleNamespace(description=lambda: "Webcam", id=lambda: b"camera-id")]
    monkeypatch.setitem(sys.modules, "PySide6.QtMultimedia", SimpleNamespace(QMediaDevices=Devices))
    vm = LauncherViewModel(AsyncMock(), EventBus())
    sent = []
    monkeypatch.setattr(vm, "_send_command", sent.append)
    panel = SettingsPanel(vm)
    panel.populate_cameras()
    panel.cam_combo.setCurrentIndex(1)
    assert sent[-1].field == "camera"
    assert sent[-1].value == b"camera-id".hex()
    panel._sync_devices({"camera": sent[-1].value})
    assert panel.cam_combo.currentText() == "Webcam"
    panel.close()
    vm.close()


async def test_plugin_panel_updates_do_not_emit_commands(qt_app):
    from src.core.presentation.desktop.qt.launcher.widgets.advanced_settings import AdvancedSettingsPanel
    vm = LauncherViewModel(AsyncMock(), EventBus())
    panel = AdvancedSettingsPanel(vm)
    changes = []
    refreshes = []
    panel.plugin_toggled.connect(lambda *args: changes.append(args))
    panel.plugins_refresh_requested.connect(lambda: refreshes.append(True))
    panel.update_plugins([{"name": "example", "enabled": True, "status": "ready", "editable": True}])
    assert not changes
    from PySide6.QtCore import Qt
    panel.plugins_list.item(0).setCheckState(Qt.CheckState.Unchecked)
    assert changes == [("example", False)]
    panel.refresh_btn.click()
    assert refreshes == [True]
    assert panel.plugins_enabled_check.isEnabled()
    panel.close()
    vm.close()


@pytest.mark.parametrize("enabled", [True, False])
def test_global_plugin_switch_controls_discovery(enabled):
    container = ApplicationContainer()
    settings = Settings.default()
    settings.on_plugins = enabled
    container.set_settings(settings)
    registry = container.container.tool_registry()
    assert ("text_utils__word_count" in registry._specs) == enabled
    assert "echo" in registry._specs
