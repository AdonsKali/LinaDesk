from abc import ABC,abstractmethod

class RecognizeABC(ABC):
    
    @abstractmethod
    def start(self, sample_rate) -> bool:
        ...


    @abstractmethod
    def feed(self, bytes: bytes) -> str:
        ...


    @abstractmethod
    def finish(self) -> str:
        ...

    
