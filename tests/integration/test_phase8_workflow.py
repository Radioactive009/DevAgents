import pytest
from llm.providers.mock_provider import MockProvider
from orchestration.workflow import run_phase7_workflow

def test_workflow_rag_and_memory_disabled():
    mock_provider = MockProvider()
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

def test_workflow_rag_and_memory_enabled():
    mock_provider = MockProvider()
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
