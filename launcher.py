import time
import pyaudio
import cv2
from server_manager import ServerManager
from app_ import start_app
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from paths import MEDIA


class Launcher(QWidget):
    def __init__(self, viewmodel):
        super().__init__()
        self.pyaudio = pyaudio.PyAudio()
        self.viewmodel = viewmodel
        self.setWindowFlags(
            Qt.Window |                    
            Qt.FramelessWindowHint |        
            Qt.WindowStaysOnTopHint
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 650)


        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon("logo.ico"))
        self.tray.setToolTip("Lina")
        self.tray.setVisible(True)
        
        #Tray menu
        self.menu = QMenu()
        show_action = QAction("Показать окно")
        quit_action = QAction("Выход")
        self.menu.addAction(show_action)
        self.menu.addAction(quit_action)
        self.tray.setContextMenu(self.menu)

        # при клике по иконке – показываем окно
        self.tray.show()
        show_action.triggered.connect(self.show_window)
        quit_action.triggered.connect(self.quit_app)
        self.tray.activated.connect(self.on_tray_activated)

        # ==============================
        # Основной layout с отступами ==
        # ==============================
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)

        # Контейнер настроек
        self.panel = QWidget()
        self.panel.setObjectName("panel")
        panel_layout = QVBoxLayout(self.panel)

        panel_layout.setSpacing(10)
        self.label_lina = QLabel("Настройки Лины")
        font = QFont("Arial", 20)
        font.setBold(True)
        self.label_lina.setFont(font)
        self.label_lina.setObjectName('label_lina')
        self.label_lina.setAlignment(Qt.AlignCenter)


        panel_layout.addWidget(self.label_lina)
        panel_layout.setSpacing(10)
        panel_layout.addWidget(QLabel("Параметры запуска"))

        check_box_panel = QGridLayout()
        check_box_panel.setColumnMinimumWidth(2, 2)
        check_box_panel.setVerticalSpacing(10)


        self.cb_debug = QCheckBox("Дебаг")
        self.cb_logs = QCheckBox("Логи")
        self.cb_gpu = QCheckBox("GPU")
        self.cb_eco = QCheckBox("Экономия")


        self.cb_logs.toggled.connect(self.viewmodel.log)
        self.cb_debug.toggled.connect(self.viewmodel.debug)
        self.cb_gpu.toggled.connect(self.viewmodel.gpu)
        self.cb_eco.toggled.connect(self.viewmodel.eco)

        # ViewModel → UI
        self.viewmodel.enable_logging_changed.connect(self.cb_logs.setChecked)
        self.viewmodel.debug_mode_changed.connect(self.cb_debug.setChecked)
        self.viewmodel.use_gpu_changed.connect(self.cb_gpu.setChecked)
        self.viewmodel.use_economy_changed.connect(self.cb_eco.setChecked)

        
        check_box_panel.addWidget(self.cb_debug)
        check_box_panel.addWidget(self.cb_logs)
        check_box_panel.addWidget(self.cb_gpu)
        check_box_panel.addWidget(self.cb_eco)


        panel_layout.addLayout(check_box_panel)
        panel_layout.addSpacing(10)


        #Языки 
        panel_layout.addWidget(QLabel("Язык"))
        self.rb_ru = QRadioButton("Русский")
        self.rb_en = QRadioButton("Английский")

        panel_layout.addWidget(self.rb_ru)
        panel_layout.addWidget(self.rb_en)

        self.rb_en.toggled.connect(self.viewmodel.change_language_ru)
        self.rb_en.toggled.connect(self.viewmodel.change_language_en)

        self.viewmodel.update_language_ru.connect(self.rb_ru.setChecked)
        self.viewmodel.update_language_en.connect(self.rb_en.setChecked)

        panel_layout.addSpacing(15)

        #Имя пользователя
        panel_layout.addWidget(QLabel("Имя пользователя"))
        self.user = QLineEdit()
        panel_layout.addWidget(self.user)

        #Микрофон и камера
        panel_layout.addSpacing(10)
        panel_layout.addWidget(QLabel("Микрофон"))
        self.combo_mic = QComboBox()
        for i in range(self.pyaudio.get_device_count()):
            device_info = self.pyaudio.get_device_info_by_index(i)
            if 'microphone' in device_info['name'].lower():
                device_name = device_info['name']                
                self.combo_mic.addItem(f'Device {i}: {device_name}')
        panel_layout.addWidget(self.combo_mic)

        panel_layout.addSpacing(10)
        panel_layout.addWidget(QLabel("Камера"))
        self.cameras = self.list_cameras_opencv()
        self.combo_cam = QComboBox()
        for cam in self.cameras:
            self.combo_cam.addItem('Камера ' + str(cam['index']+1))
        panel_layout.addWidget(self.combo_cam)

        panel_layout.addStretch()

        # кнопки
        buttons = QHBoxLayout()
        self.btn_app = QPushButton("Запуск приложения")
        self.btn_srv = QPushButton("Запуск сервера")
        self.btn_app.setCursor(Qt.PointingHandCursor)
        self.btn_srv.setCursor(Qt.PointingHandCursor)
        self.btn_app.clicked.connect(self.start_app)
        self.btn_srv.clicked.connect(self.start_server)
        buttons.addWidget(self.btn_app)
        buttons.addWidget(self.btn_srv)

        buttons_e_w = QHBoxLayout()

        self.btn_exit = QPushButton("Выход")
        self.btn_wrap = QPushButton("Свернуть")
        self.btn_exit.setCursor(Qt.PointingHandCursor)
        self.btn_wrap.setCursor(Qt.PointingHandCursor)

        buttons_e_w.addWidget(self.btn_wrap)
        buttons_e_w.addWidget(self.btn_exit)

        self.btn_exit.clicked.connect(lambda: self.quit_app())
        self.btn_wrap.clicked.connect(lambda: self.hide())

        panel_layout.addLayout(buttons)
        panel_layout.addLayout(buttons_e_w)

        main.addWidget(self.panel)


        self.setStyleSheet("""
        QWidget {
            color: white;
            font-size: 14px;
        }

        #panel {
            background: rgba(0,0,0,0.55);
            border-radius: 16px;           
            padding: 14px;
        }

        QLineEdit {
            background: rgba(255,255,255,0.3);
            padding:6px;
            border-radius: 8px;
        }

        QComboBox {
            background: rgba(255,255,255,0.3);
            padding:6px;
            border-radius: 8px;
        }

        QPushButton {
            background: rgba(255,255,255,0.2);
            padding:8px;
            border-radius: 10px;
                           
        }
        QPushButton:hover {
            background: rgba(255,255,255,0.3);
        }
        
        QPushButton:pressed {
            background: rgba(255,255,255,0.6);
        }
        """)
        self.server_manager = ServerManager()
        self.setup_server_connections()
        QTimer.singleShot(1000, self.check_server_on_start)
        self.sync_from_vm()
    #Синхронизируем UI и модель данных 
    def sync_from_vm(self):
        self.cb_logs.setChecked(self.viewmodel.get_log())
        self.cb_debug.setChecked(self.viewmodel.get_debug())
        self.cb_gpu.setChecked(self.viewmodel.get_gpu())
        self.cb_eco.setChecked(self.viewmodel.get_eco())


        if self.viewmodel.get_language() == 'ru':
            self.rb_en.setChecked(True)
        else:
            self.rb_ru.setChecked(True)


    # === переопределяем paintEvent чтобы рисовать фон ===
    def paintEvent(self, event):
        path = QPainterPath()
        path.addRoundedRect(self.rect(), 20, 20)   # ← радиус

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        painter.setClipPath(path)

        # фон-картинка
        pix = QPixmap(f"{MEDIA}/bg.png")
        painter.drawPixmap(self.rect(), pix)


    def list_cameras_opencv(self, max_test=10):
        """Проверяет доступные камеры через OpenCV"""
        available_cameras = []
        
        for i in range(max_test):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                # Получаем информацию о камере
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                codec = int(cap.get(cv2.CAP_PROP_FOURCC))
                
                # Конвертируем FOURCC код в строку
                codec_str = "".join([chr((codec >> 8 * i) & 0xFF) for i in range(4)])
                
                available_cameras.append({
                    'index': i,
                    'resolution': f"{width}x{height}",
                    'fps': fps,
                    'codec': codec_str,
                    'backend': 'OpenCV'
                })
                
                cap.release()
        
        return available_cameras
    

    def show_window(self,):
        self.show()
        self.raise_()
        self.activateWindow()


    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()


    def setup_server_connections(self):
        self.server_manager.server_started.connect(self.on_server_started)
        self.server_manager.server_stopped.connect(self.on_server_stopped)
        self.server_manager.server_error.connect(self.on_server_error)
    

    def check_server_on_start(self):
        if self.server_manager.is_running():
            self.btn_srv.setText("Сервер запущен ✓")
            self.btn_srv.setEnabled(False)
    

    def on_server_started(self):
        self.btn_srv.setText("Сервер запущен ✓")
        self.btn_srv.setEnabled(False)
        self.tray.showMessage(
            "Lina AI",
            "Сервер успешно запущен",
            QSystemTrayIcon.Information,
            2000
        )
    
    def on_server_stopped(self):
        self.btn_srv.setText("Запуск сервера")
        self.btn_srv.setEnabled(True)

    def quit_app(self):
        self.viewmodel.save_all()
        self.server_manager.stop()
        time.sleep(0.3)
        QApplication.exit(1)
    
    def on_server_error(self, error_msg):
        self.btn_srv.setText("Ошибка запуска")
        self.btn_srv.setEnabled(True)
        QMessageBox.critical(self, "Ошибка сервера", error_msg)
    
    def start_server(self):
        """Запуск сервера (неблокирующий)"""
        if self.server_manager.is_running():
            return
        
        self.btn_srv.setText("Запуск...")
        self.btn_srv.setEnabled(False)
        self.server_manager.start()
    
    def start_app(self):
        if not self.server_manager.is_running():
            reply = QMessageBox.question(
                self,
                "Сервер не запущен",
                "Для работы приложения нужен сервер. Запустить сейчас?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.start_server()
                QTimer.singleShot(3000, self._open_app_after_server)
                return
            else:
                return
        self._open_app()
    
    def _open_app_after_server(self):
        if self.server_manager.is_running():
            self.hide()
            start_app()
        else:
            QMessageBox.warning(
                self,
                "Ошибка",
                "Сервер не запустился. Проверьте настройки."
            )
    
    def _open_app(self):
        self.hide()
        start_app()
    
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


    def change_lang(self):
        if self.rb_ru.isChecked():
            self.viewmodel.change_language('ru')
        else:
            self.viewmodel.change_language('en')