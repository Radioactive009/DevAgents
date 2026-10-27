from fastapi.testclient import TestClient
from api.main import app, active_runs, active_runs_state
import pytest

client = TestClient(app)

def test_create_run():
    response = client.post("/api/runs", json={
        "task_description": "Build an API",
        "requirements": ["Req 1", "Req 2"],
        "use_rag": False,
        "use_memory": False,
        "provider": "mock",
        "model": "mock-model"
    })
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "RUNNING"
    assert active_runs[data["run_id"]] in ["RUNNING", "COMPLETED"]

def test_get_run():
    active_runs["test-run-1"] = "COMPLETED"
    response = client.get("/api/runs/test-run-1")
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"

def test_get_project_empty():
    response = client.get("/api/runs/non-existent/project")
    assert response.status_code == 200
    assert response.json() == {"files": {}}

def test_approval_checkpoint_flow():
    import threading
    from orchestration.state import ProjectState
    test_id = "test-approval-run"
    state = ProjectState(run_id=test_id, user_requirement="test")
    state.metadata["human_approval"] = True
    event = threading.Event()
    state.metadata["approval_event"] = event
    state.metadata["approval_status"] = "PENDING_APPROVAL"
    active_runs_state[test_id] = state

    # Test state retrieval
    res = client.get(f"/api/runs/{test_id}/state")
    assert res.status_code == 200
    assert res.json()["approval_status"] == "PENDING_APPROVAL"

    # Test approval submission
    app_res = client.post(f"/api/runs/{test_id}/approve", json={"decision": "APPROVE", "feedback": "Approved"})
    assert app_res.status_code == 200
    assert app_res.json()["decision"] == "APPROVED"
    assert event.is_set()

