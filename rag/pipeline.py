import time
from typing import Dict, Any
from rag.loaders import DocumentLoader
from rag.chunking import Chunker
from rag.embeddings import Embedder
from rag.vector_store import VectorStore
from rag.schemas import RAGConfig

class RAGPipeline:
    def __init__(self, config: RAGConfig):
        self.config = config
        self.loader = DocumentLoader(self.config.project_name)
        self.chunker = Chunker(chunk_size=self.config.chunk_size, chunk_overlap=self.config.chunk_overlap)
        self.embedder = Embedder(model_name=self.config.embedding_model_name)
        self.vector_store = VectorStore(store_path=self.config.vector_store_path)
        
    def build_index(self, project_path: str) -> Dict[str, Any]:
        start_time = time.time()
        
        self.loader.project_path = project_path
        files = self.loader.discover_files()
        
        all_chunks = []
        for file_path in files:
            text = self.loader.load_text(file_path)
            chunks = self.chunker.chunk_text(text, file_path=file_path, project_name=self.config.project_name)
            all_chunks.extend(chunks)
            
        embeddings = self.embedder.embed_texts([c.content for c in all_chunks])
        self.vector_store.add_chunks(all_chunks, embeddings)
        
        duration = time.time() - start_time
        
        return {
            "num_documents": len(files),
            "num_chunks": len(all_chunks),
            "embedding_model": self.config.embedding_model_name,
            "indexing_duration": duration,
            "index_location": self.config.vector_store_path
        }
