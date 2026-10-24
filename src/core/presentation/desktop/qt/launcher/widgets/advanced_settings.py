from PySide6.QtCore import Qt, Signal, QSignalBlocker
from PySide6.QtWidgets import (
    QWidget, QComboBox, QLabel, QVBoxLayout, QHBoxLayout,
    QGridLayout, QCheckBox, QPushButton, QListWidget, QListWidgetItem,
)

from src.core.presentation.desktop.qt.launcher.viewmodel import LauncherViewModel
from .tool_permission_dialog import PERMISSION_LABELS


class AdvancedSettingsPanel(QWidget):
    """Панель расширенных настроек"""
    
    # Сигналы для ViewModel
    sandbox_changed = Signal(bool)
    server_mode_changed = Signal(bool)
    autonomy_mode_changed = Signal(str)
    plugins_enabled_changed = Signal(bool)
    plugins_refresh_requested = Signal()
    plugin_toggled = Signal(str, bool)
    tool_permissions_changed = Signal(str, list)
    
    def __init__(self, viewmodel: LauncherViewModel):
        super().__init__()
        self.viewmodel = viewmodel
        self._plugins = []
        
        # Настраиваем UI
        self._setup_ui()
        
        # Подключаем сигналы от UI к ViewModel
        self._connect_ui_signals()
        
        # Подключаем сигналы от ViewModel для обновления UI
        self._connect_viewmodel_signals()
        
        # Синхронизируем с ViewModel
        self._sync_from_viewmodel()
        
    def _connect_ui_signals(self):
        """Подключение сигналов от UI к ViewModel (действия пользователя)"""
        # Чекбоксы -> ViewModel
        self.sandbox_check.toggled.connect(self.sandbox_changed.emit)
        self.server_check.toggled.connect(self.server_mode_changed.emit)
        self.plugins_enabled_check.toggled.connect(self.plugins_enabled_changed.emit)
        
        # Автономный режим -> ViewModel
        self.autonomy_combo.currentTextChanged.connect(self._on_autonomy_selected)
        
        # Плагины -> ViewModel
        self.refresh_btn.clicked.connect(self.plugins_refresh_requested.emit)
    
    def _connect_viewmodel_signals(self):
        """Подключение сигналов от ViewModel для обновления UI"""
        # ViewModel -> UI (обновление состояния)
        self.viewmodel.sandbox_changed.connect(self.sandbox_check.setChecked)
        self.viewmodel.server_mode_changed.connect(self.server_check.setChecked)
        self.viewmodel.autonomy_mode_changed.connect(self._on_autonomy_changed)
        self.viewmodel.plugins_enabled_changed.connect(self._on_plugins_enabled_changed)
        self.viewmodel.plugin_list_updated.connect(self.update_plugins)
    
    def _setup_ui(self):
        """Настройка UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Заголовок
        self.title_label = QLabel(self.tr("Advanced Settings"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.title_label.font()
        font.setBold(True)
        font.setPointSize(14)
        self.title_label.setFont(font)
        layout.addWidget(self.title_label)
        
        
        # Чекбоксы
        self._setup_checkboxes(layout)
        
        # Автономный режим
        self._setup_autonomy_mode(layout)
        
        # Плагины
        self._setup_plugins_section(layout)
        
        layout.addStretch()

    def _setup_checkboxes(self, layout):
        """Настройка чекбоксов"""
        grid = QGridLayout()
        
        self.sandbox_check = QCheckBox(self.tr("Sandbox"))
        self.sandbox_check.setToolTip(self.tr("Run in sandbox mode"))
        self.sandbox_check.toggled.connect(self.sandbox_changed.emit)
        grid.addWidget(self.sandbox_check, 0, 0)
        
        self.server_check = QCheckBox(self.tr("Server"))
        self.server_check.setEnabled(False)
        self.server_check.setToolTip("HTTP/Android — следующий этап, в desktop-прототипе не реализовано.")
        self.server_check.setToolTip(self.tr("Enable server mode"))
        self.server_check.toggled.connect(self.server_mode_changed.emit)
        grid.addWidget(self.server_check, 0, 1)
        
        layout.addLayout(grid)
    
    def _setup_autonomy_mode(self, layout):
        """Настройка автономного режима"""
        autonomy_layout = QHBoxLayout()
        
        self.autonomy_label = QLabel(self.tr("Autonomy Mode"))
        self.autonomy_combo = QComboBox()
        self.autonomy_combo.addItem(self.tr("Semi-autonomous"))
        self.autonomy_combo.addItem(self.tr("Autonomous"))
        self.autonomy_combo.setToolTip(self.tr("Select autonomy mode"))
        self.autonomy_combo.currentTextChanged.connect(self._on_autonomy_selected)
        
        autonomy_layout.addWidget(self.autonomy_label)
        autonomy_layout.addWidget(self.autonomy_combo)
        layout.addLayout(autonomy_layout)
    
    def _setup_plugins_section(self, layout):
        """Настройка секции плагинов"""
        # Заголовок
        self.plugins_label = QLabel(self.tr("Plugins"))
        layout.addWidget(self.plugins_label)
        
        # Список плагинов
        self.plugins_list = QListWidget()
        self.plugins_list.setToolTip(self.tr("Available plugins"))
        self.plugins_list.itemChanged.connect(self._on_plugin_toggled)
        self.plugins_list.currentItemChanged.connect(self._on_plugin_selected)
        layout.addWidget(self.plugins_list)

        layout.addWidget(QLabel("Права выбранного инструмента (применяются сразу)"))
        self.permission_tool_combo = QComboBox()
        self.permission_tool_combo.currentIndexChanged.connect(self._sync_permissions)
        layout.addWidget(self.permission_tool_combo)
        permission_grid = QGridLayout()
        self.permission_checks = {}
        for index, (permission, label) in enumerate(PERMISSION_LABELS.items()):
            check = QCheckBox(label)
            check.setToolTip("Отзыв блокирует новые вызовы. Уже запущенное фоновое задание можно отменить отдельно.")
            check.setEnabled(False)
            check.toggled.connect(self._on_permission_toggled)
            self.permission_checks[permission] = check
            permission_grid.addWidget(check, index // 2, index % 2)
        layout.addLayout(permission_grid)
        
        # Кнопки управления плагинами
        plugins_controls = QHBoxLayout()
        
        self.refresh_btn = QPushButton(self.tr("Refresh Plugins"))
        plugins_controls.addWidget(self.refresh_btn)
        
        self.plugins_enabled_check = QCheckBox(self.tr("Enable Plugins"))
        self.plugins_enabled_check.setEnabled(True)
        self.plugins_enabled_check.setToolTip("Включает внешние инструменты. Изменения применяются при следующем Start.")
        plugins_controls.addWidget(self.plugins_enabled_check)
        
        layout.addLayout(plugins_controls)
    
    def _on_plugin_selected(self, current, previous=None):
        previous_tool = self.permission_tool_combo.currentData()
        previous_name = previous_tool.get("name") if previous_tool else None
        plugin = current.data(Qt.ItemDataRole.UserRole) if current else {}
        with QSignalBlocker(self.permission_tool_combo):
            self.permission_tool_combo.clear()
            for spec in (plugin or {}).get("tool_specs", []):
                self.permission_tool_combo.addItem(spec["name"], spec)
                self.permission_tool_combo.setItemData(self.permission_tool_combo.count() - 1,
                                                       spec.get("description", ""), Qt.ItemDataRole.ToolTipRole)
            for index in range(self.permission_tool_combo.count()):
                if self.permission_tool_combo.itemData(index)["name"] == previous_name:
                    self.permission_tool_combo.setCurrentIndex(index)
        self._sync_permissions()

    def _sync_permissions(self, *args):
        spec = self.permission_tool_combo.currentData() or {}
        for name, check in self.permission_checks.items():
            with QSignalBlocker(check):
                check.setEnabled(name in spec.get("permissions", []))
                check.setChecked(name in spec.get("granted_permissions", []))

    def _on_permission_toggled(self, *args):
        spec = self.permission_tool_combo.currentData()
        if spec:
            granted = [name for name, check in self.permission_checks.items() if check.isEnabled() and check.isChecked()]
            self.tool_permissions_changed.emit(spec["name"], granted)

    def _on_autonomy_selected(self, text: str):
        """Выбран режим автономности - отправляем в ViewModel"""
        mode_map = {
            self.tr("Semi-autonomous"): "semi-autonomous",
            self.tr("Autonomous"): "autonomous"
        }
        mode = mode_map.get(text, "semi-autonomous")
        self.autonomy_mode_changed.emit(mode)
    
    def _on_plugin_toggled(self, item: QListWidgetItem):
        """Переключение плагина - отправляем в ViewModel"""
        if not item:
            return
        
        plugin = item.data(Qt.ItemDataRole.UserRole)
        if not plugin:
            return
        
        enabled = item.checkState() == Qt.CheckState.Checked
        plugin_name = plugin.get("name", "")
        
        if plugin_name:
            self.plugin_toggled.emit(plugin_name, enabled)
    
    def _sync_from_viewmodel(self):
        """Синхронизация UI с ViewModel"""
        self.sandbox_check.setChecked(self.viewmodel.get_sandbox())
        self.server_check.setChecked(self.viewmodel.get_server_mode())
        self.plugins_enabled_check.setChecked(self.viewmodel.get_plugins_enabled())
        
        # Автономный режим
        autonomy = self.viewmodel.get_autonomy_mode()
        autonomy_map = {
            "semi-autonomous": 0,
            "autonomous": 1
        }
        index = autonomy_map.get(autonomy, 0)
        self.autonomy_combo.setCurrentIndex(index)
    
    def _on_sandbox_changed(self, enabled: bool):
        self.sandbox_check.setChecked(enabled)
    
    def _on_server_mode_changed(self, enabled: bool):
        self.server_check.setChecked(enabled)
    
    def _on_autonomy_changed(self, mode: str):
        """Обновление UI при смене автономного режима"""
        autonomy_map = {
            "semi-autonomous": 0,
            "autonomous": 1
        }
        index = autonomy_map.get(mode, 0)
        self.autonomy_combo.setCurrentIndex(index)
    
    def _on_plugins_enabled_changed(self, enabled: bool):
        with QSignalBlocker(self.plugins_enabled_check):
            self.plugins_enabled_check.setChecked(enabled)
    
    def update_plugins(self, plugins: list):
        """Обновление списка плагинов"""
        statuses = {"ready": "готов", "disabled": "отключён", "unavailable": "недоступен", "invalid": "ошибка манифеста"}
        selected = self.plugins_list.currentItem()
        selected_name = selected.data(Qt.ItemDataRole.UserRole).get("name") if selected else None
        selected_row = 0
        with QSignalBlocker(self.plugins_list):
            self.plugins_list.clear()
            self._plugins = plugins
            for plugin in plugins:
                status = statuses.get(plugin.get("status"), "неизвестно")
                item = QListWidgetItem(f"{plugin['name']} — {status}")
                item.setData(Qt.ItemDataRole.UserRole, plugin)
                if plugin.get("editable", True):
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                    item.setCheckState(Qt.CheckState.Checked if plugin.get("enabled") else Qt.CheckState.Unchecked)
                else:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                details = [plugin.get("description", ""), "Изменения применяются при следующем Start."]
                if plugin.get("tools"):
                    details.append("Инструменты: " + ", ".join(plugin["tools"]))
                if plugin.get("requirements"):
                    details.append("Зависимости: " + str(plugin["requirements"]))
                    details.append(plugin.get("install_command", ""))
                item.setToolTip("\n".join(details))
                self.plugins_list.addItem(item)
                if plugin['name'] == selected_name:
                    selected_row = self.plugins_list.count() - 1
            self.plugins_list.setCurrentRow(selected_row)
        self._on_plugin_selected(self.plugins_list.currentItem())

    def retranslate_ui(self):
        """Обновление перевода"""
        self.title_label.setText(self.tr("Advanced Settings"))
        self.sandbox_check.setText(self.tr("Sandbox"))
        self.server_check.setText(self.tr("Server"))
        self.autonomy_label.setText(self.tr("Autonomy Mode"))
        self.autonomy_combo.setItemText(0, self.tr("Semi-autonomous"))
        self.autonomy_combo.setItemText(1, self.tr("Autonomous"))
        self.plugins_label.setText(self.tr("Plugins"))
        self.refresh_btn.setText(self.tr("Refresh Plugins"))
        self.plugins_enabled_check.setText(self.tr("Enable Plugins"))
