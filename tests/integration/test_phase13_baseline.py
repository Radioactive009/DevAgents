import pytest
import os
import json
from orchestration.workflow import run_single_agent_workflow
from orchestration.state import ProjectState
from llm.base import LLMProvider
from llm.models import LLMResponse
from observability.telemetry import Telemetry

class LocalMockProvider(LLMProvider):
    def __init__(self):
        self.responses = []
    def add_response(self, text):
        self.responses.append(text)
    def generate(self, prompt, **kwargs):
        text = self.responses.pop(0) if self.responses else "Mock response"
        return LLMResponse(text=text, provider="mock", model="mock", input_tokens=0, output_tokens=0, total_tokens=0, latency_seconds=0, finish_reason="stop")

def test_single_agent_workflow_integration():
    # Setup mock provider to generate a simple script and fix it on retry
    provider = LocalMockProvider()
    
    # 1. First iteration generates code
    project_response = {
        "project_name": "Calculator",
        "entrypoint": "calc.py",
        "run_command": "python calc.py",
        "test_command": "pytest test_calc.py",
        "dependencies": [],
        "files": [
            {
                "path": "calc.py",
                "content": "def add(a, b): return a + b\n\nif __name__ == '__main__':\n    print(add(2, 2))\n",
                "description": "calc",
                "requirement_ids": []
            },
            {
                "path": "test_calc.py",
                "content": "import calc\n\ndef test_add():\n    assert calc.add(2, 2) == 4\n",
                "description": "test",
                "requirement_ids": []
            }
        ],
        "requirement_coverage": {}
    }
    provider.add_response(json.dumps(project_response))
    
    sandbox_config = {"use_docker": True} # Wait, mock testing usually uses mock sandbox or we can use docker. 
    # The integration tests for workflow use docker if running on system with docker. We'll disable docker for pure test speed.
    sandbox_config = {"use_docker": False}
    
    # Actually TestingAgent respects use_docker = False and runs natively
    # But to make this unit test robust without side-effects, we can mock TestingAgent
    from unittest.mock import patch
    from orchestration.state import TestResult
    
    mock_test_result = TestResult(
        success=True,
        status="PASSED",
        command="pytest",
        exit_code=0,
        stdout="==== 1 passed in 0.12s ====",
        stderr="",
        duration=0.1,
        timed_out=False
    )
    
    with patch('agents.testing.TestingAgent.run') as mock_run:
        from agents.models import AgentResult
        def side_effect(state):
            state.test_result = mock_test_result
            return AgentResult(success=True, run_id=state.run_id, output=mock_test_result, raw_response_available=False)
        mock_run.side_effect = side_effect
        
        state = run_single_agent_workflow(
            run_id="test-baseline-run",
            user_requirement="Build a calculator",
            provider=provider,
            sandbox_config=sandbox_config,
            max_iterations=3
        )

    assert state.generated_project is not None
    assert state.test_result is not None

    assert state.test_result.status == "PASSED"

    # Verify telemetry has correct system configuration
    telemetry = Telemetry.get_instance()
    record = telemetry.runs.get("test-baseline-run")
    assert record is not None
    assert record.configuration["system"] == "SINGLE_AGENT_BASELINE"
    assert record.configuration["use_rag"] is False
    assert record.configuration["use_memory"] is False

    # Verify we did NOT invoke specialized agents
    log_path = f"logs/runs/test-baseline-run.jsonl"
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    event = json.loads(line)
                    if event.get("event_type") == "agent":
                        assert event["agent_name"] == "SingleAgentBaseline"
                        assert event["agent_name"] not in ["SupervisorAgent", "ArchitectureAgent", "CodingAgent", "DebuggingAgent"]
