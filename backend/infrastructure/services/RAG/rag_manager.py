from typing import List, Dict, Any
import pickle
from sentence_transformers import SentenceTransformer
import faiss
from pathlib import Path
from logger import log


class RAGManager:
    """
    A comprehensive RAG (Retrieval Augmented Generation) manager that handles document storage,
    embedding creation, similarity search, and memory persistence.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", index_path: str = None):
        self.model = SentenceTransformer(model_name)
        
        # Ensure parent directory exists for the index file
        if index_path is None:
            # Create a data directory in the backend infrastructure folder
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True, parents=True)
            self.index_path = str(data_dir / "rag_index.faiss")
        else:
            # Ensure parent directory exists for custom path
            index_file_path = Path(index_path)
            index_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.index_path = str(index_file_path)
        
        # Initialize FAISS index and metadata
        self.dimension = self.model.get_sentence_embedding_dimension()
        if self.dimension is None:
            self.dimension = 384  # Default dimension
            
        self.index = faiss.IndexFlatIP(self.dimension)  # Using Inner Product for cosine similarity
        self.texts = []
        self.metadata = []  # Store additional metadata for each text entry
        
        # Log the path being used
        log(f"RAGManager initialized with index path: {self.index_path}", 'info', __name__)
        
        # Load existing index if it exists
        self.load_index()

    def add_document(self, text: str, metadata: Dict[str, Any] = None):
        """
        Add a document to the RAG system
        """
        if not text.strip():
            return
            
        # Create embedding for the text
        embedding = self.model.encode([text])
        embedding = embedding.astype('float32')
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embedding)
        
        # Add to FAISS index
        self.index.add(embedding)
        
        # Store the text and metadata
        self.texts.append(text)
        self.metadata.append(metadata or {})
        
        # Save updated index
        self.save_index()

    def add_documents(self, texts: List[str], metadatas: List[Dict[str, Any]] = None):
        """
        Add multiple documents to the RAG system
        """
        if not texts:
            return
            
        # Prepare metadata
        if metadatas is None:
            metadatas = [{}] * len(texts)
        elif len(metadatas) != len(texts):
            raise ValueError("Number of texts and metadatas must match")
            
        # Filter out empty texts
        valid_pairs = [(text, meta) for text, meta in zip(texts, metadatas) if text.strip()]
        if not valid_pairs:
            return
            
        valid_texts, valid_metadatas = zip(*valid_pairs)
        
        # Create embeddings
        embeddings = self.model.encode(list(valid_texts))
        embeddings = embeddings.astype('float32')
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to FAISS index
        self.index.add(embeddings)
        
        # Store texts and metadata
        self.texts.extend(list(valid_texts))
        self.metadata.extend(list(valid_metadatas))
        
        # Save updated index
        self.save_index()

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for the most relevant documents given a query
        """
        if not query.strip() or self.index.ntotal == 0:
            return []
            
        # Create embedding for the query
        query_embedding = self.model.encode([query])
        query_embedding = query_embedding.astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Perform similarity search
        scores, indices = self.index.search(query_embedding, top_k)
        
        # Prepare results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.texts):  # Ensure index is valid
                results.append({
                    'text': self.texts[idx],
                    'metadata': self.metadata[idx],
                    'similarity_score': float(score)
                })
        
        return results

    def save_index(self):
        """
        Save the FAISS index and associated data to disk
        """
        try:
            # Ensure directory exists before saving
            index_path_obj = Path(self.index_path)
            index_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, str(index_path_obj))
            
            # Save texts and metadata separately
            data_path = self.index_path.replace('.faiss', '_data.pkl')
            with open(data_path, 'wb') as f:
                pickle.dump({
                    'texts': self.texts,
                    'metadata': self.metadata
                }, f)
            
            log(f"RAG index saved successfully with {len(self.texts)} entries", 'info', __name__)
        except Exception as e:
            print(f"Error saving RAG index: {e}")

    def load_index(self):
        """
        Load the FAISS index and associated data from disk
        """
        try:
            index_path = Path(self.index_path)
            data_path = Path(self.index_path.replace('.faiss', '_data.pkl'))
            
            if index_path.exists() and data_path.exists():
                # Load FAISS index
                self.index = faiss.read_index(str(index_path))
                
                # Load texts and metadata
                with open(data_path, 'rb') as f:
                    data = pickle.load(f)
                    self.texts = data['texts']
                    self.metadata = data['metadata']
                
                log(f"RAG index loaded successfully with {len(self.texts)} entries", 'info', __name__)
            else:
                log(f"RAG index files not found at {self.index_path}, starting fresh", 'info', __name__)
        except Exception as e:
            print(f"Error loading RAG index: {e}")
            # If loading fails, initialize with empty data
            self.index = faiss.IndexFlatIP(self.dimension)
            self.texts = []
            self.metadata = []

    def delete_by_metadata(self, key: str, value: Any):
        """
        Delete entries that match a specific metadata key-value pair
        """
        indices_to_remove = []
        for i, meta in enumerate(self.metadata):
            if meta.get(key) == value:
                indices_to_remove.append(i)
        
        if indices_to_remove:
            remaining_indices = [i for i in range(len(self.texts)) if i not in indices_to_remove]
            
            if remaining_indices:
                remaining_texts = [self.texts[i] for i in remaining_indices]
                remaining_metadata = [self.metadata[i] for i in remaining_indices]
                
                embeddings = self.model.encode(remaining_texts)
                embeddings = embeddings.astype('float32')
                faiss.normalize_L2(embeddings)
                
                self.index = faiss.IndexFlatIP(self.dimension)
                self.index.add(embeddings)

                self.texts = remaining_texts
                self.metadata = remaining_metadata
            else:
                self.index = faiss.IndexFlatIP(self.dimension)
                self.texts = []
                self.metadata = []

            self.save_index()

    def clear(self):
        """
        Clear all stored documents
        """
        self.index = faiss.IndexFlatIP(self.dimension)
        self.texts = []
        self.metadata = []
        
        index_path = Path(self.index_path)
        data_path = self.index_path.replace('.faiss', '_data.pkl')
        
        if index_path.exists():
            index_path.unlink()
        if data_path.exists():
            data_path.unlink()