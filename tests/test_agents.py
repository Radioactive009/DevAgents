import unittest
import json
from unittest.mock import patch

from agents.schema import ProjectPlan, ArchitectureSpecification, parse_json_response
from agents.supervisor import SupervisorAgent
from agents.architecture import ArchitectureAgent
from orchestration.state import ProjectState
from llm.base import LLMProvider
from llm.models import LLMResponse
from orchestration.workflow import run_phase4_workflow

MOCK_PROJECT_PLAN = {
    "project_summary": "Task API",
    "requirements": [{"id": "REQ-1", "description": "Create task", "priority": "high"}],
    "non_functional_requirements": [],
    "tasks": [
        {
            "id": "T-1",
            "description": "DB Schema",
            "dependencies": [],
            "expected_output": "sql",
            "requirement_ids": ["REQ-1"]
        }
    ],
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
    "components": [
        {"name": "TaskRouter", "responsibility": "Routing", "dependencies": []}
    ],
    "apis": ["POST /tasks"],
    "data_models": ["Task"],
    "directory_structure": ["src/"],
    "dependencies": ["fastapi"],
    "configuration": ["env variables"],
    "security_considerations": ["JWT"],
    "testing_strategy": ["pytest"],
    "architecture_decisions": [
        {
            "decision": "Use PostgreSQL",
            "reason": "Relational",
            "requirement_ids": ["REQ-1"]
        }
    ]
}

class MockAgentLLMProvider(LLMProvider):
    def __init__(self, fail_count=0):
        self.fail_count = fail_count
        self.attempts = 0
        
    def generate(self, prompt, system_prompt=None, temperature=0.7, max_tokens=1000, **kwargs):
        self.attempts += 1
        
        if self.attempts <= self.fail_count:
            text = "Invalid JSON { {"
        elif "Project Plan" in prompt:
            text = json.dumps(MOCK_ARCHITECTURE)
        elif "Project Manager" in (system_prompt or ""):
            text = json.dumps(MOCK_PROJECT_PLAN)
        else:
            # Fallback
            text = json.dumps(MOCK_PROJECT_PLAN)

        return LLMResponse(
            text=text,
            provider="mock",
            model="mock-model"
        )

class TestAgents(unittest.TestCase):
    
    def test_parse_json_response(self):
        text = "```json\n{\"test\": 123}\n```"
        self.assertEqual(parse_json_response(text), {"test": 123})
        
        text2 = "{\"test\": 123}"
        self.assertEqual(parse_json_response(text2), {"test": 123})

    def test_supervisor_agent(self):
        provider = MockAgentLLMProvider()
        agent = SupervisorAgent(provider)
        state = ProjectState(run_id="run-1", user_requirement="Build a task API")
        
        result = agent.run(state)
        
        self.assertTrue(result.success)
        self.assertIsInstance(result.output, ProjectPlan)
        self.assertEqual(result.output.project_summary, "Task API")
        self.assertEqual(len(result.output.tasks[0].requirement_ids), 1)
        
    def test_architecture_agent(self):
        provider = MockAgentLLMProvider()
        agent = ArchitectureAgent(provider)
        state = ProjectState(run_id="run-1", user_requirement="Build a task API")
        
        # Missing project plan should fail
        result = agent.run(state)
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "VALIDATION_ERROR")
        
        # With project plan
        state.project_plan = ProjectPlan.from_dict(MOCK_PROJECT_PLAN)
        result = agent.run(state)
        
        self.assertTrue(result.success)
        self.assertIsInstance(result.output, ArchitectureSpecification)
        self.assertEqual(result.output.technology_stack.database, "PostgreSQL")
        self.assertEqual(len(result.output.architecture_decisions[0].requirement_ids), 1)

    def test_retry_on_invalid_json(self):
        # Fail 1 time, then succeed
        provider = MockAgentLLMProvider(fail_count=1)
        agent = SupervisorAgent(provider)
        state = ProjectState(run_id="run-2", user_requirement="req")
        
        result = agent.run(state)
        self.assertTrue(result.success)
        self.assertEqual(provider.attempts, 2)
        
        # Fail 2 times -> exhausted
        provider2 = MockAgentLLMProvider(fail_count=2)
        agent2 = SupervisorAgent(provider2)
        result2 = agent2.run(state)
        self.assertFalse(result2.success)
        self.assertEqual(result2.error_category, "STRUCTURED_OUTPUT_ERROR")
        self.assertEqual(provider2.attempts, 2)
        
    def test_orchestration_workflow(self):
        provider = MockAgentLLMProvider()
        state = run_phase4_workflow("run-3", "Build a task API", provider, provider)
        
        self.assertIsNotNone(state.project_plan)
        self.assertIsNotNone(state.architecture)
        self.assertEqual(state.project_plan.project_summary, "Task API")
        self.assertEqual(state.architecture.technology_stack.language, "Python")

if __name__ == '__main__':
    unittest.main()
