from src.core.utils.logger import logger
logger.setup(
    app_name="LinaAI",
    log_to_file=False,
    clear_on_start=True,
    debug=False
)
import asyncio
from typing import Optional
from PySide6.QtCore import QCoreApplication
from src.bootstrap.di import ApplicationContainer
from src.core.application.ports.event_port import EventBusPort
from src.core.domain.events.system_events import (
    SystemStartRequested,
    SystemStopRequested,
    SystemStarted,
    SystemStopped,
    SystemError,
)
from src.core.domain.events.settings_events import (
    SettingsChanged,
    SettingsLoaded,
)
from src.core.domain.value_objects.settings import Settings
from src.core.presentation.desktop.qt.launcher.launcher import Launcher
from src.core.presentation.desktop.qt.chibi.chibi import ChibiApp
from src.core.presentation.desktop.qt.splash import SplashScreen
from local_paths import IMAGES


class Application:
    """
    Главный runtime приложения.
    """

    def __init__(
        self,
        ui_type: str = "qt",
        qt_app: Optional[QCoreApplication] = None,
    ):
        self._ui_type = ui_type
        self._container = ApplicationContainer()
        self._event_bus: Optional[EventBusPort] = None
        self._qt_app = qt_app
        self._launcher: Optional[Launcher] = None
        self._chibi_app: Optional[ChibiApp] = None
        self._splash: Optional[SplashScreen] = None
        self._is_system_ready = False
        self._is_running = False
        self._system_handlers_registered = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._shutdown_future: Optional[asyncio.Future] = None
        self._is_starting = False
        self._start_task = None
        self._stop_task = None
        self._exit_requested = False
        self._shutdown_complete = False

    # =========================================================
    # APPLICATION START
    # =========================================================

    async def run(self) -> None:
        try:
            self._event_bus = self._container.get_event_bus()
            await self._event_bus.start()
            self._subscribe_to_system_events()

            settings_repo = self._container.get_settings_repo()
            settings = await settings_repo.get()
            if settings is None:
                settings = Settings.default()
                await settings_repo.save(settings)

            self._container.set_settings(settings)
            logger.info("Settings loaded")

            # ← Публикуем SettingsLoaded для UI
            await self._event_bus.publish(SettingsLoaded(
                settings=settings.to_dict(),
                source="file",
            ))
            
            logger.setup(
                app_name="LinaAI",
                log_to_file=False,
                clear_on_start=True,
                debug=self._container.get_settings().on_debug
            )
            
            self._start_ui()

            # 4. Heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat())

            loop = asyncio.get_running_loop()
            self._shutdown_future = loop.create_future()
            self._is_running = True
            await self._shutdown_future

        except asyncio.CancelledError:
            logger.info("Application run cancelled")
            raise
        except Exception:
            logger.error("Application error")
            raise

    # =========================================================
    # HEARTBEAT
    # =========================================================

    async def _heartbeat(self) -> None:
        while self._is_running:
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.error("Heartbeat error")

    # =========================================================
    # EVENTS
    # =========================================================

    def _subscribe_to_system_events(self) -> None:
        if self._system_handlers_registered:
            return
        if self._event_bus is None:
            raise RuntimeError("EventBus is not initialized")

        self._event_bus.subscribe(
            SystemStartRequested, self._on_system_start_requested
        )
        self._event_bus.subscribe(
            SystemStopRequested, self._on_system_stop_requested
        )

        # Изменение настроек
        self._event_bus.subscribe(SettingsChanged, self._on_settings_changed)

        self._system_handlers_registered = True

    async def _on_settings_changed(self, event: SettingsChanged) -> None:
        if self._is_system_ready or self._is_starting or (self._stop_task and not self._stop_task.done()):
            # Persisted settings are picked up at the next Start.
            return
        new_settings = Settings.from_dict(event.new_settings)   # новый объект
        self._container.set_settings(new_settings)

    # =========================================================
    # SYSTEM START
    # =========================================================

    async def _start_splash(self) -> None:
        self._splash = SplashScreen(background_image=f"{IMAGES}/splash.png")
        self._splash.set_version(self._container.get_settings().version)
        self._splash.set_progress(0)
        self._splash.set_status("Initializing...")
        self._splash.show()
        await asyncio.sleep(0)

    async def _on_system_start_requested(
        self,
        event: SystemStartRequested,
    ) -> None:
        if self._exit_requested or self._is_system_ready or self._is_starting or (self._stop_task and not self._stop_task.done()):
            logger.warning("System is already running")
            return
        self._is_starting = True
        self._stop_task = None
        self._start_task = asyncio.create_task(self._start_system(event))

    async def _start_system(self, event):
        try:
            await self._start_splash()

            settings_repo = self._container.get_settings_repo()
            settings = await settings_repo.get() or Settings.default()
            self._container.set_settings(settings)
            self._container.container.gate().stopping = False
            self._container.container.gate().touch()
            # Bind lazy chat dependencies only after settings are finalized.
            self._container.container.tool_registry.reset()
            self._container.container.tool_engine.reset()
            self._container.container.pipeline.reset()
            self._container.container.chat_orchestration.reset()
            self._container.container.autonomy_orchestration.reset()
            self._container._handlers_registered = False
            self._container.get_command_bus()
                
            llm = self._container.get_llm_client()
            await llm.initialize()
            
            logger.info("   LLM initialized")

            # Engines / репозитории
            self._splash.set_progress_and_status(40, "Initializing engines")
            await asyncio.sleep(0)

            # Прогреваем синглтоны, чтобы они собрались
            self._splash.set_progress_and_status(45, "Initializing vector memory")
            await self._container.get_memory_repo().initialize_index()
            # в _on_system_start_requested после ensure_lina / ensure_user / ensure_session
            if settings.autonomy == "autonomous":
                logger.info("  🤖 Starting autonomy mode...")
                user = await self._container.ensure_user()
                autonomy = self._container.container.autonomy_orchestration()
                await autonomy.start(
                    lina= await self._container.ensure_lina(),
                    user= user,
                    session= await self._container.ensure_session(user.id),
                    reason="system_start",
                )

            # Гарантируем пользователя, Лину, сессию
            user = await self._container.ensure_user()
            lina = await self._container.ensure_lina()
            await self._container.ensure_session(user.id)

            logger.info("   Engines initialized")

            # Pipeline / orchestration собираются лениво через провайдеры,
            # но прогреем их, чтобы ошибки вылезли сейчас, а не в чате
            self._splash.set_progress_and_status(60, "Initializing orchestrators")
            await asyncio.sleep(0)
            self._container.container.chat_orchestration()

            logger.info("   Orchestrators initialized")

            # Chibi
            self._splash.set_progress_and_status(86, "Showing chibi!")
            self._start_chibi()
            await asyncio.sleep(0)

            self._splash.set_progress_and_status(100, "Done!")
            self._splash.close_splash()

            self._is_system_ready = True

            if self._event_bus:
                await self._event_bus.publish(SystemStarted(
                    boot_time_ms=0,
                    components=self._get_components(),
                    settings=event.settings,
                ))

            logger.info(" System fully initialized and ready!")

        except Exception as e:
            logger.exception("Failed to initialize system")
            await self._cleanup_runtime()
            if self._splash:
                self._splash.close_splash()
            if self._launcher:
                self._launcher.show()
            if self._event_bus:
                await self._event_bus.publish(SystemError(
                    error=str(e),
                    component="bootstrap",
                ))
        finally:
            self._is_starting = False

    # =========================================================
    # SYSTEM STOP
    # =========================================================

    async def _on_system_stop_requested(
        self,
        event: SystemStopRequested,
    ) -> None:
        self._exit_requested |= event.reason == "exit"
        if self._stop_task and not self._stop_task.done():
            return
        self._stop_task = asyncio.create_task(self._stop_system(event.reason))

    async def _cleanup_runtime(self):
        gate = self._container.container.gate()
        gate.stopping = True
        # Drain producers before closing native resources or deleting Qt objects.
        for cleanup in (self._stop_chibi_async,
                        self._container.container.autonomy_orchestration().stop):
            try:
                await cleanup()
            except Exception:
                logger.exception("Runtime cleanup failed")
        try:
            async with gate.lock:
                await self._container.reset()
        finally:
            self._is_system_ready = False
            if self._splash:
                self._splash.close_splash()
                self._splash = None

    async def _stop_system(self, reason):
        try:
            if self._start_task and not self._start_task.done():
                self._start_task.cancel()
                await asyncio.gather(self._start_task, return_exceptions=True)
            await self._cleanup_runtime()
        except Exception:
            logger.exception("Failed to stop system")
        finally:
            self._is_system_ready = False
            if self._event_bus:
                await self._event_bus.publish(SystemStopped(
                    uptime_seconds=0,
                    reason="exit" if self._exit_requested else reason,
                ))
                # This task is outside the event worker, so join cannot deadlock it.
                await self._event_bus.drain()
            if self._exit_requested:
                self._is_running = False
                if self._shutdown_future and not self._shutdown_future.done():
                    self._shutdown_future.set_result(None)

    # =========================================================
    # UI
    # =========================================================

    def _start_ui(self) -> None:
        if self._ui_type == "qt":
            self._start_qt_launcher()
        elif self._ui_type == "cli":
            raise NotImplementedError("CLI mode is not implemented with qasync yet")
        else:
            raise ValueError(f"Unknown UI type: {self._ui_type}")

    def _start_qt_launcher(self) -> None:
        if self._event_bus is None:
            raise RuntimeError("EventBus is not initialized")
        if self._launcher is not None:
            return

        self._launcher = Launcher(
            command_bus=self._container.get_command_bus(),
            event_bus=self._event_bus,
        )
        self._launcher.show()
        self._launcher._window.restart_requested.connect(self._request_restart)
        logger.info("   Qt Launcher started")

    def _request_restart(self):
        if getattr(self, "restart_requested", False):
            return
        self.restart_requested = True
        self._launcher._window.restart_button.setEnabled(False)
        self._launcher._viewmodel.exit_application()

    # =========================================================
    # CHIBI
    # =========================================================

    def _start_chibi(self) -> None:
        if self._chibi_app is not None:
            logger.warning("Chibi is already running, recreating...")
            old = self._chibi_app
            self._chibi_app = None
            old.shutdown()

        try:
            self._chibi_app = ChibiApp(
                self._container.get_command_bus(),
                self._container.get_event_bus(),
            )
            settings = self._container.get_settings()
            microphone = settings.microphone
            self._chibi_app.coordinator.api_service.activity_callback = self._container.container.gate().touch
            self._chibi_app.coordinator.api_service.microphone = (
                None if microphone in (None, "", "default") else microphone)
            logger.info(" Chibi started")
        except Exception as e:
            logger.error(f"Failed to start Qt Chibi: {e}")
            self._chibi_app = None
            raise

    # =========================================================
    # SHUTDOWN
    # =========================================================

    async def shutdown(self) -> None:
        if self._shutdown_complete:
            return
        self._is_running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            await asyncio.gather(self._heartbeat_task, return_exceptions=True)
            self._heartbeat_task = None
        if self._stop_task:
            await self._stop_task
        else:
            if self._start_task and not self._start_task.done():
                self._start_task.cancel()
                await asyncio.gather(self._start_task, return_exceptions=True)
            await self._cleanup_runtime()
        try:
            if self._launcher:
                self._launcher.shutdown()
                self._launcher = None
        finally:
            if self._event_bus:
                await self._event_bus.stop()
            self._shutdown_complete = True
            if self._shutdown_future and not self._shutdown_future.done():
                self._shutdown_future.set_result(None)

    async def _stop_chibi_async(self):
        if self._chibi_app:
            await self._chibi_app.aclose()
            self._chibi_app = None

    # =========================================================
    # HELPERS
    # =========================================================

    def _get_components(self) -> list[str]:
        return [
            "event_bus",
            "command_bus",
            "repositories",
            "llm",
            "memory_engine",
            "emotion_engine",
            "mood_engine",
            "plugin_engine",
            "tool_executor",
            "pipeline",
            "chat_orchestration",
        ]

    def is_system_ready(self) -> bool:
        return self._is_system_ready

    def get_container(self) -> ApplicationContainer:
        return self._container

    def get_event_bus(self) -> Optional[EventBusPort]:
        return self._event_bus
