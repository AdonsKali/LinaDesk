from typing import List
import yaml
from ..schemas.message_schema import MessageHistory
from paths import CONFIGS


class Agent():
    def __init__(self, yaml_config: str = "chibi.yaml"):
        super().__init__() 
        self.name: str
        self._tools: List[str]
        self._system_prompt: str = ""
        self._generation_params = {}
        self.load_config(yaml_config)

        self._history: List[MessageHistory] = []
        

        if self._system_prompt:
            self._history.append(MessageHistory(
                role='system',
                content=self._system_prompt
            ))
        

    def reset(self):
        self._history.clear()
        if self._system_prompt:
            self._history.append(MessageHistory(
                role='system',
                content=self._system_prompt
            ))


    def add_message(self, message: MessageHistory):
        self._history.append(message)


    def remove_message(self, message: MessageHistory):
        self._history.remove(message)

    @property
    def history(self) -> List[MessageHistory]:
        return self._history


    def get_last(self) -> MessageHistory:
        return self._history[-1]
    
    def get_system(self) -> MessageHistory:
        return self._history[0]
    
    def record_message(self, index: int, message: MessageHistory) -> bool:
        self._history[index] = message
        return True
    
    def load_config(self, yaml_file: str):
        with open(f'{CONFIGS}/{yaml_file}', 'r') as file:
            config = yaml.safe_load(file)
            self._tools = [tool for tool in config['tools']]
            self.name = config['name']
            self._system_prompt = config['system_prompt']

            self._generation_params['max_tokens'] = config['generation_params']['max_tokens']
            self._generation_params['temperature'] = config['generation_params']['temperature']
            self._generation_params['top_p'] = config['generation_params']['top_p']
            self._generation_params['top_k'] = config['generation_params']['top_k']

    @property
    def generation_params(self) -> dict:
        return self._generation_params

    @property
    def tools(self) -> List[str]:
        return self._tools

