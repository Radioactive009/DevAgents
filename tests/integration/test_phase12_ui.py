from fastapi.testclient import TestClient
from api.main import app, active_runs
import pytest
from llm.mock import MockLLMProvider

def test_phase12_integration_ui():
    client = TestClient(app)
    
    # Create a small task with RAG enabled, memory disabled
    response = client.post("/api/runs", json={
        "task_description": "Build a simple calculator",
        "requirements": ["Addition", "Subtraction"],
        "use_rag": True,
        "use_memory": False,
        "provider": "mock",
        "model": "test-model"
    })
    
    assert response.status_code == 200
    data = response.json()
    run_id = data["run_id"]
    
    # Observe status updates
    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    assert response.json()["status"] in ["RUNNING", "COMPLETED", "FAILED"]
    
    # Verify events
    response = client.get(f"/api/runs/{run_id}/events")
    assert response.status_code == 200
    assert "events" in response.json()
    
    # Verify metrics
    response = client.get(f"/api/runs/{run_id}/metrics")
    assert response.status_code in [200, 404]  # 404 if not finished yet
    
    # Verify project
    response = client.get(f"/api/runs/{run_id}/project")
    assert response.status_code == 200
