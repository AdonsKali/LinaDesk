from .view.widgets.launcher_window import LauncherWindow
from .viewmodel.launcher_controller import ViewLauncher
from utils.logger import setup, get_logger

setup(app_name="launcher", log_dir="logs", debug=False, clear_on_start=True)
logger = get_logger(__name__)

class Launcher:
    def __init__(self):
        self.viewmodel = ViewLauncher()
        self.launcher = LauncherWindow(self.viewmodel)
        self.launcher.show()