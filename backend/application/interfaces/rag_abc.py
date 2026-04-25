from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Union


class RAGABC(ABC):
    @abstractmethod
    def add_document(self, content: str, metadata: Optional[Dict] = None, doc_id: Optional[str] = None) -> str:
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[Dict[str, Union[str, Dict]]]) -> List[str]:
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Union[str, Dict, float]]]:
        pass
    
    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[Dict[str, Union[str, Dict]]]:
        pass
    
    @abstractmethod
    def remove_document(self, doc_id: str) -> bool:
        pass
    
    @abstractmethod
    def save_index(self):
        """Save the current index to disk"""
        pass
    
    @abstractmethod
    def load_index(self):
        """Load the index from disk"""
        pass
    
    @abstractmethod
    def clear_index(self):
        """Clear all documents from the index"""
        pass
    
    @abstractmethod
    def get_document_count(self) -> int:
        """Get the number of documents in the index"""
        pass