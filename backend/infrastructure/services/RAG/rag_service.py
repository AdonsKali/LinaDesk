from pathlib import Path
from typing import List, Dict, Optional, Union
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from backend.application.interfaces.rag_abc import RAGABC
from utils.logger import logger

log = logger.get(__name__)


class RAGService(RAGABC):
    """
    RAG (Retrieval Augmented Generation) service for document storage and search
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the RAG service
        
        Args:
            model_name: Name of the sentence transformer model to use for embeddings
        """
        self.index_path = Path("backend/infrastructure/data/rag_index.faiss")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        
        log.debug(f"Loading embedding model: {model_name}")
        self.encoder = SentenceTransformer(model_name)
        self.documents: List[Dict[str, Union[str, Dict]]] = []
        self.embeddings: Optional[np.ndarray] = None
        
        if self.index_path.exists():
            self.load_index()
        else:
            log.warning(f"No existing index found at {self.index_path}. Creating new index.")
    
    def add_document(self, content: str, metadata: Optional[Dict] = None, doc_id: Optional[str] = None) -> str:
        """Add a document to the RAG index"""
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
        
        log.debug(f"Added document {doc_id} to index")
        return doc_id
    
    def add_documents(self, documents: List[Dict[str, Union[str, Dict]]]) -> List[str]:
        """Add multiple documents at once"""
        contents = [doc["content"] for doc in documents]
        embeddings = self.encoder.encode(contents) #type: ignore
        doc_ids = []
        
        for i, doc in enumerate(documents):
            doc_id = doc.get("id") or f"doc_{len(self.documents) + i}"
            self.documents.append({
                "id": doc_id,
                "content": doc["content"],
                "metadata": doc.get("metadata", {})
            })
            doc_ids.append(doc_id)
        
        if self.embeddings is None:
            self.embeddings = embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings])
        
        log.debug(f"Added {len(documents)} documents to index")
        return doc_ids
    
    def search(self, query: str, top_k: int = 3, similarity_threshold: float = 0.4) -> List[Dict[str, Union[str, Dict, float]]]:
        """Search for relevant documents given a query"""
        if not self.documents or self.embeddings is None:
            log.warning("No documents in index")
            return []
        
        query_embedding = self.encoder.encode([query])
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        sorted_indices = np.argsort(similarities)[::-1]
        
        results = []
        for idx in sorted_indices:
            score = float(similarities[idx])
            if score >= similarity_threshold:
                doc = self.documents[idx]
                results.append({
                    "id": doc["id"],
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": score
                })
            
            if len(results) >= top_k:
                break

        if results:
            avg_score = sum(r["score"] for r in results) / len(results)
            log.debug(f"Found {len(results)} results for query: '{query[:50]}...' "
                    f"(threshold={similarity_threshold}, avg_score={avg_score:.3f})")
        
        return results
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Union[str, Dict]]]:
        """Retrieve a specific document by ID"""
        for doc in self.documents:
            if doc["id"] == doc_id:
                return doc
        return None
    
    def remove_document(self, doc_id: str) -> bool:
        """Remove a document by ID"""
        for i, doc in enumerate(self.documents):
            if doc["id"] == doc_id:
                self.documents.pop(i)
                if self.embeddings is not None:
                    if self.embeddings.shape[0] > 1:
                        self.embeddings = np.delete(self.embeddings, i, axis=0)
                    else:
                        self.embeddings = None
                
                log.debug(f"Removed document {doc_id}")
                return True
        
        log.warning(f"Document {doc_id} not found for removal")
        return False
    
    def should_remember_conversation(self, user_query: str, threshold: float = 0.65) -> bool:
        """
        Determines whether the user wants to save the conversation
        
        Args:
            user_query: Current user query
            threshold: Similarity threshold (0-1)
            
        Returns:
            True if should remember, False otherwise
        """
        if not user_query or not user_query.strip():
            return False
        
        remember_commands = [
            "запомни это", "запомни", "запомни разговор", "сохрани это",
            "сохрани в память", "запомни информацию", "важно запомнить","remember this", "save this", "memorize this", "记住", "记住这个", "记得谈话", 
            "保存这个", "保存在内存中", "记住信息"
        ]
        
        query_embedding = self.encoder.encode([user_query.lower().strip()])
        command_embeddings = self.encoder.encode(remember_commands)
        similarities = cosine_similarity(query_embedding, command_embeddings)[0]
        max_similarity = float(np.max(similarities))
        
        # Прямое попадание по ключевым словам для коротких команд
        direct_keywords = ["запомни", "сохрани", "remember", "save", "记住", "记住这个"]
        direct_match = any(keyword in user_query.lower() for keyword in direct_keywords)
        
        log.debug(f"Query: '{user_query}' - Best similarity: {max_similarity:.3f}")
        return max_similarity >= threshold or direct_match
    
    def save_index(self):
        """Save the current index to disk"""
        data = {
            "documents": self.documents,
            "embeddings": self.embeddings
        }
        with open(self.index_path, "wb") as f:
            pickle.dump(data, f)
        log.debug(f"Saved index with {len(self.documents)} documents to {self.index_path}")
    
    def load_index(self):
        """Load the index from disk"""
        try:
            with open(self.index_path, "rb") as f:
                data = pickle.load(f)
            
            self.documents = data["documents"]
            self.embeddings = data["embeddings"]
            log.debug(f"Loaded index with {len(self.documents)} documents from {self.index_path}")
        except Exception as e:
            log.error(f"Failed to load index from {self.index_path}: {e}")
            self.documents = []
            self.embeddings = None
    
    def clear_index(self):
        """Clear all documents from the index"""
        self.documents = []
        self.embeddings = None
        log.debug("Cleared RAG index")
        if self.index_path.exists():
            self.index_path.unlink()
    
    def get_document_count(self) -> int:
        """Get the number of documents in the index"""
        return len(self.documents)