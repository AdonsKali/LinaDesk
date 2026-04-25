from abc import ABC,abstractmethod


class ToolManagerABC(ABC):
    @abstractmethod
    def execute(self, name: str, args: dict):
        ...



