from .tools import *
import json


class Manager():
    def __init__(self):
        super().__init__()
        self.tools = {
            "open": run,
            "mk_dir": mk_dir,
            "mk_file": mk_file,
            "read": read,
            "search_web": duckduckgo_search_with_rich_snippets,
            "list_directory": list_directory,
            "cmd": execute_cmd,
            "shell": execute_ps
        }


    def execute(self, name, args):
        result = self.tools[name](**args)
        return result