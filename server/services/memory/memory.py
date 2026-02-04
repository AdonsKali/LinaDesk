import faiss
import numpy as np
from paths import DATABASES
from sentence_transformers import SentenceTransformer


class Memory:
    def __init__(self, embed_model="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(embed_model)
        self.dim = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dim)
        self.docs = [] 
        self.embs = []  


    def _embed(self, text: str) -> np.ndarray:
        vec = self.model.encode([text], convert_to_numpy=True)[0]
        faiss.normalize_L2(vec.reshape(1, -1))  # нормализация для cosine
        return vec
    

    def remember(self, text: str):
        """Add context to memory"""
        vec = self._embed(text)
        self.index.add(vec.reshape(1, -1))
        self.docs.append(text)
        self.embs.append(vec)


    def recall(self, query: str, k: int = 3):
        """Find k most near facts"""
        qvec = self._embed(query).reshape(1, -1)
        D, I = self.index.search(qvec, k)
        results = []
        for idx, score in zip(I[0], D[0]):
            if idx == -1: 
                continue
            results.append((self.docs[idx], float(score)))
        return results
    

    def save(self, path="memory.index", docs_path=f"{DATABASES}/temp_memory.npy"):
        """Save memory to disk"""
        faiss.write_index(self.index, path)
        np.save(docs_path, np.array(self.docs), allow_pickle=True)


    def load(self, path="memory.index", docs_path=f"{DATABASES}/temp_memory.npy"):
        """Load memory form disk"""
        self.index = faiss.read_index(path)
        self.docs = np.load(docs_path, allow_pickle=True).tolist()
        