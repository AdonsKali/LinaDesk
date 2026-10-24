from PySide6.QtCore import Qt, Signal, QSignalBlocker
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QPushButton,
    QWidget,
)
from .advanced_settings import AdvancedSettingsPanel


class SettingsPanel(QWidget):
    """Панель основных настроек."""

    debug_changed = Signal(bool)
    log_changed = Signal(bool)
    gpu_changed = Signal(bool)
    economy_changed = Signal(bool)
    language_changed = Signal(str)
    username_changed = Signal(str)

    def __init__(self, viewmodel):
        super().__init__()

        self.viewmodel = viewmodel
        self.pyaudio = None

        self._setup_ui()
        self._connect_ui_signals()
        self._connect_viewmodel_signals()
        self._sync_from_viewmodel()


    def _connect_ui_signals(self):
        self.cb_debug.toggled.connect(
            self.debug_changed.emit
        )
        self.cb_logs.toggled.connect(
            self.log_changed.emit
        )
        self.cb_gpu.toggled.connect(
            self.gpu_changed.emit
        )
        self.cb_eco.toggled.connect(
            self.economy_changed.emit
        )

        self.rb_ru.toggled.connect(
            lambda checked: self._on_language_toggled(
                "ru",
                checked,
            )
        )

        self.rb_en.toggled.connect(
            lambda checked: self._on_language_toggled(
                "en",
                checked,
            )
        )

        self.rb_zh.toggled.connect(
            lambda checked: self._on_language_toggled(
                "zh",
                checked,
            )
        )

        self.user_input.editingFinished.connect(
            lambda: self.username_changed.emit(self.user_input.text().strip() or "user"))

    def _connect_viewmodel_signals(self):
        self.viewmodel.settings_updated.connect(self._sync_devices)

        self.viewmodel.debug_changed.connect(
            self._set_debug_from_vm
        )

        self.viewmodel.log_changed.connect(
            self._set_log_from_vm
        )

        self.viewmodel.gpu_changed.connect(
            self._set_gpu_from_vm
        )

        self.viewmodel.economy_changed.connect(
            self._set_economy_from_vm
        )

        self.viewmodel.language_changed.connect(
            self._on_language_changed
        )

        self.viewmodel.username_changed.connect(
            self._set_username_from_vm
        )

    def _on_language_toggled(
        self,
        code: str,
        checked: bool,
    ):

        if not checked:
            return

        self.language_changed.emit(code)

    def _set_debug_from_vm(self, value: bool):
        if self.cb_debug.isChecked() != value:
            with QSignalBlocker(self.cb_debug):
                self.cb_debug.setChecked(value)

    def _set_log_from_vm(self, value: bool):
        if self.cb_logs.isChecked() != value:
            with QSignalBlocker(self.cb_logs):
                self.cb_logs.setChecked(value)

    def _set_gpu_from_vm(self, value: bool):
        if self.cb_gpu.isChecked() != value:
            with QSignalBlocker(self.cb_gpu):
                self.cb_gpu.setChecked(value)

    def _set_economy_from_vm(self, value: bool):
        if self.cb_eco.isChecked() != value:
            with QSignalBlocker(self.cb_eco):
                self.cb_eco.setChecked(value)

    def _set_username_from_vm(self, value: str):
        if self.user_input.text() != value:
            with QSignalBlocker(self.user_input):
                self.user_input.setText(value)

    def _on_language_changed(self, code: str):

        buttons = {
            "ru": self.rb_ru,
            "en": self.rb_en,
            "zh": self.rb_zh,
        }

        button = buttons.get(code)

        if button is None:
            return

        if button.isChecked():
            self.retranslate_ui()
            return

        with QSignalBlocker(self.rb_ru), \
             QSignalBlocker(self.rb_en), \
             QSignalBlocker(self.rb_zh):

            button.setChecked(True)

        self.retranslate_ui()

    def _sync_from_viewmodel(self):

        with QSignalBlocker(self.cb_logs):
            self.cb_logs.setChecked(
                self.viewmodel.get_log()
            )

        with QSignalBlocker(self.cb_debug):
            self.cb_debug.setChecked(
                self.viewmodel.get_debug()
            )

        with QSignalBlocker(self.cb_gpu):
            self.cb_gpu.setChecked(
                self.viewmodel.get_gpu()
            )

        with QSignalBlocker(self.cb_eco):
            self.cb_eco.setChecked(
                self.viewmodel.get_economy()
            )

        with QSignalBlocker(self.user_input):
            self.user_input.setText(
                self.viewmodel.get_username()
            )

        lang = self.viewmodel.get_language()

        buttons = {
            "ru": self.rb_ru,
            "en": self.rb_en,
            "zh": self.rb_zh,
        }

        button = buttons.get(
            lang,
            self.rb_en,
        )

        with QSignalBlocker(self.rb_ru), \
             QSignalBlocker(self.rb_en), \
             QSignalBlocker(self.rb_zh):

            button.setChecked(True)

    # =========================================================
    # UI
    # =========================================================

    def _setup_ui(self):

        main_layout = QVBoxLayout(self)

        self.back_button = QPushButton(
            "<- " + self.tr("Back")
        )
        self.back_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )
        self.back_button.hide()
        self.back_button.clicked.connect(
            self._show_main_settings
        )

        self.stacked_widget = QStackedWidget()

        self.main_panel = QWidget()
        self._setup_main_panel()

        self.advanced_panel = AdvancedSettingsPanel(
            self.viewmodel
        )

        self.stacked_widget.addWidget(
            self.main_panel
        )

        self.stacked_widget.addWidget(
            self.advanced_panel
        )

        main_layout.addWidget(
            self.back_button
        )

        main_layout.addWidget(
            self.stacked_widget
        )

    def _setup_main_panel(self):

        layout = QVBoxLayout(
            self.main_panel
        )

        layout.setSpacing(10)

        self.title_label = QLabel(
            self.tr("Lina settings")
        )

        font = QFont("Arial", 20)
        font.setBold(True)

        self.title_label.setFont(font)
        self.title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            self.title_label
        )

        self.subtitle_label = QLabel(
            self.tr("Launch options")
        )

        layout.addWidget(
            self.subtitle_label
        )

        self._setup_checkboxes(layout)
        self._setup_language_controls(layout)
        self._setup_username_control(layout)
        self._setup_audio_video_controls(layout)

        self.advanced_btn = QPushButton(
            self.tr("Advanced settings")
        )

        self.advanced_btn.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.advanced_btn.clicked.connect(
            self._show_advanced_settings
        )

        layout.addWidget(
            self.advanced_btn
        )

        layout.addStretch()

    def _setup_checkboxes(self, layout):

        self.cb_debug = QCheckBox(
            self.tr("Debug")
        )

        self.cb_debug.setToolTip(
            self.tr("Enable debug mode")
        )

        self.cb_logs = QCheckBox(
            self.tr("Logs")
        )

        self.cb_logs.setToolTip(
            self.tr("Save logs to file")
        )

        self.cb_gpu = QCheckBox(
            self.tr("Видеокарта")
        )

        self.cb_gpu.setToolTip(
            self.tr("Включено: все слои на GPU (-1). Выключено: CPU (0). Применяется при следующем Start.")
        )

        self.cb_eco = QCheckBox(
            self.tr("Economy")
        )

        self.cb_eco.setToolTip(
            self.tr("Economy mode (save resources)")
        )

        grid = QGridLayout()

        grid.addWidget(
            self.cb_debug,
            0,
            0,
        )

        grid.addWidget(
            self.cb_logs,
            0,
            1,
        )

        grid.addWidget(self.cb_gpu, 1, 0)

        self.cb_eco.setParent(self)
        self.cb_eco.hide()

        layout.addLayout(grid)

    def _setup_language_controls(self, layout):

        self.lang_label = QLabel(
            self.tr("Language")
        )

        layout.addWidget(
            self.lang_label
        )

        self.language_group = QButtonGroup(
            self
        )

        self.rb_ru = QRadioButton(
            "Русский"
        )

        self.rb_en = QRadioButton(
            "English"
        )

        self.rb_zh = QRadioButton(
            "中國人"
        )

        self.language_group.addButton(
            self.rb_ru
        )

        self.language_group.addButton(
            self.rb_en
        )

        self.language_group.addButton(
            self.rb_zh
        )

        lang_layout = QHBoxLayout()

        lang_layout.addWidget(
            self.rb_ru
        )

        lang_layout.addWidget(
            self.rb_en
        )

        lang_layout.addWidget(
            self.rb_zh
        )

        layout.addLayout(
            lang_layout
        )

    def _setup_username_control(self, layout):

        self.user_label = QLabel(
            self.tr("Username")
        )

        layout.addWidget(
            self.user_label
        )

        self.user_input = QLineEdit()

        self.user_input.setToolTip(
            self.tr("Enter your name")
        )

        layout.addWidget(
            self.user_input
        )

    def _setup_audio_video_controls(self, layout):

        self.mic_label = QLabel(
            self.tr("Microphone")
        )

        layout.addWidget(
            self.mic_label
        )

        self.mic_combo = QComboBox()
        self.mic_combo.currentIndexChanged.connect(self._select_microphone)

        self.mic_combo.setToolTip(
            self.tr("Select microphone")
        )

        layout.addWidget(
            self.mic_combo
        )

        self.cam_label = QLabel(
            self.tr("Camera")
        )

        layout.addWidget(
            self.cam_label
        )

        self.cam_combo = QComboBox()
        self.cam_combo.currentIndexChanged.connect(self._select_camera)

        self.cam_combo.setToolTip(
            self.tr("Select camera")
        )

        layout.addWidget(
            self.cam_combo
        )

    def _show_advanced_settings(self):
        self.viewmodel.refresh_plugins()
        self.stacked_widget.setCurrentIndex(1)
        self.back_button.show()

    def _show_main_settings(self):
        self.stacked_widget.setCurrentIndex(0)
        self.back_button.hide()
        
    def set_pyaudio(self, pyaudio_instance):
        self.pyaudio = pyaudio_instance
        self._populate_microphones()

    def _populate_microphones(self):
        import sounddevice as sd
        with QSignalBlocker(self.mic_combo):
            self.mic_combo.clear()
            self.mic_combo.addItem("По умолчанию", "default")
            try:
                for index, info in enumerate(sd.query_devices()):
                    if info["max_input_channels"] > 0:
                        self.mic_combo.addItem(f'{index}: {info["name"]}', index)
            except Exception:
                self.mic_combo.setToolTip("Аудиоустройства недоступны; текстовый чат остаётся доступен.")

        self._sync_devices(self.viewmodel._settings)

    def _select_microphone(self, index):
        if index < 0:
            return
        from src.core.application.commands.settings_commands import UpdateSettingsCommand
        self.viewmodel._send_command(UpdateSettingsCommand("microphone", self.mic_combo.itemData(index)))

    def populate_cameras(self):
        with QSignalBlocker(self.cam_combo):
            self.cam_combo.clear()
            self.cam_combo.addItem("По умолчанию", None)
            try:
                from PySide6.QtMultimedia import QMediaDevices
                if not hasattr(self, "_media_devices"):
                    self._media_devices = QMediaDevices(self)
                    self._media_devices.videoInputsChanged.connect(self.populate_cameras)
                for device in QMediaDevices.videoInputs():
                    self.cam_combo.addItem(device.description(), bytes(device.id()).hex())
                self.cam_combo.setEnabled(True)
            except ImportError:
                self.cam_combo.setEnabled(False)
                self.cam_combo.setToolTip("Для выбора камеры требуется PySide6 QtMultimedia.")
            self._sync_devices(self.viewmodel._settings)

    def _select_camera(self, index):
        if index < 0:
            return
        from src.core.application.commands.settings_commands import UpdateSettingsCommand
        self.viewmodel._send_command(UpdateSettingsCommand("camera", self.cam_combo.itemData(index)))

    def _sync_devices(self, settings):
        for combo, field, default in ((self.mic_combo, "microphone", "default"),
                                      (self.cam_combo, "camera", None)):
            with QSignalBlocker(combo):
                value = settings.get(field, default)
                index = combo.findData(value)
                if index < 0 and value not in (None, "default", ""):
                    combo.addItem(f"Недоступно: {value}", value)
                    index = combo.count() - 1
                combo.setCurrentIndex(max(0, index))

    def update_plugins(self, plugins: list):
        self.advanced_panel.update_plugins(
            plugins
        )


    def retranslate_ui(self):

        self.title_label.setText(
            self.tr("Lina settings")
        )

        self.subtitle_label.setText(
            self.tr("Launch options")
        )

        self.cb_debug.setText(
            self.tr("Debug")
        )

        self.cb_logs.setText(
            self.tr("Logs")
        )

        self.cb_gpu.setText(
            self.tr("Видеокарта")
        )

        self.cb_eco.setText(
            self.tr("Economy")
        )

        self.lang_label.setText(
            self.tr("Language")
        )

        self.user_label.setText(
            self.tr("Username")
        )

        self.mic_label.setText(
            self.tr("Microphone")
        )

        self.cam_label.setText(
            self.tr("Camera")
        )

        self.back_button.setText(
            "<- " + self.tr("Back")
        )

        self.advanced_btn.setText(
            self.tr("Advanced settings")
        )

        self.advanced_panel.retranslate_ui()
