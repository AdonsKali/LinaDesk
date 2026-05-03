import pickle
from utils.logger import log
from typing import List, Dict, Optional, Union
from pathlib import Path
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from backend.application.interfaces.rag_abc import RAGABC
from utils.logger import get_logger

log = get_logger(__name__)


class RAGService(RAGABC):
    """
    Simple but quality RAG (Retrieval Augmented Generation) service
    Allows storing, retrieving, and searching documents using vector embeddings
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the RAG service
        
        Args:
            model_name: Name of the sentence transformer model to use for embeddings
            index_path: Path to store/load the vector index
        """
        index_path = "backend/infrastructure/data/rag_index.faiss"
        self.index_path = Path("backend/infrastructure/data/rag_index.faiss")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        log.info(f"Loading embedding model: {model_name}")
        self.encoder = SentenceTransformer(model_name)
        self.documents: List[Dict[str, Union[str, Dict]]] = []
        self.embeddings: Optional[np.ndarray] = None
        if self.index_path.exists():
            self.load_index()
        else:
            log.info(f"No existing index found at {index_path}. Creating new index.")
    
    def add_document(self, content: str, metadata: Optional[Dict] = None, doc_id: Optional[str] = None) -> str:
        """
        Add a document to the RAG index
        
        Args:
            content: Text content of the document
            metadata: Optional metadata dictionary
            doc_id: Optional document ID (auto-generated if not provided)
            
        Returns:
            Document ID
        """
        if not doc_id:
            doc_id = f"doc_{len(self.documents)}"
        
        document = {
            "id": doc_id,
            "content": content,
            "metadata": metadata or {}
        }
        
        self.documents.append(document)
        new_embedding = self.encoder.encode([content])
        if self.embeddings is None:
            self.embeddings = new_embedding
        else:
            self.embeddings = np.vstack([self.embeddings, new_embedding])
        
        log.info(f"Added document {doc_id} to index")
        return doc_id
    
    def add_documents(self, documents: List[Dict[str, Union[str, Dict]]]) -> List[str]:
        """
        Add multiple documents at once
        
        Args:
            documents: List of documents in format {"content": "...", "metadata": {}, "id": "..."}
            
        Returns:
            List of document IDs
        """
        doc_ids = []
        
        contents = [doc["content"] for doc in documents]
        embeddings = self.encoder.encode(contents)
        
        for i, doc in enumerate(documents):
            doc_id = doc.get("id") or f"doc_{len(self.documents) + i}"
            document = {
                "id": doc_id,
                "content": doc["content"],
                "metadata": doc.get("metadata", {})
            }
            
            self.documents.append(document)
            doc_ids.append(doc_id)
        
        if self.embeddings is None:
            self.embeddings = embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings])
        
        log.info(f"Added {len(documents)} documents to index")
        return doc_ids
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Union[str, Dict, float]]]:
        """
        Search for relevant documents given a query
        
        Args:
            query: Search query
            top_k: Number of top results to return
            
        Returns:
            List of documents with similarity scores in format:
            [{"content": "...", "metadata": {}, "score": 0.x}, ...]
        """
        if not self.documents or self.embeddings is None:
            log.warning("No documents in index")
            return []
        
        query_embedding = self.encoder.encode([query])
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score > 0.01:  # Filter out very low similarity matches
                doc = self.documents[idx]
                results.append({
                    "id": doc["id"],
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": score
                })
        
        log.info(f"Found {len(results)} results for query: {query[:50]}...")
        return results
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Union[str, Dict]]]:
        """
        Retrieve a specific document by ID
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document or None if not found
        """
        for doc in self.documents:
            if doc["id"] == doc_id:
                return doc
        return None
    
    def remove_document(self, doc_id: str) -> bool:
        """
        Remove a document by ID
        
        Args:
            doc_id: Document ID to remove
            
        Returns:
            True if document was removed, False otherwise
        """
        for i, doc in enumerate(self.documents):
            if doc["id"] == doc_id:
                self.documents.pop(i)
                if self.embeddings.shape[0] > 1:
                    self.embeddings = np.delete(self.embeddings, i, axis=0)
                else:
                    self.embeddings = None
                
                log.info(f"Removed document {doc_id}")
                return True
        
        log.warning(f"Document {doc_id} not found for removal")
        return False
    
    def save_index(self):
        """Save the current index to disk"""
        data = {
            "documents": self.documents,
            "embeddings": self.embeddings
        }
        with open(self.index_path, "wb") as f:
            pickle.dump(data, f)
        log.info(f"Saved index with {len(self.documents)} documents to {self.index_path}")
    
    def load_index(self):
        """Load the index from disk"""
        try:
            with open(self.index_path, "rb") as f:
                data = pickle.load(f)
            
            self.documents = data["documents"]
            self.embeddings = data["embeddings"]
            
            log.info(f"Loaded index with {len(self.documents)} documents from {self.index_path}")
        except Exception as e:
            log.error(f"Failed to load index from {self.index_path}: {e}")
            self.documents = []
            self.embeddings = None
    
    def clear_index(self):
        """Clear all documents from the index"""
        self.documents = []
        self.embeddings = None
        log.info("Cleared RAG index")
        if self.index_path.exists():
            self.index_path.unlink()
    
    def get_document_count(self) -> int:
        """Get the number of documents in the index"""
        return len(self.documents)