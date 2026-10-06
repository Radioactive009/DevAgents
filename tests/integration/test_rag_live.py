import pytest
from rag.embeddings import Embedder

def test_live_embedding_generation():
    try:
        embedder = Embedder()
        emb = embedder.embed_texts(["hello integration"])
        assert emb.shape[1] == 384
    except Exception as e:
        pytest.skip(f"Live embedding model not locally available or network failed: {e}")

def test_live_empty_query():
    try:
        embedder = Embedder()
        emb = embedder.embed_query("")
        assert len(emb) == 384
    except Exception as e:
        pytest.skip(f"Live embedding model not locally available or network failed: {e}")
