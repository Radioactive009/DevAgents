import pytest
from llm.base import MockLLMProvider
from orchestration.workflow import run_phase7_workflow

def test_workflow_rag_and_memory_disabled():
    mock_provider = MockLLMProvider()
    state = run_phase7_workflow(
        run_id="test_run",
        user_requirement="Create a hello world app",
        supervisor_provider=mock_provider,
        architecture_provider=mock_provider,
        coding_provider=mock_provider,
        testing_provider=mock_provider,
        debugging_provider=mock_provider,
        use_rag=False,
        use_memory=False
    )
    assert state is not None

from unittest.mock import patch

def test_workflow_rag_and_memory_enabled():
    mock_provider = MockLLMProvider()
    with patch("rag.pipeline.Embedder") as mock_embedder_cls:
        # Mock the instance returned by Embedder()
        mock_embedder_instance = mock_embedder_cls.return_value
        mock_embedder_instance.model_name = "mock"
        mock_embedder_instance.embed_texts.side_effect = lambda texts: __import__('numpy').random.rand(len(texts), 384).astype('float32')
        mock_embedder_instance.embed_query.side_effect = lambda query: __import__('numpy').random.rand(384).astype('float32')

        state = run_phase7_workflow(
            run_id="test_run_mem",
            user_requirement="Create a hello world app with rag",
        supervisor_provider=mock_provider,
        architecture_provider=mock_provider,
        coding_provider=mock_provider,
        testing_provider=mock_provider,
        debugging_provider=mock_provider,
        use_rag=True,
        use_memory=True
    )
    assert state is not None
