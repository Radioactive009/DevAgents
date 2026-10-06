import time
from typing import List, Tuple, Dict, Any
from rag.schemas import RAGChunk
from rag.embeddings import Embedder
from rag.vector_store import VectorStore

class Retriever:
    def __init__(self, embedder: Embedder, vector_store: VectorStore):
        self.embedder = embedder
        self.vector_store = vector_store
        
    def retrieve(self, query: str, top_k: int = 5) -> Tuple[List[Dict[str, Any]], float]:
        """
        Retrieves relevant RAG chunks for a given query.
        Returns a tuple of (results list, latency in seconds).
        """
        start_time = time.time()
        if not query or not query.strip():
            return [], time.time() - start_time
            
        if len(self.vector_store.chunks) == 0:
            return [], time.time() - start_time
            
        query_embedding = self.embedder.embed_query(query)
        search_results = self.vector_store.search(query_embedding, top_k=top_k)
        
        results = []
        for chunk, score in search_results:
            results.append({
                "chunk_id": chunk.chunk_id,
                "text": chunk.content,
                "source": chunk.source,
                "file_path": chunk.file_path,
                "document_type": chunk.document_type,
                "project": chunk.project,
                "requirement_ids": chunk.requirement_ids,
                "score": score
            })
            
        latency = time.time() - start_time
        return results, latency
