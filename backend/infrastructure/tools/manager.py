from .system import *
from .web import *
from backend.core.schemas import ToolSchemaOut


class ToolManager():
    def __init__(self):
        super().__init__()
        self.cmd_ps = AIShellController(

        )
        self.player = MusicFinderAndStreamer(

        )

        self.tools = {
            "mk_file":mk_file,
            "search_web":duckduckgo_search_with_rich_snippets,
            "powerShell": self.cmd_ps.execute,
            "search_and_play": self.player.play_search,
            }
                
        
    def toolsConvert(self, toolOut: ToolSchemaOut | dict):
        if isinstance(toolOut, dict):
            return toolOut
        else:
            return {"status": toolOut.status, "msg": toolOut.msg, "data": toolOut.data}


    def execute(self, name, args):
        result = self.tools[name](**args)
        return self.toolsConvert(result)
    
    def get_tools(self, tool_names):
        """
        Returns a list of tools by name
        """
        result = []
        for name in tool_names:
            if name in self.tools:
                result.append(self.tools[name])
        return result