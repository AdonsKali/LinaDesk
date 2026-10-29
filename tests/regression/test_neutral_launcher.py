import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from unittest.mock import AsyncMock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtTest import QSignalSpy
from src.core.infrastructure.providers.event_bus import EventBus
from src.core.presentation.desktop.qt.launcher.viewmodel import LauncherViewModel
from src.core.presentation.desktop.qt.launcher.widgets.launcher_window import LauncherWindow
from src.core.presentation.desktop.qt.launcher.widgets.settings_panel import SettingsPanel

def test_neutral_launcher(tmp_path):
    app = QApplication.instance() or QApplication([])
    if os.name == "nt":
        QFontDatabase.addApplicationFont("C:/Windows/Fonts/segoeui.ttf")
        app.setFont(QFont("Segoe UI", 10))
    vm = LauncherViewModel(AsyncMock(), EventBus())
    with patch.object(SettingsPanel, 'populate_cameras'), patch.object(SettingsPanel, 'set_pyaudio'):
        window = LauncherWindow(vm)
    try:
        window.show()
        app.processEvents()
        p = window.settings_panel
        assert [p.tabs.tabText(i) for i in range(3)] == ['Общие', 'Настройки', 'Плагины']
        changed = QSignalSpy(p.username_changed)
        p.user_input.setText('Example')
        with patch.object(vm, "_send_command"):
            p.user_input.editingFinished.emit()
        assert changed.count() == 1
        for i in range(3):
            p.tabs.setCurrentIndex(i)
            app.processEvents()
            assert window.start_btn.isVisible() and window.restart_button.isVisible()
        assert p.user_input.text() == 'Example'
        assert not p.advanced_panel.server_check.isEnabled()
        assert p.advanced_panel.permission_tool_combo.isVisible()
        restart = QSignalSpy(window.restart_requested)
        window.restart_button.click()
        assert restart.count() == 1
        p.tabs.setCurrentIndex(1)
        app.processEvents()
        window.grab().save(str(tmp_path / 'neutral-launcher.png'))
    finally:
        window._close_app()
        window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
