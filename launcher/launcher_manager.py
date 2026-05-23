from utils.logger import logger
from launcher.model.launcher_model import LauncherModel
from launcher.model import LauncherModel

class Launcher:
    def __init__(self):
        self.model = LauncherModel()
        self.model.load_from_file()
        logger.setup(
            app_name="launcher",
            log_dir="logs",
            debug=self.model.on_debug,
            clear_on_start=True,
        )
        from .view.widgets.launcher_window import LauncherWindow
        from .viewmodel.launcher_controller import ViewLauncher
        self.viewmodel = ViewLauncher(self.model)
        self.launcher = LauncherWindow(self.viewmodel)
    
    def show(self):
        self.launcher.show()