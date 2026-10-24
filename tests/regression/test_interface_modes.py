import hashlib
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
    QStyle,
    QStyleOptionButton,
    QVBoxLayout,
    QWidget,
)

from src.core.infrastructure.providers.event_bus import EventBus
from src.core.presentation.desktop.qt.chibi.chibi import ChibiApp
from src.core.presentation.desktop.qt.chibi.core.event_types import EventType
from src.core.presentation.desktop.qt.chibi.core.events import Event
from src.core.presentation.desktop.qt.interface_modes.controller import (
    InterfaceModeController,
)
from src.core.presentation.desktop.qt.interface_modes.herta import STATES
from src.core.presentation.desktop.qt.launcher.viewmodel import LauncherViewModel
from src.core.presentation.desktop.qt.launcher.widgets.launcher_window import (
    LauncherWindow,
)


@pytest.fixture
def rig(tmp_path):
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    runtime = ChibiApp(AsyncMock(), EventBus())
    window = QWidget()
    window.panel = QWidget(window)
    QVBoxLayout(window.panel)
    controller = InterfaceModeController(tmp_path / "interface.json")
    controller.attach_launcher(window)
    controller.bind(runtime)
    yield app, controller, runtime, window
    controller.shutdown()
    runtime.shutdown()
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_fifty_switches_and_core_preserved(rig):
    app, c, runtime, _window = rig
    root = Path(__file__).resolve().parents[2]
    protected = list((root / "data").rglob("*")) + list((root / "src/resources").glob("animations/*"))
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected if p.is_file()}
    classic = runtime.chibi_view
    chat = runtime.chat_view
    assert len(c.buttons) == 1
    assert not any(button.text() in ("Включить Герту", "Вернуть Лину")
                   for button in chat.findChildren(type(c.buttons[0])))
    chat._input.setText("unsent message")
    style = chat.styleSheet()
    initial_widgets = len(app.allWidgets())
    for index in range(50):
        c.buttons[0].click()
        assert c.mode == "herta"
        assert runtime.chibi_view is c.herta
        assert not classic._motion_timer.isActive()
        assert not classic.isVisible()
        for state in ("idle", "talk", "think", "process"):
            runtime.coordinator.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, state))
            assert c.herta.state == state
        for state in STATES:
            c.herta.set_state(state)
            assert not c.herta.frames[state].isNull()
        c.buttons[-1].click()
        assert c.mode == "lina_classic"
        assert runtime.chibi_view is classic
        assert classic._motion_timer.isActive()
        assert classic._animation_name == "process"
        assert not c.herta.frames
        assert chat.styleSheet() == style
        assert chat._input.text() == "unsent message"
        app.processEvents()
    assert len(app.allWidgets()) == initial_widgets
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == h for p, h in before.items())


def test_missing_sprite_falls_back_and_retries(rig, tmp_path):
    _, c, runtime, _ = rig
    assets = c.herta.assets
    c.herta.assets = tmp_path
    assert not c.set_mode("herta")
    assert c.mode == "lina_classic"
    assert runtime.chibi_view is c.classic
    assert "спрайт" in c.labels[0].text()
    c.herta.assets = assets
    assert c.set_mode("herta")


def test_preference_restart_and_scale(rig):
    _, c, runtime, _ = rig
    assert c.mode == "lina_classic"
    c.set_mode("herta")
    c._set_scale(1.4)
    restored = InterfaceModeController(c.path)
    assert restored.preferred == "herta"
    assert restored.scale == 1.4
    c.unbind()
    c.bind(runtime)
    assert c.mode == "herta"
    c.set_mode("lina_classic")
    assert json.loads(c.path.read_text())["mode"] == "lina_classic"


def test_disabled_and_corrupt_settings(tmp_path):
    path = tmp_path / "ui.json"
    path.write_text("broken", encoding="utf-8")
    c = InterfaceModeController(path, enabled=False)
    assert c.mode == "lina_classic"
    assert not c.set_mode("herta")
    assert path.read_text() == "broken"


def test_herta_motion_and_hidden_pause(rig):
    app, c, _, _ = rig
    c.set_mode("herta")
    view = c.herta
    assert view._motion_timer.isActive()
    assert view._motion_timer.interval() == 16  # Airborne physics is independent of idle artwork.
    view.move(300, 0)
    initial_y = view.y()
    view._advance(0.066)
    assert view.y() > initial_y  # Gravity, as in the original Lina view.
    view.walk("left")
    initial_x = view.x()
    view._advance(0.066)
    assert 0 < initial_x-view.x() <= 10  # Incremental movement, not a teleport.
    phase = view._phase
    view.hide()
    assert not view._motion_timer.isActive()
    view._advance(0.066)
    assert view._phase == phase
    view.show()
    app.processEvents()
    assert view._motion_timer.isActive()
    view.set_state("sleep")
    assert view._motion_timer.interval() == 16
    view.move(view.x(), view.screen().availableGeometry().bottom()-view.height()+1)
    view._advance(0.016)
    assert view._motion_timer.interval() == 125
    c.set_mode("lina_classic")
    assert not view._motion_timer.isActive()
    assert not view.frames


def test_fall_keeps_fast_ticks_and_stops_at_floor(rig):
    _, c, _, _ = rig
    c.set_mode("herta")
    view = c.herta
    floor = view.screen().availableGeometry().bottom()-view.height()+1
    view.move(view.x(), floor-180)
    for state in ("idle", "sleep", "talk"):
        view.move(view.x(), floor-180)
        view._velocity_y = 0
        view.set_state(state)
        view._update_motion_interval()
        assert view._motion_timer.interval() == 16
        for _ in range(100):
            previous = view.y()
            view._advance(0.016)
            assert previous <= view.y() <= floor
            if view.y() < floor:
                assert view._motion_timer.interval() == 16
        assert view.y() == floor and view._velocity_y == 0
        assert view._motion_timer.interval() == (125 if state == "sleep" else 34 if state == "talk" else 66)


def test_herta_dialog_contrast_and_classic_restore(rig):
    app, c, runtime, window = rig
    size = window.size()
    original_name = runtime.chat_view.objectName()
    c.set_mode("herta")
    dialog = QMessageBox(QMessageBox.Question, "Exit", "Are you sure you want to exit?",
                         QMessageBox.Yes | QMessageBox.No, window)
    dialog.show()
    app.processEvents()
    assert "QMessageBox QLabel { color: #f6efff" in dialog.styleSheet()
    assert dialog.grab().toImage().pixelColor(5, 5).lightness() < 60
    assert not c._backdrop.isHidden()
    assert runtime.chat_view.objectName() == "hertaChat"
    dialog.close()
    dialog.deleteLater()
    c.set_mode("lina_classic")
    assert window.size() == size
    assert c._backdrop.isHidden()
    assert runtime.chat_view.objectName() == original_name


def test_tabs_and_hide_work_without_model(tmp_path):
    app = QApplication.instance() or QApplication([])
    commands = []
    vm = LauncherViewModel(AsyncMock(), EventBus())
    vm._send_command = commands.append
    window = LauncherWindow(vm)
    c = InterfaceModeController(tmp_path / "interface.json")
    c.attach_launcher(window)
    window.show()
    original_debug = window.settings_panel.cb_debug
    original_logs = window.settings_panel.cb_logs
    try:
        original_debug.setChecked(True)
        original_logs.setChecked(True)
        commands.clear()
        c.buttons[0].click()
        assert c.mode == "herta" and c.runtime is None
        assert not vm.is_system_running()
        assert commands == []  # Changing the interface sends no Start or settings commands.
        assert c._settings_tabs.count() == 4
        assert c._desktop_button is None
        c._settings_tabs.setCurrentIndex(3)
        app.processEvents()
        assert original_debug.isVisible() and original_logs.isVisible()
        assert original_debug.isChecked() and original_logs.isChecked()
        option = QStyleOptionButton()
        original_logs.initStyleOption(option)
        checked_rect = original_logs.style().subElementRect(QStyle.SE_CheckBoxContents, option, original_logs)
        checked_size = original_logs.sizeHint()
        original_logs.setChecked(False)
        original_logs.initStyleOption(option)
        assert original_logs.style().subElementRect(QStyle.SE_CheckBoxContents, option, original_logs) == checked_rect
        assert original_logs.sizeHint() == checked_size
        assert c._settings_tabs.quit_button.parentWidget() is c._settings_tabs.layouts["general"].parentWidget()
        assert not c._settings_tabs.geometry().intersects(c._portrait.geometry())
        assert c._portrait.isVisible() and c._portrait.width() >= 210
        for _ in range(10):
            c.set_mode("lina_classic")
            assert window.settings_panel.cb_debug is original_debug
            assert original_debug.isChecked() and not original_logs.isChecked()
            assert original_debug.parentWidget() is window.settings_panel.main_panel
            c.set_mode("herta")
        c.close_button.click()
        assert not window.isVisible()
        assert c.mode == "herta"
        assert c.runtime is None
        window.show()
        window.resize(640, 900)
        app.processEvents()
        assert c.close_button.x() == window.width()-48
        assert c.close_button.isVisible()
        c.set_mode("lina_classic")
        assert not c._settings_tabs.active
        assert window.settings_panel.advanced_panel.parentWidget() is window.settings_panel.stacked_widget
    finally:
        c.set_mode("lina_classic", persist=False)
        c.shutdown()
        window._close_app()
        window.close()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_original_lina_and_herta_movies_play_and_pause(rig):
    _, c, runtime, _ = rig
    for state in ("idle", "talk", "think", "process"):
        runtime.coordinator.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, state))
        movie = runtime.chibi_view.movie()
        assert movie is not None and movie.isValid() and movie.frameCount() > 1
        assert movie.fileName().endswith(f"{state}.webp")
        assert movie.cacheMode() == QMovie.CacheNone
    c.set_mode("herta")
    assert c.herta._movie.isValid() and c.herta._movie.frameCount() == 100
    for movie in runtime.coordinator.animation_service._cache.values():
        assert movie.state() != QMovie.Running
    c.herta.set_state("talk")
    assert c.herta._movie.frameCount() == 60
    for _ in range(5):
        assert c.herta._movie.jumpToNextFrame()
    first = c.herta._movie.currentPixmap().toImage()
    for _ in range(5):
        assert c.herta._movie.jumpToNextFrame()
    assert c.herta._movie.currentPixmap().toImage() != first
    c.herta.hide()
    assert c.herta._movie.state() != QMovie.Running
    c.herta.show()
    assert c.herta._movie.state() == QMovie.Running
    c.set_mode("lina_classic")
    assert runtime.chibi_view.movie().fileName().endswith("process.webp")
    assert not runtime.chibi_view._fallback
