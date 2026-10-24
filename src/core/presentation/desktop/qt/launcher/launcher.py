from typing import Optional

from src.core.application.ports.event_port import EventBusPort
from src.core.application.ports.command_bus import CommandBusPort

from src.core.presentation.desktop.qt.launcher.viewmodel import (
    LauncherViewModel,
)

from src.core.presentation.desktop.qt.launcher.widgets.launcher_window import (
    LauncherWindow,
)

from src.core.utils.logger import logger


class Launcher:
    def __init__(
        self,
        command_bus: CommandBusPort,
        event_bus: EventBusPort,
    ):
        self._command_bus = command_bus
        self._event_bus = event_bus

        self._viewmodel = None
        self._window = None
        self._is_running = False

    def show(self) -> None:
        if self._is_running:
            if self._window:
                self._window.show()
                self._window.raise_()
            return

        self._viewmodel = LauncherViewModel(
            self._command_bus,
            self._event_bus,
        )

        self._window = LauncherWindow(
            self._viewmodel
        )

        self._window.show()

        self._is_running = True

        logger.info(
            "  ✅ Launcher window shown"
        )

    def shutdown(self) -> None:
        if not self._is_running:
            return

        self._is_running = False

        if self._window is not None:
            try:
                self._window._close_app()
                self._window.close()
                self._window.deleteLater()
            except Exception as e:
                logger.warning(
                    f"Error closing launcher window: {e}"
                )

            self._window = None

        if self._viewmodel is not None:
            try:
                self._viewmodel.close()
            except Exception as e:
                logger.warning(
                    f"Error closing launcher ViewModel: {e}"
                )

            self._viewmodel = None

        logger.info(
            "  ✅ Launcher shutdown complete"
        )

    def is_running(self) -> bool:
        return self._is_running
