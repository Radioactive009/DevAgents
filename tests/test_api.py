from fastapi.testclient import TestClient
from api.main import app, active_runs, active_runs_state
import pytest

client = TestClient(app)

def test_create_run():
    response = client.post("/api/runs", json={
        "task_description": "Build an API",
        "requirements": ["Req 1", "Req 2"],
        "use_rag": False,
        "use_memory": False
    })
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert data["status"] == "RUNNING"
    assert active_runs[data["run_id"]] == "RUNNING"

def test_get_run():
    active_runs["test-run-1"] = "COMPLETED"
    response = client.get("/api/runs/test-run-1")
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"

def test_get_project_empty():
    response = client.get("/api/runs/non-existent/project")
    assert response.status_code == 200
    assert response.json() == {"files": {}}
