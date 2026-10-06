import pytest
from orchestration.state import ProjectState
from agents.single_agent_baseline import SingleAgentBaseline
from agents.schema import GeneratedProject, GeneratedFile, DebugPatch
from llm.base import LLMProvider
from llm.models import LLMResponse
import json

class LocalMockProvider(LLMProvider):
    def __init__(self):
        self.responses = []
    def add_response(self, text):
        self.responses.append(text)
    def generate(self, prompt, **kwargs):
        text = self.responses.pop(0) if self.responses else "Mock response"
        return LLMResponse(text=text, provider="mock", model="mock", input_tokens=0, output_tokens=0, total_tokens=0, latency_seconds=0, finish_reason="stop")

def test_single_agent_generate_success():
    provider = LocalMockProvider()
    
    valid_project = {
        "project_name": "TestProj",
        "entrypoint": "main.py",
        "run_command": "python main.py",
        "test_command": "pytest",
        "dependencies": [],
        "files": [
            {
                "path": "main.py",
                "content": "print('Hello')",
                "description": "Main file",
                "requirement_ids": []
            }
        ],
        "requirement_coverage": {}
    }
    
    provider.add_response(json.dumps(valid_project))
    
    agent = SingleAgentBaseline(provider=provider)
    state = ProjectState(run_id="test", user_requirement="Build a script")
    
    result = agent.run(state)
    assert result.success is True
    assert len(state.generated_project.files) == 1

def test_single_agent_generate_unsafe_path():
    provider = LocalMockProvider()
    
    invalid_project = {
        "project_name": "TestProj",
        "entrypoint": "main.py",
        "run_command": "python main.py",
        "test_command": "pytest",
        "dependencies": [],
        "files": [
            {
                "path": "../main.py",
                "content": "print('Hello')",
                "description": "Main file",
                "requirement_ids": []
            }
        ],
        "requirement_coverage": {}
    }
    
    provider.add_response(json.dumps(invalid_project))
    
    agent = SingleAgentBaseline(provider=provider, max_retries=1)
    state = ProjectState(run_id="test", user_requirement="Build a script")
    
    result = agent.run(state)
    assert result.success is False
    assert result.error_category == "PATH_SECURITY_ERROR"

def test_single_agent_debug_success():
        provider = LocalMockProvider()
    
        valid_patch = {
            "root_cause": "Bug",
            "failure_category": "Logic",
            "explanation": "Fix bug",
            "changes": [
                {
                    "path": "main.py",
                    "action": "modify",
                    "new_content": "print('Fixed')",
                    "reason": "Fix",
                    "requirement_ids": []
                }
            ]
        }
    
        provider.add_response(json.dumps(valid_patch))
    
        agent = SingleAgentBaseline(provider=provider)
        state = ProjectState(run_id="test", user_requirement="Build a script")
        state.generated_project = GeneratedProject(
            project_name="Test",
            entrypoint="main.py",
            run_command="python main.py",
            test_command="pytest",
            dependencies=[],
            files=[GeneratedFile(path="main.py", content="print('Bug')", description="bug", requirement_ids=[])],
            requirement_coverage={}
        )
    
        # Mock test failure
        from orchestration.state import TestResult
        state.test_result = TestResult(
            success=False,
            status="FAILED",
            tests_passed=0,
            tests_total=1,
            stdout="",
            stderr="failed",
            command="pytest",
            exit_code=1,
            duration=1.0,
            timed_out=False
        )
    
        result = agent.run(state)
        assert result.success is True
        assert state.generated_project.files[0].content == "print('Fixed')"

def test_single_agent_debug_pass_skip():
    provider = LocalMockProvider()
    agent = SingleAgentBaseline(provider=provider)
    state = ProjectState(run_id="test", user_requirement="Build a script")
    
    state.generated_project = GeneratedProject(
        project_name="Test",
        entrypoint="main.py",
        run_command="python main.py",
        test_command="pytest",
        dependencies=[],
        files=[],
        requirement_coverage={}
    )
    
    # Mock test pass
    from orchestration.state import TestResult
    state.test_result = TestResult(
        success=True, status="PASSED", tests_passed=1, tests_total=1,
        stdout="", stderr="", command="pytest", exit_code=0,
        duration=1.0, timed_out=False
    )
    
    result = agent.run(state)
    assert result.success is True
    assert "skipped" in result.error_message
