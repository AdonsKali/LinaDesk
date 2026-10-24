from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, Literal, Optional
from uuid import UUID, uuid4
from src.core.domain.value_objects.plugin import Plugin
from src.core.domain.value_objects.behavior_policy import BehaviorPolicy


class LogLevel(str, Enum):
    """Уровни логирования."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"    
    
@dataclass(slots=True)   
class LLMSettings:
    """Настройки LLM."""
    mmproj_path: Optional[str]
    model_path: Optional[str]
    provider: Literal["llamacpp", "OpenAI"]
    context_window: int
    n_gpu_layers: int
    n_threads: int
    flash_attn: bool   
    chat_handler: str = "gemma4"
    
    
    def __post_init__(self):
        # Валидация на уровне доменного объекта
        if self.context_window < 0:
            raise ValueError(f"Invalid context window, it must be non-negative: {self.context_window}")
        if self.n_gpu_layers < -1:
            raise ValueError("n_gpu_layers must be -1 (all), 0 (automatic), or a positive layer count")
        if self.n_threads < 0:
            raise ValueError("n_threads must be non-negative")

    
@dataclass(slots=True)
class Settings:
    """Value Object для настроек - доменный объект значения"""
    version: str
    
    on_log: bool
    on_gpu: bool
    on_debug: bool
    on_economy: bool
    language: str
    username: str
    microphone: Optional[str | int]
    camera: Optional[str] 
    
    plugins: Optional[list[Plugin]] 
    on_sandbox: bool 
    on_server: bool 
    autonomy: Literal["semi-autonomous", "autonomous"]
    on_plugins: bool
    
    llm: LLMSettings
    
    user_id: str
    behavior: BehaviorPolicy = field(default_factory=BehaviorPolicy)
    
    def __post_init__(self):
        # Валидация на уровне доменного объекта
        if self.language not in ["en", "ru", "zh"]:
            raise ValueError(f"Invalid language: {self.language}")
        
        if self.username.strip() == "":
            raise ValueError("Username cannot be empty")
        
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Settings':
        """Создание объекта Settings из словаря с глубокой конвертацией."""
        if not data:
            return cls.default()
            
        # Копируем словарь, чтобы не мутировать исходные данные
        processed_data = cls.default().to_dict()
        processed_data.update(data)
        
        # Получаем данные для вложенного LLMSettings
        llm_data = processed_data.get("llm")
        
        # Если там словарь, превращаем его в объект LLMSettings
        if isinstance(llm_data, dict):
            # Фильтруем ключи на случай, если в словаре есть лишние поля
            valid_llm_fields = cls.default().to_dict()["llm"]
            valid_llm_fields.update({k: v for k, v in llm_data.items() if k in LLMSettings.__dataclass_fields__})
            processed_data["llm"] = LLMSettings(**valid_llm_fields)
        elif llm_data is None:
            # Если llm настроек нет в словаре, можно создать дефолтные
            processed_data["llm"] = LLMSettings(
                mmproj_path=None, model_path=None, provider="llamacpp",
                context_window=0, n_gpu_layers=0, n_threads=0, flash_attn=False
            )
            
        if isinstance(processed_data.get("behavior"), dict):
            processed_data["behavior"] = BehaviorPolicy.from_dict(processed_data["behavior"])

        # Фильтруем поля для самого класса Settings
        valid_settings_fields = {
            k: v for k, v in processed_data.items() 
            if k in cls.__dataclass_fields__
        }
        
        return cls(**valid_settings_fields)

    
    
    
    @classmethod
    def default(cls) -> 'Settings':
        """Создание настроек по умолчанию"""
        return cls(
                version = "1.0.6",
                on_log  = False,
                on_gpu = False,
                on_debug  = False,
                on_economy  = False,
                language = "en",
                username = "user",
                microphone  = "default",
                camera = "default",
                
                plugins = None,
                on_sandbox = False,
                on_server = False,
                autonomy = "semi-autonomous",
                on_plugins = False,
                
                user_id = str(uuid4()),
                behavior = BehaviorPolicy(),
                
                llm = LLMSettings(
                    mmproj_path = None,
                    model_path = None,
                    provider = "llamacpp",
                    context_window = 1086,
                    n_gpu_layers = -1,
                    n_threads = 8,
                    flash_attn = False
                )
            )
        
    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        data = asdict(self)
        for key in ("identity", "autonomous_tools"):
            data["behavior"][key] = list(data["behavior"][key])
        return data
