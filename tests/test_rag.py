import os
import pytest
import numpy as np
from rag.chunking import Chunker
from rag.embeddings import Embedder
from rag.loaders import DocumentLoader
from rag.schemas import MemoryRecord
from rag.memory import ProjectMemory
from rag.vector_store import VectorStore
from rag.schemas import RAGChunk

def test_chunking():
    chunker = Chunker(chunk_size=10, chunk_overlap=2)
    chunks = chunker.chunk_text("hello world this is a test", "test.py", "test_proj")
    assert len(chunks) > 1
    assert chunks[0].project == "test_proj"
    
def test_embedding_generation():
    embedder = Embedder()
    emb = embedder.embed_texts(["hello"])
    assert emb.shape[1] == 384
    
def test_empty_query():
    embedder = Embedder()
    emb = embedder.embed_query("")
    assert len(emb) == 384
    
def test_memory_add_and_retrieve(tmp_path):
    path = os.path.join(tmp_path, "mem.jsonl")
    mem = ProjectMemory(path)
    record = MemoryRecord(memory_id="1", timestamp="", project_id="p1", memory_type="TEST_RESULT", content="passed")
    mem.add_memory(record)
    
    mem2 = ProjectMemory(path)
    res = mem2.search_memory("passed")
    assert len(res) == 1
    assert res[0].memory_type == "TEST_RESULT"
    
def test_loader_exclusions():
    loader = DocumentLoader("BugsInPy")
    assert loader.discover_files() == []

def test_vector_store(tmp_path):
    store = VectorStore(os.path.join(tmp_path, "store"))
    chunk = RAGChunk(chunk_id="1", content="test", source="", file_path="", document_type="", project="")
    store.add_chunks([chunk], np.random.rand(1, 384))
    res = store.search(np.random.rand(384))
    assert len(res) == 1
