from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Union


class RAGABC(ABC):
    """Base interface for RAG (Retrieval Augmented Generation) services"""
    
    @abstractmethod
    def add_document(self, content: str, metadata: Optional[Dict] = None, doc_id: Optional[str] = None) -> str:
        """Add a single document to the index"""
        pass
    
    @abstractmethod
    def add_documents(self, documents: List[Dict[str, Union[str, Dict]]]) -> List[str]:
        """Add multiple documents to the index"""
        pass
    
    @abstractmethod
    def search(self, query: str, top_k: int = 3, similarity_threshold: float = 0.4) -> List[Dict[str, Union[str, Dict, float]]]:
        """Search for relevant documents"""
        pass
    
    @abstractmethod
    def should_remember_conversation(self, user_query: str, threshold: float = 0.65) -> bool:
        """Check if the user wants to save the conversation"""
        pass
    
    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[Dict[str, Union[str, Dict]]]:
        """Retrieve a document by ID"""
        pass
    
    @abstractmethod
    def remove_document(self, doc_id: str) -> bool:
        """Remove a document by ID"""
        pass
    
    @abstractmethod
    def save_index(self) -> None:
        """Save the current index to disk"""
        pass
    
    @abstractmethod
    def load_index(self) -> None:
        """Load the index from disk"""
        pass
    
    @abstractmethod
    def clear_index(self) -> None:
        """Clear all documents from the index"""
        pass
    
    @abstractmethod
    def get_document_count(self) -> int:
        """Get the number of documents in the index"""
        pass