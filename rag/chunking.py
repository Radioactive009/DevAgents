from typing import List
from rag.schemas import RAGChunk
import uuid

class Chunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
    def chunk_text(self, text: str, file_path: str, project_name: str) -> List[RAGChunk]:
        chunks = []
        if not text.strip():
            return chunks
            
        # Simple character-based overlapping chunking
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + self.chunk_size, text_len)
            
            # If not at the end, try to find a natural break (newline)
            if end < text_len:
                last_newline = text.rfind('\n', start, end)
                if last_newline != -1 and last_newline > start + self.chunk_size // 2:
                    end = last_newline + 1
                    
            chunk_content = text[start:end]
            
            chunk = RAGChunk(
                chunk_id=str(uuid.uuid4()),
                content=chunk_content.strip(),
                source=file_path,
                file_path=file_path,
                document_type="source_code" if file_path.endswith('.py') else "documentation",
                project=project_name
            )
            chunks.append(chunk)
            
            if end == text_len:
                break
                
            start = end - self.chunk_overlap
            
        return chunks
