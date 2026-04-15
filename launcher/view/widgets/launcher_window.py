from typing import Callable
import pyaudio
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QMenu, 
                               QMessageBox, QPushButton, QSystemTrayIcon, 
                               QVBoxLayout, QWidget)
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPainterPath, QPixmap, Qt
from PySide6.QtCore import QFile, QTimer
from .settings_panel import SettingsPanel
from paths import MEDIA
from ..styles.launcher_style import get_stylesheet


class LauncherWindow(QWidget):
    def __init__(self, viewmodel):
        super().__init__()
        self.viewmodel = viewmodel
        self.pyaudio = pyaudio.PyAudio()
        self.viewmodel._apply_language()
        self.drag_offset = None
        
        self.setup_window()
        self.setup_ui()
        self.setup_tray()
        self.setup_connections()

    def retranslate_ui(self):
        self.btn_app.setText(self.tr("Start app"))
        self.btn_exit.setText(self.tr("Exit"))
        self.btn_srv.setText(self.tr("Start server"))
        self.btn_wrap.setText(self.tr("Minimize"))

    
    def setup_window(self):
        """Настройка параметров окна"""
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(400, 650)
    
    def setup_tray(self):
        """Настройка системного трея"""
        self.tray = QSystemTrayIcon(self)
        icon_path = "logo.ico"
        if QFile.exists(icon_path):
            self.tray.setIcon(QIcon(icon_path))
        else:
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.blue)
            self.tray.setIcon(QIcon(pixmap))
            
        self.tray.setToolTip("Lina")
        self.tray.setVisible(True)
        
        # Tray menu
        self.menu = QMenu()
        show_action = QAction(self.tr("Settings"))
        quit_action = QAction(self.tr("Exit"))
        self.menu.addAction(show_action)
        self.menu.addAction(quit_action)
        self.tray.setContextMenu(self.menu)
        
        show_action.triggered.connect(self.show_window)
        quit_action.triggered.connect(self.quit_app)
        self.tray.activated.connect(self.on_tray_activated)
    
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Контейнер настроек
        self.panel = QWidget()
        self.panel.setObjectName("panel")
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setSpacing(10)
        
        # Панель настроек
        self.settings_panel = SettingsPanel(self.viewmodel)
        self.settings_panel.set_pyaudio(self.pyaudio)
        self.settings_panel.populate_cameras()
        panel_layout.addWidget(self.settings_panel)
        
        # Кнопки
        self.setup_buttons(panel_layout)
        
        main_layout.addWidget(self.panel)
        self.setStyleSheet(get_stylesheet())
    
    def setup_buttons(self, layout):
        """Настройка кнопок"""
        buttons = QHBoxLayout()
        self.btn_app = QPushButton(self.tr("Start app"))
        self.btn_srv = QPushButton(self.tr("Start server"))
        self.btn_app.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_srv.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_app.clicked.connect(self.start_app)
        self.btn_srv.clicked.connect(self.start_server)
        buttons.addWidget(self.btn_app)
        buttons.addWidget(self.btn_srv)
        
        buttons_e_w = QHBoxLayout()
        self.btn_exit = QPushButton(self.tr("Exit"))
        self.btn_wrap = QPushButton(self.tr("Minimize"))
        self.btn_exit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_wrap.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_exit.clicked.connect(self.quit_app)
        self.btn_wrap.clicked.connect(self.hide)
        
        buttons_e_w.addWidget(self.btn_wrap)
        buttons_e_w.addWidget(self.btn_exit)
        
        layout.addLayout(buttons)
        layout.addLayout(buttons_e_w)
    
    def setup_connections(self):
        """Настройка соединений с сервером"""
        self.viewmodel.server_manager.server_started.connect(self.on_server_started)
        self.viewmodel.server_manager.server_stopped.connect(self.on_server_stopped)
        self.viewmodel.server_manager.server_error.connect(self.on_server_error)


        self.viewmodel.language_changed.connect(self.retranslate_ui)

    
    def paintEvent(self, event):
        """Отрисовка фона с закругленными углами"""
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 20, 20)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipPath(path)

        bg_path = f"launcher/view/bg.png"
        if QFile.exists(bg_path):
            pix = QPixmap(bg_path)
            painter.drawPixmap(self.rect(), pix)
        else:
            painter.fillRect(self.rect(), QColor(30, 30, 30, 200))
    
    def show_window(self,):
        self.show()
        self.raise_()
        self.activateWindow()


    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window()
    

    def on_server_started(self):
        self.btn_srv.setText(self.tr("Success"))
        self.btn_srv.setEnabled(False)
        self.tray.showMessage(
            "Lina AI",
            self.tr("Server started successfully"),
            QSystemTrayIcon.MessageIcon.Information,
            2000
        )
    
    def on_server_stopped(self):
        self.btn_srv.setText(self.tr("Start server"))
        self.btn_srv.setEnabled(True)

    def quit_app(self):
        self.viewmodel.kill_all.emit()
    
    def on_server_error(self, error_msg):
        self.btn_srv.setText(self.tr("Error"))
        self.btn_srv.setEnabled(True)
        QMessageBox.critical(self, self.tr("Error starting server. Check your settings."), error_msg)
    
    def start_server(self):
        if self.viewmodel.server_manager.is_running():
            return
        
        self.btn_srv.setText(self.tr("Starting"))
        self.btn_srv.setEnabled(False)
        self.viewmodel.start_server.emit()
    
    def start_app(self):
        if not self.viewmodel.server_manager.is_running():
            reply = QMessageBox.question(
                self,
                self.tr("Warning"),
                self.tr("The server needs to be running to run the application. Run now ?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.start_server()
                QTimer.singleShot(3000, self._open_app_after_server)
                return
        self._open_app()
    
    def _open_app_after_server(self):
        if self.viewmodel.server_manager.is_running():
            self.hide()
            self._open_app()
        else:
            QMessageBox.warning(
                self,
                self.tr("Error"),
                self.tr("Error starting server. Check your settings.")
            )
    
    def _open_app(self):
        try:
            self.viewmodel.start_app.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start client: {e}")
    
    def closeEvent(self, event):
        event.ignore()
        self.hide()


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.pos()


    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = self.pos() + (event.pos() - self.drag_offset)
            self.move(new_pos)

    