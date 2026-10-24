import sys
import asyncio
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtCore import QProcess
from PySide6.QtGui import QIcon
from qasync import QEventLoop

from src.bootstrap.app import Application
from src.core.utils.logger import logger


def main():
    os.chdir(Path(__file__).resolve().parent)
    if os.name == "nt":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LinaAI.Desktop")
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    qt_app = QApplication(sys.argv)
    qt_app.setWindowIcon(QIcon(str(Path(__file__).resolve().parent / "logo.ico")))
    qt_app.setQuitOnLastWindowClosed(False)

    loop = QEventLoop(qt_app)
    asyncio.set_event_loop(loop)

    application = Application(
        ui_type="qt",
        qt_app=qt_app,
    )
    shutdown_ok = False

    try:
        loop.run_until_complete(application.run())

    except KeyboardInterrupt:
        pass

    finally:
        if not loop.is_closed():
            try:
                loop.run_until_complete(
                    application.shutdown()
                )
                shutdown_ok = True
            except Exception:
                logger.exception("Application shutdown failed")

            loop.close()

        qt_app.quit()
        if shutdown_ok and getattr(application, "restart_requested", False):
            executable = sys.executable
            if os.name == "nt":
                windowless = Path(executable).with_name("pythonw.exe")
                if windowless.exists():
                    executable = str(windowless)
            started, _pid = QProcess.startDetached(
                executable, [str(Path(__file__).resolve()), *sys.argv[1:]],
                str(Path(__file__).resolve().parent))
            if not started:
                logger.error("Failed to restart application")


if __name__ == "__main__":
    main()
