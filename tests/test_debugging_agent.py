import unittest
import json
from unittest.mock import patch, MagicMock

from agents.debugging import DebuggingAgent
from orchestration.state import ProjectState
from agents.schema import GeneratedProject, GeneratedFile, TestResult, ProjectPlan, Requirement
from llm.base import LLMProvider, LLMResponse

MOCK_DEBUG_PATCH = {
    "changes": [
        {
            "path": "main.py",
            "action": "modify",
            "new_content": "def add(a, b): return a + b",
            "reason": "Fix addition logic",
            "requirement_ids": ["REQ-1"]
        }
    ],
    "root_cause": "Logic error in add function",
    "failure_category": "LOGIC_ERROR",
    "explanation": "Added a and b instead of subtracting"
}

class MockDebuggingLLMProvider(LLMProvider):
    def __init__(self, mode="valid"):
        self.mode = mode
        self.attempts = 0

    def generate(self, prompt, **kwargs):
        self.attempts += 1
        
        import copy
        if self.mode == "valid":
            text = json.dumps(MOCK_DEBUG_PATCH)
        elif self.mode == "invalid_json":
            if self.attempts == 1:
                text = "invalid {"
            else:
                text = json.dumps(MOCK_DEBUG_PATCH)
        elif self.mode == "invalid_json_exhaust":
            text = "invalid {"
        elif self.mode == "unsafe_path":
            patch = copy.deepcopy(MOCK_DEBUG_PATCH)
            patch["changes"][0]["path"] = "../main.py"
            text = json.dumps(patch) if self.attempts == 1 else json.dumps(MOCK_DEBUG_PATCH)
        elif self.mode == "protected_file":
            patch = copy.deepcopy(MOCK_DEBUG_PATCH)
            patch["changes"][0]["path"] = ".env"
            text = json.dumps(patch) if self.attempts == 1 else json.dumps(MOCK_DEBUG_PATCH)
        elif self.mode == "invalid_syntax":
            patch = copy.deepcopy(MOCK_DEBUG_PATCH)
            patch["changes"][0]["new_content"] = "if True print('error')"
            text = json.dumps(patch) if self.attempts == 1 else json.dumps(MOCK_DEBUG_PATCH)
        elif self.mode == "unknown_req":
            patch = copy.deepcopy(MOCK_DEBUG_PATCH)
            patch["changes"][0]["requirement_ids"] = ["REQ-999"]
            text = json.dumps(patch) if self.attempts == 1 else json.dumps(MOCK_DEBUG_PATCH)
        else:
            text = json.dumps(MOCK_DEBUG_PATCH)

        return LLMResponse(text=text, provider="mock", model="mock")

class TestDebuggingAgent(unittest.TestCase):
    def setUp(self):
        self.state = ProjectState(run_id="run-debug", user_requirement="test")
        self.state.project_plan = ProjectPlan(
            project_summary="", requirements=[Requirement(id="REQ-1", description="", priority="")],
            non_functional_requirements=[], tasks=[], testing_requirements=[], assumptions=[]
        )
        self.state.generated_project = GeneratedProject(
            project_name="proj",
            files=[GeneratedFile(path="main.py", content="def add(a, b): return a - b", requirement_ids=["REQ-1"])],
            entrypoint="", run_command="", test_command="", dependencies=[], requirement_coverage={"REQ-1": ["main.py"]}
        )
        self.state.test_result = TestResult(
            success=False, status="FAILED", command="pytest", exit_code=1, stdout="Failed", stderr="", duration=1.0, timed_out=False
        )

    def test_successful_debug(self):
        provider = MockDebuggingLLMProvider("valid")
        agent = DebuggingAgent(provider)
        
        result = agent.run(self.state)
        
        self.assertTrue(result.success)
        self.assertEqual(len(self.state.debugging_history), 1)
        self.assertEqual(self.state.debugging_history[0]["failure_category"], "LOGIC_ERROR")
        self.assertEqual(self.state.generated_project.files[0].content, "def add(a, b): return a + b")

    def test_skip_passed_tests(self):
        self.state.test_result.status = "PASSED"
        provider = MockDebuggingLLMProvider("valid")
        agent = DebuggingAgent(provider)
        
        result = agent.run(self.state)
        self.assertTrue(result.success)
        self.assertEqual(result.error_message, "Tests passed, debugging skipped.")
        self.assertEqual(len(self.state.debugging_history), 0)

    def test_invalid_json_retry(self):
        provider = MockDebuggingLLMProvider("invalid_json")
        agent = DebuggingAgent(provider)
        result = agent.run(self.state)
        self.assertTrue(result.success)
        self.assertEqual(provider.attempts, 2)

    def test_invalid_json_exhaust(self):
        provider = MockDebuggingLLMProvider("invalid_json_exhaust")
        agent = DebuggingAgent(provider)
        result = agent.run(self.state)
        self.assertFalse(result.success)
        self.assertEqual(provider.attempts, 2)
        self.assertEqual(result.error_category, "STRUCTURED_OUTPUT_ERROR")

    def test_unsafe_path(self):
        provider = MockDebuggingLLMProvider("unsafe_path")
        agent = DebuggingAgent(provider)
        result = agent.run(self.state)
        self.assertTrue(result.success) # Retried and succeeded
        self.assertEqual(provider.attempts, 2)

    def test_protected_file(self):
        provider = MockDebuggingLLMProvider("protected_file")
        agent = DebuggingAgent(provider)
        result = agent.run(self.state)
        self.assertTrue(result.success)
        self.assertEqual(provider.attempts, 2)

    def test_invalid_syntax(self):
        provider = MockDebuggingLLMProvider("invalid_syntax")
        agent = DebuggingAgent(provider)
        result = agent.run(self.state)
        self.assertTrue(result.success)
        self.assertEqual(provider.attempts, 2)

    def test_unknown_requirement(self):
        provider = MockDebuggingLLMProvider("unknown_req")
        agent = DebuggingAgent(provider)
        result = agent.run(self.state)
        self.assertTrue(result.success)
        self.assertEqual(provider.attempts, 2)

if __name__ == '__main__':
    unittest.main()
