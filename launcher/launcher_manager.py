from .view.widgets.launcher_window import LauncherWindow
from .viewmodel.launcher_controller import ViewLauncher

class Launcher:
    def __init__(self):
        self.viewmodel = ViewLauncher()
        self.launcher = LauncherWindow(self.viewmodel)
        self.launcher.show()