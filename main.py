import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("logo.ico"))
    from launcher import Launcher
    launcher = Launcher()
    launcher.show()
    sys.exit(app.exec()) 