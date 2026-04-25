from typing import List
import yaml
from backend.core.schemas.tool_schema import ToolSchema
from ..schemas.message_schema import MessageHistory
from paths import CONFIGS


class Agent():
    def __init__(self):
        super().__init__() 
        self.name: str
        self.tools: List[ToolSchema]
        self.system_prompt: str = ""
        self.load_config("chibi.yaml")

        self.history: List[MessageHistory] = []
        

        if self.system_prompt:
            self.history.append(MessageHistory(
                role='system',
                content=self.system_prompt
            ))
        

    def reset(self):
        self.history.clear()


    def add_message(self, message: MessageHistory):
        self.history.append(message)


    def remove_message(self, message: MessageHistory):
        self.history.remove(message)


    def get_history(self) -> List[MessageHistory]:
        return self.history


    def get_last(self) -> MessageHistory:
        return self.history[-1]
    
    def get_system(self) -> MessageHistory:
        return self.history[0]
    
    def record_message(self, index: int, message: MessageHistory) -> bool:
        self.history[index] = message
        return True
    
    def load_config(self, yaml_file: str):
        with open(f'{CONFIGS}/{yaml_file}', 'r') as file:
            config = yaml.safe_load(file)
            # self.tools = [ToolSchema(**tool) for tool in config['tools']]
            self.name = config['name']
            self.system_prompt = config['system_prompt']


    def get_tools(self) -> List[ToolSchema]:
        return self.tools

