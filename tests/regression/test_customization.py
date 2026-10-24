import json
import os
from unittest.mock import AsyncMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from src.core.infrastructure.providers.event_bus import EventBus
from src.core.presentation.desktop.qt.chibi.chibi import ChibiApp
from src.core.presentation.desktop.qt.customization.controller import (
    CustomizationController,
)
from src.core.presentation.desktop.qt.launcher.viewmodel import LauncherViewModel
from src.core.presentation.desktop.qt.launcher.widgets.launcher_window import (
    LauncherWindow,
)


@pytest.fixture
def custom(tmp_path):
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    runtime = ChibiApp(AsyncMock(), EventBus())
    window = QWidget()
    window.panel = QWidget(window)
    QVBoxLayout(window.panel)
    controller = CustomizationController(tmp_path / "customization.json")
    controller.attach_launcher(window)
    controller.bind(runtime)
    yield controller, runtime
    controller.shutdown()
    runtime.shutdown()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def test_independent_combinations_and_animation_routing(custom):
    c, runtime = custom
    classic = runtime.chibi_view
    runtime.chat_view._input.setText("draft")
    original_style = runtime.chat_view.styleSheet()
    for _ in range(3):
        for interface in ("herta", "lina_classic"):
            c.interface_combo.setCurrentIndex(c.interface_combo.findData(interface))
            for character in ("herta", "lina_classic"):
                c.character_combo.setCurrentIndex(c.character_combo.findData(character))
                assert c.mode == interface
                assert c.character == character
                assert runtime.chibi_view is (c.herta if character == "herta" else classic)
                c._state_changed("talk")
                assert (c.herta.state if character == "herta" else classic._animation_name) == "talk"
                assert runtime.chat_view._input.text() == "draft"
    assert runtime.chat_view.styleSheet() == original_style
    assert not c.buttons


def test_restore_and_runtime_restart(custom):
    c, runtime = custom
    c.set_mode("lina_classic")
    c.set_character("herta")
    c._set_scale(1.2)
    restored = CustomizationController(c.path)
    assert restored.preferred == "lina_classic"
    assert restored.character == "herta"
    assert restored.scale == 1.2
    c.unbind()
    assert runtime.chibi_view is not None
    c.bind(runtime)
    assert c.mode == "lina_classic"
    assert runtime.chibi_view is c.herta


def test_offline_legacy_preferences(tmp_path):
    app = QApplication.instance() or QApplication([])
    legacy = tmp_path / "legacy.json"
    legacy.write_text(json.dumps({"mode": "herta", "herta_scale": 1.3}))
    before = legacy.read_bytes()
    c = CustomizationController(tmp_path / "new.json", legacy_path=legacy)
    window = QWidget()
    window.panel = QWidget(window)
    QVBoxLayout(window.panel)
    c.attach_launcher(window)
    assert c.mode == c.character == "herta"
    c.character_combo.setCurrentIndex(0)
    assert c.character == "lina_classic" and c.mode == "herta"
    c.interface_combo.setCurrentIndex(0)
    assert c.mode == "lina_classic"
    assert legacy.read_bytes() == before
    assert json.loads(c.path.read_text())["character"] == "lina_classic"
    c.shutdown()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert app is not None


def test_original_settings_and_offline_controls(tmp_path):
    app = QApplication.instance() or QApplication([])
    commands = []
    vm = LauncherViewModel(AsyncMock(), EventBus())
    vm._send_command = commands.append
    window = LauncherWindow(vm)
    c = CustomizationController(tmp_path / "ui.json")
    original_margins = window.layout().contentsMargins()
    c.attach_launcher(window)
    window.show()
    debug = window.settings_panel.cb_debug
    debug.setChecked(True)
    commands.clear()
    try:
        for mode in ("herta", "lina_classic") * 3:
            c.interface_combo.setCurrentIndex(c.interface_combo.findData(mode))
            app.processEvents()
            assert c.mode == mode
            assert c.character == "lina_classic"
            assert c.interface_combo.isVisible() and c.character_combo.isVisible()
            assert debug.isChecked()
            assert commands == []  # Appearance changes do not dispatch settings commands.
            assert c._settings_tabs.count() == 3
            if mode == "herta":
                assert c.customization_panel.parentWidget() is c._settings_tabs.layouts["general"].parentWidget()
                assert c.restart_button.parentWidget() is window.panel
                assert c.quit_button.parentWidget() is window.panel
                c._settings_tabs.setCurrentIndex(1)
                app.processEvents()
                assert debug.isVisible()
                assert c.restart_button.isVisible() and c.quit_button.isVisible()
                c._settings_tabs.setCurrentIndex(2)
                app.processEvents()
                advanced = window.settings_panel.advanced_panel
                assert advanced.plugins_list.isVisible()
                assert advanced.refresh_btn.isVisible()
                assert not debug.isVisible()
                assert c._portrait.isHidden()
                assert not c._backdrop.artwork.isNull()
                assert window.panel.width() == max(280, min(440, round(window.width()*.34)))
                assert abs(window.width()/window.height()-1.5) < .02
                widths = [c._settings_tabs.tabBar().tabRect(i).width() for i in range(3)]
                assert max(widths)-min(widths) <= 1
                c._settings_tabs.setCurrentIndex(0)
            commands.clear()  # Leaving the name field can commit it via editingFinished.
            if mode == "lina_classic":
                assert window.layout().contentsMargins() == original_margins
            assert not vm.is_system_running()
        assert debug.parentWidget() is window.settings_panel.main_panel
    finally:
        c.shutdown()
        window._close_app()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
