import asyncio
from PySide6.QtCore import QObject, QTranslator, Signal, Slot, QCoreApplication
from typing import Dict, Any, List
from src.core.application.ports.event_port import EventBusPort
from src.core.application.ports.command_bus import CommandBusPort
from src.core.application.commands.settings_commands import *
from src.core.application.commands.system_commands import *
from src.core.domain.events.settings_events import SettingsLoaded, SettingsChanged 
from src.core.domain.events.system_events import SystemStarted, SystemStopped, SystemError
from src.core.domain.events.plugin_events import PluginListReceived
from src.core.domain.events.tool_events import BackgroundJobFinished, ToolPermissionRequested, ToolPermissionRequestClosed
from src.core.utils.logger import logger


class LauncherViewModel(QObject):
    """
    ViewModel для лаунчера.
    Содержит ВСЮ логику взаимодействия с системой.
    НЕ ЗНАЕТ о Application!
    """
    
    # Сигналы для UI
    settings_updated = Signal(dict)
    debug_changed = Signal(bool)
    log_changed = Signal(bool)
    gpu_changed = Signal(bool)
    economy_changed = Signal(bool)
    language_changed = Signal(str)
    username_changed = Signal(str)
    sandbox_changed = Signal(bool)
    server_mode_changed = Signal(bool)
    autonomy_mode_changed = Signal(str)
    plugins_enabled_changed = Signal(bool)
    
    system_start_requested = Signal()
    system_started = Signal()
    system_stopped = Signal()
    application_exit_requested = Signal()  
    system_error = Signal(str)
    busy_changed = Signal(bool)
    plugin_list_updated = Signal(list)
    background_job_finished = Signal(dict)
    tool_permission_requested = Signal(dict)
    tool_permission_closed = Signal(str)
    
    def __init__(
        self,
        command_bus: CommandBusPort,
        event_bus: EventBusPort,
    ):
        super().__init__()

        self._command_bus = command_bus
        self._event_bus = event_bus

        self._settings: Dict[str, Any] = {}
        self._plugins: List[Dict[str, Any]] = []

        self._is_system_running = False
        self._is_closing = False
        self._busy = False
        self._tasks = set()

        self._translator = QTranslator()

        self._subscribe_to_events()
    
    def _subscribe_to_events(self):
        """Подписка на события для обновления UI"""
        self._event_bus.subscribe(SettingsLoaded, self._on_settings_loaded)
        self._event_bus.subscribe(SettingsChanged, self._on_settings_changed)
        self._event_bus.subscribe(SystemStarted, self._on_system_started)
        self._event_bus.subscribe(SystemStopped, self._on_system_stopped)
        self._event_bus.subscribe(SystemError, self._on_system_error)
        self._event_bus.subscribe(PluginListReceived, self._on_plugin_list_received)
        self._event_bus.subscribe(BackgroundJobFinished, self._on_background_job_finished)
        self._event_bus.subscribe(ToolPermissionRequested, self._on_tool_permission_requested)
        self._event_bus.subscribe(ToolPermissionRequestClosed, self._on_tool_permission_closed)

    async def _on_tool_permission_requested(self, event):
        if not self._is_closing:
            self.tool_permission_requested.emit(dict(request_id=event.request_id, tool_name=event.tool_name,
                                                     plugin_name=event.plugin_name, permissions=event.permissions))

    async def _on_tool_permission_closed(self, event):
        if not self._is_closing:
            self.tool_permission_closed.emit(event.request_id)

    async def _on_background_job_finished(self, event):
        if not self._is_closing and event.status != "cancelled":
            self.background_job_finished.emit(dict(tool_name=event.tool_name, status=event.status,
                                                   job_id=event.job_id, error=event.error))
    
        # ==================== Обработчики событий ====================
        
    async def _on_settings_loaded(
        self,
        event: SettingsLoaded,
    ):
        if self._is_closing:
            return

        settings = event.settings

        self._settings = dict(settings)

        self._apply_language(
            settings.get("language", "en")
        )

        self._emit_all_settings_signals()

        self.settings_updated.emit(
            dict(self._settings)
        )
        
    def _apply_language(self, language: str):

        app = QCoreApplication.instance()

        if app is None:
            return

        app.removeTranslator(
            self._translator
        )

        self._translator = QTranslator()

        path = (
            f"src/resources/languages/"
            f"{language}/launcher.qm"
        )

        if not self._translator.load(path):

            logger.warning(
                "Failed to load translation: %s",
                path,
            )

            return

        app.installTranslator(
            self._translator
        )
    
    async def _on_settings_changed(
        self,
        event: SettingsChanged,
    ):
        if self._is_closing:
            return

        for field, value in event.new_settings.items():

            old_value = self._settings.get(field)

            if old_value == value:
                continue

            self._settings[field] = value

            if field == "language":
                self._apply_language(value)

        self._emit_all_settings_signals()

        self.settings_updated.emit(
            dict(self._settings)
        )
    
    async def _on_system_started(self, event: SystemStarted):
        if self._is_closing:
            return
        self._is_system_running = True
        self._set_busy(False)
        self.system_started.emit()
        logger.info("✅ System started (UI updated)")
    
    async def _on_system_stopped(self, event: SystemStopped):
        """
        Система остановлена - обновляем UI.
        Если мы в процессе выхода - завершаем его.
        """
        if self._is_closing:
            return
        
        self._is_system_running = False
        self._set_busy(False)
        if event.reason == "exit":
            logger.info("✅ System stopped due to application exit")
            self._complete_exit()
        else:
            self.system_stopped.emit()
            logger.info("✅ System stopped (UI updated)")
        
    
    async def _on_system_error(self, event: SystemError):
        if self._is_closing:
            return
        self._set_busy(False)
        self.system_error.emit(event.error)
        logger.error(f"System error: {event.error}")
    
    async def _on_plugin_list_received(self, event: PluginListReceived):
        if self._is_closing:
            return
        self._plugins = event.plugins
        self.plugin_list_updated.emit(self._plugins)
    
    # ==================== Действия от UI ====================
    
    @Slot(bool)
    def set_debug(self, enabled: bool):
        self._send_command(UpdateSettingsCommand("on_debug", enabled))
    
    @Slot(bool)
    def set_log(self, enabled: bool):
        self._send_command(UpdateSettingsCommand("on_log", enabled))
    
    @Slot(bool)
    def set_gpu(self, enabled: bool):
        self._send_command(UpdateSettingsCommand("on_gpu", enabled))
    
    @Slot(bool)
    def set_economy(self, enabled: bool):
        self._send_command(UpdateSettingsCommand("on_economy", enabled))
    
    @Slot(str)
    def set_language(self, language: str):
        self._send_command(UpdateSettingsCommand("language", language))
    
    @Slot(str)
    def set_username(self, username: str):
        self._send_command(UpdateSettingsCommand("username", username))
    
    @Slot(bool)
    def set_sandbox(self, enabled: bool):
        self._send_command(UpdateSettingsCommand("on_sandbox", enabled))
    
    @Slot(bool)
    def set_server_mode(self, enabled: bool):
        self._send_command(UpdateSettingsCommand("on_server", enabled))
    
    @Slot(str)
    def set_autonomy_mode(self, mode: str):
        self._send_command(UpdateSettingsCommand("autonomy", mode))
    
    @Slot(bool)
    def set_plugins_enabled(self, enabled: bool):
        self._send_command(UpdateSettingsCommand("on_plugins", enabled))
    
    @Slot(str, bool)
    def toggle_plugin(self, plugin_name: str, enabled: bool):
        self._send_command(TogglePluginCommand(plugin_name, enabled))
    
    @Slot()
    def refresh_plugins(self):
        self._send_command(GetPluginListCommand())

    @Slot(str, list)
    def set_tool_permissions(self, tool_name, permissions):
        self._send_command(SetToolPermissionsCommand(tool_name, permissions))

    def resolve_tool_permission(self, request_id, allowed, remember=False):
        self._send_command(ResolveToolPermissionCommand(request_id, allowed, remember))
    
    @Slot()
    def toggle_system(self):
        """Пользователь нажал Start/Stop"""
        if self._busy:
            return
        self._set_busy(True)
        if self._is_system_running:
            logger.info("🔄 User requested system stop")
            self._send_command(StopSystemCommand(reason="stop"))
        else:
            logger.info("🔄 User requested system start")
            self.system_start_requested.emit()
            self._send_command(StartSystemCommand())
    
    @Slot()
    def exit_application(self):
        """
        Выход из приложения.
        Отправляет команду остановки системы и ждет события SystemStopped.
        """
        logger.info("🛑 User requested exit")
        self._send_command(StopSystemCommand(reason="exit"))
        
    
    def _complete_exit(self):
        """Завершение выхода"""
        if self._is_closing:
            return
        
        logger.info("✅ System stopped, exiting application...")
        self.application_exit_requested.emit()
    
    # ==================== Вспомогательные методы ====================
    
    def _send_command(self, command):

        if self._is_closing:
            logger.warning(
                "ViewModel is closing, command not sent"
            )
            return

        task = asyncio.create_task(
            self._send_command_async(command)
        )
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        
    async def _send_command_async(self, command):

        try:

            await self._command_bus.send(command)

        except Exception as exc:
            self._set_busy(False)
            logger.error(
                "Failed to execute command %s",
                type(command).__name__,
            )
            self.system_error.emit(str(exc))
    
    def _emit_all_settings_signals(self):
        """Эмит всех сигналов настроек"""
        signal_map = {
            "on_debug": self.debug_changed,
            "on_log": self.log_changed,
            "on_gpu": self.gpu_changed,
            "on_economy": self.economy_changed,
            "language": self.language_changed,
            "username": self.username_changed,
            "on_sandbox": self.sandbox_changed,
            "on_server": self.server_mode_changed,
            "autonomy": self.autonomy_mode_changed,
            "on_plugins": self.plugins_enabled_changed
        }
        
        for field, signal in signal_map.items():
            if field in self._settings:
                try:
                    signal.emit(self._settings[field])
                except Exception as e:
                    logger.warning(f"Error emitting signal for {field}: {e}")
    
    def close(self):
        """Закрытие ViewModel"""
        self._is_closing = True
        for event_type, handler in (
            (SettingsLoaded, self._on_settings_loaded),
            (SettingsChanged, self._on_settings_changed),
            (SystemStarted, self._on_system_started),
            (SystemStopped, self._on_system_stopped),
            (SystemError, self._on_system_error),
            (PluginListReceived, self._on_plugin_list_received),
            (BackgroundJobFinished, self._on_background_job_finished),
            (ToolPermissionRequested, self._on_tool_permission_requested),
            (ToolPermissionRequestClosed, self._on_tool_permission_closed),
        ):
            self._event_bus.unsubscribe(event_type, handler)
        for task in self._tasks:
            task.cancel()
        self._settings.clear()
        self._plugins.clear()
        logger.info("  ✅ ViewModel closed")
    
    # ==================== Геттеры ====================
    
    def _set_busy(self, busy):
        self._busy = busy
        self.busy_changed.emit(busy)

    def get_debug(self) -> bool:
        return self._settings.get("on_debug", False)
    
    def get_log(self) -> bool:
        return self._settings.get("on_log", False)
    
    def get_gpu(self) -> bool:
        return self._settings.get("on_gpu", False)
    
    def get_economy(self) -> bool:
        return self._settings.get("on_economy", False)
    
    def get_language(self) -> str:
        return self._settings.get("language", "en")
    
    def get_username(self) -> str:
        return self._settings.get("username", "User")
    
    def get_sandbox(self) -> bool:
        return self._settings.get("on_sandbox", False)
    
    def get_server_mode(self) -> bool:
        return self._settings.get("on_server", False)
    
    def get_autonomy_mode(self) -> str:
        return self._settings.get("autonomy", "semi-autonomous")
    
    def get_plugins_enabled(self) -> bool:
        return self._settings.get("on_plugins", False)
    
    def get_plugins(self) -> List[Dict[str, Any]]:
        return self._plugins
    
    def is_system_running(self) -> bool:
        return self._is_system_running
