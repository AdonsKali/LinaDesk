from PySide6.QtCore import Qt, QTimer, QFile, Signal
from PySide6.QtGui import QAction, QCloseEvent, QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QMenu, QMessageBox, QPushButton,
    QSystemTrayIcon, QVBoxLayout, QWidget
)
from .settings_panel import SettingsPanel
from .tool_permission_dialog import ToolPermissionDialog
from ..styles.launcher_style import get_stylesheet
from src.core.utils.logger import logger
from local_paths import IMAGES


class LauncherWindow(QWidget):
    """
    Главное окно лаунчера.
    Только UI - вся логика в ViewModel.
    """
    
    restart_requested = Signal()

    def __init__(self, viewmodel):
        super().__init__()
        font = self.font()
        font.setFamily("Segoe UI")
        self.setFont(font)
        self.viewmodel = viewmodel
        self.pyaudio = None
        self.drag_offset = None
        self._is_closing = False
        self._permission_dialogs = {}
        
        # Настраиваем UI
        self._setup_window()
        self._setup_ui()
        self._setup_tray()
        
        # Подключаем сигналы
        self._connect_signals()
        
        # Обновляем состояние кнопки
        self._update_start_button()
    
    def _connect_signals(self):
        """Подключение сигналов ViewModel"""
        # Системные события
        self.viewmodel.system_start_requested.connect(self.hide)
        self.viewmodel.system_started.connect(self._on_system_started)
        self.viewmodel.system_stopped.connect(self._on_system_stopped)
        self.viewmodel.system_error.connect(self._on_system_error)
        self.viewmodel.background_job_finished.connect(self._on_background_job_finished)
        self.viewmodel.tool_permission_requested.connect(self._on_tool_permission_requested)
        self.viewmodel.tool_permission_closed.connect(self._on_tool_permission_closed)
        
        # Язык
        self.viewmodel.language_changed.connect(self._on_language_changed)
        
        # Выход из приложения - ВАЖНО!
        self.viewmodel.application_exit_requested.connect(self._on_exit_requested)
        
        # Кнопки UI -> ViewModel
        self.start_btn.clicked.connect(self.viewmodel.toggle_system)
        self.viewmodel.busy_changed.connect(lambda busy: self.start_btn.setEnabled(not busy))
        self.exit_btn.clicked.connect(self._on_exit_clicked)
        self.minimize_btn.clicked.connect(self.hide)
        
        # Настройки -> ViewModel
        self.settings_panel.debug_changed.connect(self.viewmodel.set_debug)
        self.settings_panel.log_changed.connect(self.viewmodel.set_log)
        self.settings_panel.gpu_changed.connect(self.viewmodel.set_gpu)
        self.settings_panel.economy_changed.connect(self.viewmodel.set_economy)
        self.settings_panel.language_changed.connect(self.viewmodel.set_language)
        self.settings_panel.username_changed.connect(self.viewmodel.set_username)
        
        # Расширенные настройки -> ViewModel
        self.settings_panel.advanced_panel.sandbox_changed.connect(self.viewmodel.set_sandbox)
        self.settings_panel.advanced_panel.server_mode_changed.connect(self.viewmodel.set_server_mode)
        self.settings_panel.advanced_panel.autonomy_mode_changed.connect(self.viewmodel.set_autonomy_mode)
        self.settings_panel.advanced_panel.plugins_enabled_changed.connect(self.viewmodel.set_plugins_enabled)
        self.settings_panel.advanced_panel.plugins_refresh_requested.connect(self.viewmodel.refresh_plugins)
        self.settings_panel.advanced_panel.plugin_toggled.connect(self.viewmodel.toggle_plugin)
        self.settings_panel.advanced_panel.tool_permissions_changed.connect(self.viewmodel.set_tool_permissions)
    
    def _setup_window(self):
        """Настройка окна"""
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.resize(520, 780)
        self.setMinimumSize(480, 700)
        self.setWindowTitle("Lina AI Launcher")
    
    def _setup_tray(self):
        """Настройка системного трея"""
        self.tray = QSystemTrayIcon(self)
        
        icon_path = "logo.ico"
        if QFile.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.blue)
            self.tray.setIcon(QIcon(pixmap))
        
        self.tray.setToolTip("Lina AI Launcher")
        self.tray.setVisible(True)
        
        # Меню трея
        self.tray_menu = QMenu()
        show_action = QAction(self.tr("Show"))
        quit_action = QAction(self.tr("Exit"))
        self.tray_menu.addAction(show_action)
        self.tray_menu.addAction(quit_action)
        self.tray.setContextMenu(self.tray_menu)
        
        show_action.triggered.connect(self._show_window)
        quit_action.triggered.connect(self._on_exit_clicked)
        self.tray.activated.connect(self._on_tray_activated)
    
    def _setup_ui(self):
        """Настройка UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        header = QHBoxLayout()
        header.addStretch()
        close_button = QPushButton("×")
        close_button.setAccessibleName("Скрыть в трей")
        close_button.setFixedWidth(36)
        close_button.clicked.connect(self.hide)
        header.addWidget(close_button)
        main_layout.addLayout(header)

        # Панель с настройками
        self.panel = QWidget()
        self.panel.setObjectName("panel")
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setSpacing(10)
        
        # Панель настроек
        self.settings_panel = SettingsPanel(self.viewmodel)
        self.settings_panel.set_pyaudio(self.pyaudio)
        self.settings_panel.populate_cameras()
        panel_layout.addWidget(self.settings_panel)
        
        # Кнопки управления
        self._setup_buttons(panel_layout)
        
        main_layout.addWidget(self.panel)
        self.setStyleSheet(get_stylesheet())
    
    def _setup_buttons(self, layout):
        """Настройка кнопок"""
        buttons = QVBoxLayout()
        buttons.setSpacing(8)
        
        # Основная кнопка "Запустить/Остановить"
        self.start_btn = QPushButton(self.tr("Start"))
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        buttons.addWidget(self.start_btn)
        
        # Кнопки управления окном
        controls = QHBoxLayout()
        
        self.minimize_btn = QPushButton(self.tr("Minimize"))
        self.minimize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls.addWidget(self.minimize_btn)
        
        self.exit_btn = QPushButton(self.tr("Exit"))
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls.addWidget(self.exit_btn)
        
        self.restart_button = QPushButton("Перезагрузить приложение")
        self.restart_button.clicked.connect(self.restart_requested.emit)
        buttons.addWidget(self.restart_button)
        buttons.addLayout(controls)
        layout.addLayout(buttons)
    
    # ==================== Обработчики от ViewModel ====================
    
    def _on_tool_permission_requested(self, request):
        if self._is_closing or request['request_id'] in self._permission_dialogs:
            return
        dialog = ToolPermissionDialog(request, self)
        self._permission_dialogs[request['request_id']] = dialog
        def finished(result):
            if self._permission_dialogs.pop(request['request_id'], None) is not None:
                self.viewmodel.resolve_tool_permission(request['request_id'], result == QMessageBox.StandardButton.Yes,
                                                        dialog.remember.isChecked())
            dialog.deleteLater()
        dialog.finished.connect(finished)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _on_tool_permission_closed(self, request_id):
        dialog = self._permission_dialogs.pop(request_id, None)
        if dialog is not None:
            dialog.done(QMessageBox.StandardButton.No)

    def _on_background_job_finished(self, job):
        labels = {"succeeded": "Завершено", "failed": "Ошибка", "timed_out": "Превышено время"}
        self.tray.showMessage(
            "Лина — фоновое задание",
            f"{job['tool_name']}: {labels.get(job['status'], job['status'])}",
            QSystemTrayIcon.MessageIcon.Information if job['status'] == 'succeeded' else QSystemTrayIcon.MessageIcon.Warning,
            5000,
        )

    def _on_system_started(self):
        """Система запущена"""
        self._update_start_button()
        self.tray.showMessage(
            "Lina AI",
            self.tr("System started successfully"),
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        self.hide()
    
    def _on_system_stopped(self):
        """Система остановлена"""
        self._update_start_button()
        self.tray.showMessage(
            "Lina AI",
            self.tr("System stopped"),
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
        self.show()
    
    def _on_system_error(self, error_msg):
        self.show()
        """Ошибка системы"""
        self._update_start_button()
        dialog = QMessageBox(QMessageBox.Icon.Critical, self.tr("Error"),
                             self.tr("System error: ") + error_msg,
                             QMessageBox.StandardButton.Ok, self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.open()
    

    def _on_language_changed(self, language: str):
        """Изменен язык"""
        self.retranslate_ui()
    
    def _on_exit_clicked(self):
        """Пользователь нажал Exit - делегируем ViewModel"""
        if self._is_closing:
            return
        
        # Спрашиваем подтверждение
        reply = QMessageBox.question(
            self,
            self.tr("Exit"),
            self.tr("Are you sure you want to exit?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logger.info("🛑 User confirmed exit")
            # Делегируем ViewModel
            self.viewmodel.exit_application()
    
    def _on_exit_requested(self):
        """
        Получен сигнал от ViewModel о выходе.
        Теперь можно безопасно закрывать приложение.
        """
        if self._is_closing:
            return
        
        logger.info("🔄 Exit confirmed by ViewModel, closing application...")
        self._close_app()
    
    def _on_tray_activated(self, reason):
        """Активация трея"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()
    
    # ==================== Вспомогательные методы ====================
    
    def _update_start_button(self):
        """Обновление состояния кнопки запуска"""
        if self.viewmodel.is_system_running():
            self.start_btn.setText(self.tr("Stop"))
            self.start_btn.setStyleSheet("""
                QPushButton {
                    background: rgba(220, 53, 69, 0.8);
                    padding: 12px;
                    border-radius: 10px;
                    font-size: 16px;
                    font-weight: bold;
                    color: white;
                }
                QPushButton:hover {
                    background: rgba(230, 83, 97, 1.0);
                }
            """)
        else:
            self.start_btn.setText(self.tr("Start"))
            self.start_btn.setStyleSheet("""
                QPushButton {
                    padding: 12px;
                    border-radius: 10px;
                    font-size: 16px;
                    font-weight: bold;
                    color: white;
                }
            """)
    
    def _show_window(self):
        """Показать окно"""
        self.show()
        self.raise_()
        self.activateWindow()
    
    def _close_app(self):
        """Закрытие приложения"""
        if self._is_closing:
            return
        
        self._is_closing = True
        for request_id in list(self._permission_dialogs):
            self._on_tool_permission_closed(request_id)
        logger.info("🔄 Closing application...")
        
        # Закрываем PyAudio
        if self.pyaudio:
            try:
                self.pyaudio.terminate()
                logger.info("  ✅ PyAudio terminated")
            except Exception as e:
                logger.warning(f"  ⚠️ Error terminating PyAudio: {e}")
        
        # Закрываем ViewModel
        self.viewmodel.close()
        
        # Скрываем трей
        if hasattr(self, 'tray') and self.tray:
            try:
                self.tray.setVisible(False)
                logger.info("  ✅ Tray hidden")
            except Exception as e:
                logger.warning(f"  ⚠️ Error hiding tray: {e}")
        
        # Очищаем сигналы
        self.blockSignals(True)
        
        # Закрываем приложение
        logger.info("✅ Application closed")
        self.hide()  # Application owns qasync shutdown and resource disposal.
    
    def retranslate_ui(self):
        """Обновление перевода"""
        self.start_btn.setText(
            self.tr("Stop") if self.viewmodel.is_system_running() else self.tr("Start")
        )
        self.minimize_btn.setText(self.tr("Minimize"))
        self.exit_btn.setText(self.tr("Exit"))
        self.settings_panel.retranslate_ui()
    
    # ==================== События окна ====================
    
    def paintEvent(self, event):
        """Отрисовка фона с закругленными углами"""
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 20, 20)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipPath(path)

        painter.fillRect(self.rect(), QColor("#20252b"))

    def closeEvent(self, event: QCloseEvent):
        """Закрытие окна - скрываем в трей вместо закрытия"""
        if self._is_closing:
            event.accept()
            return
        
        event.ignore()
        self.hide()
    
    def mousePressEvent(self, event):
        """Перетаскивание окна"""
        if event.button() == Qt.MouseButton.LeftButton and self.childAt(event.pos()) is None:
            self.drag_offset = event.pos()

    def mouseMoveEvent(self, event):
        """Перетаскивание окна"""
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_offset and self.childAt(event.pos()) is None:
            new_pos = self.pos() + (event.pos() - self.drag_offset)
            self.move(new_pos)
