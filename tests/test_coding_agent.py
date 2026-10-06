import unittest
import json
from unittest.mock import patch

from agents.schema import GeneratedProject, ProjectPlan, ArchitectureSpecification
from agents.coding import CodingAgent
from orchestration.state import ProjectState
from orchestration.workflow import run_phase5_workflow
from llm.base import LLMProvider
from llm.models import LLMResponse

MOCK_PROJECT_PLAN = {
    "project_summary": "Task API",
    "requirements": [{"id": "REQ-1", "description": "Create task", "priority": "high"}],
    "non_functional_requirements": [],
    "tasks": [],
    "testing_requirements": [],
    "assumptions": []
}

MOCK_ARCHITECTURE = {
    "project_type": "API",
    "technology_stack": {
        "language": "Python",
        "framework": "FastAPI",
        "database": "PostgreSQL",
        "other": []
    },
    "components": [],
    "apis": [],
    "data_models": [],
    "directory_structure": [],
    "dependencies": [],
    "configuration": [],
    "security_considerations": [],
    "testing_strategy": [],
    "architecture_decisions": []
}

MOCK_GENERATED_PROJECT = {
    "project_name": "task-api",
    "files": [
        {
            "path": "app/main.py",
            "content": "print('hello')",
            "description": "Main entrypoint",
            "requirement_ids": ["REQ-1"]
        }
    ],
    "entrypoint": "app/main.py",
    "run_command": "python app/main.py",
    "test_command": "pytest",
    "dependencies": ["fastapi"],
    "requirement_coverage": {
        "REQ-1": ["app/main.py"]
    }
}

class MockCodingLLMProvider(LLMProvider):
    def __init__(self, mode="valid"):
        self.mode = mode
        self.attempts = 0

    def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=1000, **kwargs):
        self.attempts += 1
        
        if self.mode == "valid":
            text = json.dumps(MOCK_GENERATED_PROJECT)
        elif self.mode == "invalid_json":
            if self.attempts == 1:
                text = "invalid json {"
            else:
                text = json.dumps(MOCK_GENERATED_PROJECT)
        elif self.mode == "invalid_json_always":
            text = "invalid json {"
        elif self.mode == "invalid_path":
            proj = dict(MOCK_GENERATED_PROJECT)
            proj["files"] = [{"path": "/etc/passwd", "content": "hello", "requirement_ids": []}]
            if self.attempts == 1:
                text = json.dumps(proj)
            else:
                text = json.dumps(MOCK_GENERATED_PROJECT)
        elif self.mode == "invalid_syntax":
            proj = dict(MOCK_GENERATED_PROJECT)
            proj["files"] = [{"path": "app/main.py", "content": "if True print('hello')", "requirement_ids": []}]
            if self.attempts == 1:
                text = json.dumps(proj)
            else:
                text = json.dumps(MOCK_GENERATED_PROJECT)
        else:
            text = json.dumps(MOCK_GENERATED_PROJECT)
            
        return LLMResponse(
            text=text,
            provider="mock",
            model="mock-model"
        )

class TestCodingAgent(unittest.TestCase):
    def setUp(self):
        self.state = ProjectState(run_id="test-run", user_requirement="req")
        self.state.project_plan = ProjectPlan.from_dict(MOCK_PROJECT_PLAN)
        self.state.architecture = ArchitectureSpecification.from_dict(MOCK_ARCHITECTURE)

    def test_coding_agent_valid(self):
        provider = MockCodingLLMProvider(mode="valid")
        agent = CodingAgent(provider)
        
        result = agent.run(self.state)
        
        self.assertTrue(result.success)
        self.assertIsInstance(result.output, GeneratedProject)
        self.assertEqual(result.generated_file_count, 1)
        self.assertEqual(result.requirement_coverage, 1.0)
        self.assertEqual(self.state.generated_project.project_name, "task-api")

    def test_coding_agent_missing_context(self):
        provider = MockCodingLLMProvider(mode="valid")
        agent = CodingAgent(provider)
        empty_state = ProjectState(run_id="test-run", user_requirement="req")
        
        result = agent.run(empty_state)
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "MISSING_CONTEXT")

    def test_coding_agent_invalid_path(self):
        provider = MockCodingLLMProvider(mode="invalid_path")
        agent = CodingAgent(provider)
        
        result = agent.run(self.state)
        
        self.assertTrue(result.success)
        self.assertEqual(provider.attempts, 2)
        
    def test_coding_agent_invalid_syntax(self):
        provider = MockCodingLLMProvider(mode="invalid_syntax")
        agent = CodingAgent(provider)
        
        result = agent.run(self.state)
        
        self.assertTrue(result.success)
        self.assertEqual(provider.attempts, 2)

    def test_coding_agent_invalid_json_retry(self):
        provider = MockCodingLLMProvider(mode="invalid_json")
        agent = CodingAgent(provider)
        
        result = agent.run(self.state)
        
        self.assertTrue(result.success)
        self.assertEqual(provider.attempts, 2)
        
    def test_coding_agent_invalid_json_exhausted(self):
        provider = MockCodingLLMProvider(mode="invalid_json_always")
        agent = CodingAgent(provider)
        
        result = agent.run(self.state)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "STRUCTURED_OUTPUT_ERROR")
        self.assertEqual(provider.attempts, 2)

if __name__ == '__main__':
    unittest.main()
