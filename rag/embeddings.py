from sentence_transformers import SentenceTransformer
from typing import List
import numpy as np

class Embedder:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        if not texts:
            return np.array([])
        return self.model.encode(texts)
    
    def embed_query(self, query: str) -> np.ndarray:
        return self.model.encode([query])[0]
