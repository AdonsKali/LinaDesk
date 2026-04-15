import yaml
from backend.core.agent import Agent
from backend.infrastructure.tools.manager import ToolManager
from backend.core.schemas.message_schema import MessageHistory


class AgentFactory:
    def __init__(self, tool_manager: ToolManager, config_dir="backend/agents/configs/"):
        self.tool_manager = tool_manager
        self.config_dir = config_dir

    def create(self, agent_name: str) -> Agent:
        # Загружаем YAML
        with open(f"{self.config_dir}/{agent_name}.yaml", "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        agent = Agent()
        agent.config = cfg
        agent.tools = self.tool_manager.get_tools(cfg["tools"])
        # Инициализируем системное сообщение
        agent.add_message(MessageHistory(role="system", content=cfg["system_prompt"]))
        return agent