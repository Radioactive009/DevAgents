import os
import pickle
import numpy as np
try:
    import faiss
except ImportError:
    pass
from typing import List, Tuple, Dict
from rag.schemas import RAGChunk

class VectorStore:
    def __init__(self, store_path: str, dimension: int = 384):
        self.store_path = store_path
        self.dimension = dimension
        self.index = faiss.IndexFlatL2(self.dimension)
        self.chunks: List[RAGChunk] = []
        
        self.load()
        
    def add_chunks(self, chunks: List[RAGChunk], embeddings: np.ndarray):
        if len(chunks) == 0:
            return
            
        self.index.add(embeddings.astype('float32'))
        self.chunks.extend(chunks)
        self.save()
        
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Tuple[RAGChunk, float]]:
        if len(self.chunks) == 0:
            return []
            
        distances, indices = self.index.search(np.array([query_embedding]).astype('float32'), min(top_k, len(self.chunks)))
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.chunks):
                results.append((self.chunks[idx], float(distances[0][i])))
                
        return results
        
    def save(self):
        os.makedirs(os.path.dirname(self.store_path) or '.', exist_ok=True)
        faiss.write_index(self.index, f"{self.store_path}.faiss")
        with open(f"{self.store_path}.pkl", "wb") as f:
            pickle.dump(self.chunks, f)
            
    def load(self):
        if os.path.exists(f"{self.store_path}.faiss") and os.path.exists(f"{self.store_path}.pkl"):
            self.index = faiss.read_index(f"{self.store_path}.faiss")
            with open(f"{self.store_path}.pkl", "rb") as f:
                self.chunks = pickle.load(f)
