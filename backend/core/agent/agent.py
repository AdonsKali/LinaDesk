from typing import Dict, List, Literal, Union
import yaml
from paths import CONFIGS


class Agent():
    def __init__(self, yaml_config: str):
        super().__init__() 
        self.name: str
        self._tools: List[str]
        self._system_prompt: str = ""
        self._generation_params = {}
        self._max_steps: int
        self._rag: bool
        self.load_config(yaml_config)
        
        # Храним историю как список словарей
        self._history: List[Dict] = []
        
        if self._system_prompt:
            self._history.append({
                'role': 'system',
                'content': self._system_prompt
            })
    
    def reset(self):
        """Сброс истории"""
        self._history.clear()
        if self._system_prompt:
            self._history.append({
                'role': 'system',
                'content': self._system_prompt
            })
    
    def add_message(self, role: Literal["system", "user", "assistant"], 
                    content: Union[str, list]):
        """Добавление сообщения в историю"""
        self._history.append({
            'role': role,
            'content': content
        })
    
    def add_user_message(self, content: Union[str, list]):
        """Добавление пользовательского сообщения"""
        self._history.append({
            'role': 'user',
            'content': content
        })
    
    def add_assistant_message(self, content: Union[str, list]):
        """Добавление ответа ассистента"""
        self._history.append({
            'role': 'assistant',
            'content': content
        })
    
    def add_tool_result(self, tool_name: str, result):
        """Добавление результата выполнения инструмента"""
        self._history.append({
            'role': 'assistant',
            'content': self._format_tool_result(tool_name, result)
        })
    
    def remove_last_message(self) -> Dict | None:
        """Удалить последнее сообщение"""
        return self._history.pop() if self._history else None
    
    def get_last(self) -> Dict | None:
        """Получить последнее сообщение"""
        return self._history[-1] if self._history else None
    
    def get_system(self) -> Dict | None:
        """Получить системное сообщение"""
        return self._history[0] if self._history and self._history[0]['role'] == 'system' else None
    

    def get_user_content_without_media(self) -> List[Dict]:
        """Удаление изображений из истории"""
        if self.history:
            last_msg = self.get_last()
            if last_msg and last_msg.get('role') == 'user':
                content: List[Dict] = last_msg.get('content', [])
                if isinstance(content, list):
                    filtered_content = [
                        item for item in content 
                        if item.get('type') != 'image_url' or item.get('type') != 'input_audio'
                    ]
                    return filtered_content
        return []
    
    @property
    def history(self) -> List[Dict]:
        """Получить всю историю (уже в формате для LLM)"""
        return self._history
    
    @property
    def tools(self) -> List[str]:
        return self._tools
    
    @property
    def max_steps(self) -> int:
        return self._max_steps
    
    @property
    def rag(self) -> bool:
        return self._rag
    
    @property
    def generation_params(self) -> dict:
        return self._generation_params
    
    def load_config(self, yaml_file: str):
        """Загрузка конфигурации из YAML"""
        with open(f'{CONFIGS}/{yaml_file}', 'r') as file:
            config = yaml.safe_load(file)
            self._tools = [tool for tool in config['tools']]
            self.name = config['name']
            self._system_prompt = config['system_prompt']
            self._rag = config['RAG']
            self._max_steps = config['max_steps']
            
            self._generation_params['max_tokens'] = config['generation_params']['max_tokens']
            self._generation_params['temperature'] = config['generation_params']['temperature']
            self._generation_params['top_p'] = config['generation_params']['top_p']
            self._generation_params['top_k'] = config['generation_params']['top_k']
    
    def _format_tool_result(self, tool_name: str, result) -> str:
        """Форматирование результата инструмента (вспомогательный метод)"""
        import json
        
        if hasattr(result, 'status'):
            if result.status == 'ok':
                output = f"<tool_result>\nTool: {tool_name}\nStatus: SUCCESS\n"
                if result.msg:
                    output += f"Message: {result.msg}\n"
                if result.data:
                    output += f"Data: {json.dumps(result.data, ensure_ascii=False)[:500]}\n"
                output += "</tool_result>"
                return output
            else:
                return f"<tool_result>\nTool: {tool_name}\nStatus: ERROR\nMessage: {result.msg or 'Unknown error'}\n</tool_result>"
        return f"<tool_result>\nTool: {tool_name}\nResult: {str(result)}\n</tool_result>"
    
    def __len__(self) -> int:
        """Длина истории"""
        return len(self._history)
    
    def __getitem__(self, index: int) -> Dict:
        """Доступ по индексу"""
        return self._history[index]
    
    def __str__(self) -> str:
        """Строковое представление для логирования"""
        result = f"Agent: {self.name}\nHistory:\n"
        for msg in self._history:
            role = msg['role']
            content = str(msg['content'])[:100]  # Обрезаем для читаемости
            result += f"  {role}: {content}...\n"
        return result