from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, 
                                QGridLayout, QHBoxLayout, QLabel, 
                                QLineEdit, QRadioButton, QStackedWidget, 
                                QVBoxLayout, QPushButton, QWidget)
from PySide6.QtGui import QFont, Qt 
from .advanced_settings import AdvancedSettings
from launcher.utils.camera import list_cameras_opencv


class SettingsPanel(QWidget):
    def __init__(self, viewmodel):
        super().__init__()
        self.viewmodel = viewmodel
        self.pyaudio = None
        self.setup_ui()
        self.connect_signals()
        self.sync_from_viewmodel()
    
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        self.back_button = QPushButton("<-" + self.tr("Back"))
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.hide()
        self.back_button.clicked.connect(self.show_main_settings)
        self.stacked_widget = QStackedWidget()
        
        self.main_panel = QWidget()
        self.setup_main_panel()
        

        self.advanced_panel = AdvancedSettings()
        self.stacked_widget.addWidget(self.main_panel)
        self.stacked_widget.addWidget(self.advanced_panel)
        
        main_layout.addWidget(self.back_button)
        main_layout.addWidget(self.stacked_widget)
    
    def setup_main_panel(self):
        layout = QVBoxLayout(self.main_panel)
        layout.setSpacing(10)
        
        self.label_lina = QLabel(self.tr("Lina settings"))
        font = QFont("Arial", 20)
        font.setBold(True)
        self.label_lina.setFont(font)
        self.label_lina.setObjectName('label_lina')
        self.label_lina.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label_lina)
        self.lina_options = QLabel(self.tr("Launch options"))
        layout.addWidget(self.lina_options)
        
        self.setup_checkboxes(layout)
        self.setup_language_controls(layout)

        self.user_label = QLabel(self.tr("Username"))
        layout.addWidget(self.user_label)
        self.user = QLineEdit()
        self.user.setToolTip(
            self.tr("<b>User</b><br>"
                   "Ведите Ваше имя для того, чтобы Лина к вам обращалась<br>")
        )
        self.user.setText(self.viewmodel.get_user()) 
        layout.addWidget(self.user)
        
        # Микрофон и камера
        self.microphone = QLabel(self.tr("Microphone"))
        layout.addWidget(self.microphone)
        self.mic_combo = QComboBox()
        self.mic_combo.setToolTip(
            self.tr("<b>Microphone</b><br>"
                   "Выберите устройство для записи звука<br>")

        )
        layout.addWidget(self.mic_combo)
        
        self.camera = QLabel(self.tr("Camera"))
        layout.addWidget(self.camera)
        self.camera_combo = QComboBox()
        self.camera_combo.setToolTip(
            self.tr("<b>Camera</b><br>"
                   "Выберите устройство для захвата изображения<br>")
        )
        layout.addWidget(self.camera_combo)

        self.advanced_settings = QPushButton(self.tr("Advanced settings"))
        self.advanced_settings.pressed.connect(self.show_advanced_settings)
        self.advanced_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.advanced_settings)
        
        layout.addStretch()
    
    def setup_checkboxes(self, layout):
        """Настройка чекбоксов с подсказками"""
        self.cb_debug = QCheckBox(self.tr("Debug"))
        self.cb_debug.setToolTip(
            self.tr("<b>Debug</b><br>"
                   "Включает детальное логирование<br>"
                   "<i>• Подробные сообщения в консоли</i><br>"
                   "<i>• Отладочная информация</i><br>")
        )
        
        self.cb_logs = QCheckBox(self.tr("Logs"))
        self.cb_logs.setToolTip(
            self.tr("<b>Logs</b><br>"
                   "Сохранять логи в файл<br>"
                   "<i>• Файлы сохраняются в log.txt/</i><br>")
        )
        
        self.cb_gpu = QCheckBox(self.tr("GPU"))
        self.cb_gpu.setToolTip(
            self.tr("<b>GPU</b><br>"
                   "Использовать видеокарту для ускорения<br>"
                   "<i>• Требуется CUDA</i><br>"
                   "<i>• Поддерживается NVIDIA</i><br>")
        )
        
        self.cb_eco = QCheckBox(self.tr("Economy"))
        self.cb_eco.setToolTip(
            self.tr("<b>Economy</b><br>"
                   "Экономия ресурсов системы<br>"
                   "<i>• Меньше потребление CPU/GPU</i><br>"
                   "<i>• Пониженная производительность</i>")
        )
        
        grid = QGridLayout()
        grid.addWidget(self.cb_debug, 0, 0)
        grid.addWidget(self.cb_logs, 0, 1)
        grid.addWidget(self.cb_gpu, 1, 0)
        grid.addWidget(self.cb_eco, 1, 1)
        layout.addLayout(grid)
    
    def setup_language_controls(self, layout):
        self.lang = QLabel(self.tr("Language"))
        layout.addWidget(self.lang)

        self.language_group = QButtonGroup(self)
        
        self.rb_ru = QRadioButton("Русский")
        self.rb_en = QRadioButton("English")
        self.rb_zh = QRadioButton("中國人")
        
        self.language_group.addButton(self.rb_ru, 1)  
        self.language_group.addButton(self.rb_en, 2) 
        self.language_group.addButton(self.rb_zh, 3) 
        self.rb_ru.setProperty("code", "ru")
        self.rb_en.setProperty("code", "en")
        self.rb_zh.setProperty("code", "zh")
        
        lang_layout = QHBoxLayout()
        lang_layout.addWidget(self.rb_ru)
        lang_layout.addWidget(self.rb_en)
        lang_layout.addWidget(self.rb_zh)
        layout.addLayout(lang_layout)
    
    def show_advanced_settings(self):
        """Показывает панель расширенных настроек"""
        self.stacked_widget.setCurrentIndex(1)  
        self.back_button.show()
    
    def show_main_settings(self):
        """Возвращается к основной панели настроек"""
        self.stacked_widget.setCurrentIndex(0) 
        self.back_button.hide()
    
    def connect_signals(self):
        # Чекбоксы -> ViewModel
        self.cb_logs.toggled.connect(self.viewmodel.log)
        self.cb_debug.toggled.connect(self.viewmodel.debug)
        self.cb_gpu.toggled.connect(self.viewmodel.gpu)
        self.cb_eco.toggled.connect(self.viewmodel.eco)
        
        # ViewModel -> UI
        self.viewmodel.enable_logging_changed.connect(self.cb_logs.setChecked)
        self.viewmodel.debug_mode_changed.connect(self.cb_debug.setChecked)
        self.viewmodel.use_gpu_changed.connect(self.cb_gpu.setChecked)
        self.viewmodel.use_economy_changed.connect(self.cb_eco.setChecked)
        
        # Язык
        self.rb_ru.toggled.connect(self.on_language_radio_toggled)
        self.rb_en.toggled.connect(self.on_language_radio_toggled)
        self.rb_zh.toggled.connect(self.on_language_radio_toggled)

        self.viewmodel.update_language.connect(self.on_language_changed_from_viewmodel)
        
        
        # Имя пользователя
        self.user.textChanged.connect(self.viewmodel.change_user)
        self.viewmodel.update_user.connect(self.user.setText)
    
    def on_language_radio_toggled(self, checked):
        if not checked: 
            return
        sender = self.sender()
        code = sender.property("code")
        if code:
            self.viewmodel.change_language(code)
    
    def on_language_changed_from_viewmodel(self, code):
        """Обновляет радио-кнопки при изменении языка извне"""
        if code == 'ru':
            self.rb_ru.setChecked(True)
        elif code == 'en':
            self.rb_en.setChecked(True)
        elif code == 'zh':
            self.rb_zh.setChecked(True)

        self.retranslate_ui()
    
    def set_pyaudio(self, pyaudio_instance):
        self.pyaudio = pyaudio_instance
        self.populate_microphones()

    
    def populate_microphones(self):
        if not self.pyaudio:
            return
        
        self.mic_combo.clear()
        for i in range(self.pyaudio.get_device_count()):
            device_info = self.pyaudio.get_device_info_by_index(i)
            if 'microphone' in device_info['name'].lower():
                self.mic_combo.addItem(f'Device {i}: {device_info["name"]}')
    
    def populate_cameras(self):
        self.camera_combo.clear()
        cameras = list_cameras_opencv()
        for cam in cameras:
            self.camera_combo.addItem(f'{self.tr("Camera")} {cam["index"] + 1}', cam)
    
    def sync_from_viewmodel(self):
        self.cb_logs.setChecked(self.viewmodel.get_log())
        self.cb_debug.setChecked(self.viewmodel.get_debug())
        self.cb_gpu.setChecked(self.viewmodel.get_gpu())
        self.cb_eco.setChecked(self.viewmodel.get_eco())
        self.user.setText(self.viewmodel.get_user())
        
        # Синхронизация языка при загрузке
        current_language = self.viewmodel.get_language()
        if current_language == 'ru':
            self.rb_ru.setChecked(True)
        elif current_language == 'zh':
            self.rb_zh.setChecked(True)
        elif current_language == 'en':
            self.rb_en.setChecked(True)

    def retranslate_ui(self):
        self.cb_debug.setText(self.tr("Debug"))
        self.cb_logs.setText(self.tr("Logs"))
        self.cb_gpu.setText(self.tr("GPU"))
        self.cb_eco.setText(self.tr("Economy"))

        self.lang.setText(self.tr("Language"))
        self.user_label.setText(self.tr("Username"))
        self.camera.setText(self.tr("Camera"))
        self.microphone.setText(self.tr("Microphone"))
        
        self.label_lina.setText(self.tr("Lina settings"))
        self.lina_options.setText(self.tr("Launch options"))

        self.back_button.setText(self.tr("<-" + self.tr("Back")))
        self.advanced_settings.setText(self.tr("Advanced settings"))

    def mousePressEvent(self, event):
        ...


    def mouseMoveEvent(self, event):
        ...