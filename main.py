import sys
from launcher import Launcher
from PySide6.QtWidgets import QApplication
from app.src.view.launcher_controller import ViewLauncher

if __name__ == "__main__":
    app = QApplication(sys.argv)
    viewmodel = ViewLauncher()
    window = Launcher(viewmodel)
    window.show()
    sys.exit(app.exec()) 