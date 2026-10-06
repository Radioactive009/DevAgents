import os
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class RAGChunk:
    chunk_id: str
    content: str
    source: str
    file_path: str
    document_type: str
    project: str
    requirement_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class RAGConfig:
    use_rag: bool = True
    use_memory: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 200
    embedding_model_name: str = 'all-MiniLM-L6-v2'
    vector_store_path: str = 'rag_data/vector_store'
    memory_store_path: str = 'rag_data/memory.jsonl'
    top_k: int = 5
    project_name: str = 'DevAgents_Project'

@dataclass
class MemoryRecord:
    memory_id: str
    timestamp: str
    project_id: str
    memory_type: str
    content: str
    requirement_ids: List[str] = field(default_factory=list)
    agent_name: Optional[str] = None
    phase: Optional[str] = None
    iteration: Optional[int] = None
    source: Optional[str] = None
    importance: int = 1
