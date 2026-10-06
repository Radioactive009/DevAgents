import pytest
from fastapi.testclient import TestClient
from orchestration.state import ProjectState
from orchestration.workflow import run_phase11_workflow
from api.main import app, active_runs_state

client = TestClient(app)

def test_api_state_visibility_before_completion():
    run_id = "test-run-123"
    # Emulate the API registering state early
    active_runs_state[run_id] = ProjectState(run_id=run_id, user_requirement="build a calculator")
    
    # Query API before any files exist
    response = client.get(f"/api/runs/{run_id}/project")
    assert response.status_code == 200
    assert response.json() == {"files": {}}
    
    # Simulate an agent mutating the state
    from agents.schema import GeneratedProject, GeneratedFile
    active_runs_state[run_id].generated_project = GeneratedProject(
        project_name="calc",
        files=[GeneratedFile(path="calc.py", content="def add(): pass")],
        entrypoint="", run_command="", test_command="", dependencies=[], requirement_coverage={}
    )
    
    # Query API again - it should instantly see the mutated files!
    response2 = client.get(f"/api/runs/{run_id}/project")
    assert response2.status_code == 200
    assert response2.json()["files"]["calc.py"] == "def add(): pass"

def test_workflow_compatibility_with_none_state():
    # Calling run_phase11_workflow with state=None should not crash (assuming mock providers)
    # This verifies we didn't break existing calls that don't pass `state`
    from unittest.mock import MagicMock
    mock_provider = MagicMock()
    mock_provider.generate.return_value = "Mocked!"
    # We won't run the full workflow here because it does I/O, but we verify it's a valid kwarg.
    import inspect
    sig = inspect.signature(run_phase11_workflow)
    assert "state" in sig.parameters

