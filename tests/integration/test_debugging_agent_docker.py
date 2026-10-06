import unittest
import os
import json
from unittest.mock import patch, MagicMock

from agents.schema import GeneratedProject, GeneratedFile, TestResult, DebugPatch
from orchestration.state import ProjectState
from agents.debugging import DebuggingAgent
from agents.testing import TestingAgent
from orchestration.workflow import run_phase7_workflow
from execution.docker_sandbox import check_docker_available
from llm.base import LLMProvider, LLMResponse

class MockTestLLMProvider(LLMProvider):
    def generate(self, prompt, **kwargs):
        # We don't use this for testing agent
        return LLMResponse(text="", provider="mock", model="mock")

class MockDebugLLMProvider(LLMProvider):
    def __init__(self, mode="fix_on_first"):
        self.mode = mode
        self.attempts = 0
        
    def generate(self, prompt, **kwargs):
        self.attempts += 1
        
        if self.mode == "fix_on_first":
            patch = {
                "changes": [
                    {
                        "path": "main.py",
                        "action": "modify",
                        "new_content": "def add(a, b):\n    return a + b\n",
                        "reason": "Fix bug",
                        "requirement_ids": []
                    }
                ],
                "root_cause": "Typo",
                "failure_category": "LOGIC_ERROR",
                "explanation": "Fix bug"
            }
            return LLMResponse(text=json.dumps(patch), provider="mock", model="mock")
        elif self.mode == "fix_on_second":
            if self.attempts == 1:
                patch = {
                    "changes": [
                        {
                            "path": "main.py",
                            "action": "modify",
                            "new_content": "def add(a, b):\n    return a * b\n",
                            "reason": "Wrong fix",
                            "requirement_ids": []
                        }
                    ],
                    "root_cause": "Typo",
                    "failure_category": "LOGIC_ERROR",
                    "explanation": "Fix bug"
                }
            else:
                patch = {
                    "changes": [
                        {
                            "path": "main.py",
                            "action": "modify",
                            "new_content": "def add(a, b):\n    return a + b\n",
                            "reason": "Right fix",
                            "requirement_ids": []
                        }
                    ],
                    "root_cause": "Typo",
                    "failure_category": "LOGIC_ERROR",
                    "explanation": "Fix bug"
                }
            return LLMResponse(text=json.dumps(patch), provider="mock", model="mock")
        elif self.mode == "never_fix":
            patch = {
                "changes": [
                    {
                        "path": "main.py",
                        "action": "modify",
                        "new_content": "def add(a, b):\n    return a * b\n",
                        "reason": "Wrong fix",
                        "requirement_ids": []
                    }
                ],
                "root_cause": "Typo",
                "failure_category": "LOGIC_ERROR",
                "explanation": "Fix bug"
            }
            return LLMResponse(text=json.dumps(patch), provider="mock", model="mock")

@unittest.skipUnless(check_docker_available(), "Docker is not available")
class TestDebuggingAgentDocker(unittest.TestCase):
    def setUp(self):
        self.state = ProjectState(run_id="run-docker-debug", user_requirement="test")
        self.state.generated_project = GeneratedProject(
            project_name="calc_proj",
            files=[
                GeneratedFile(path="main.py", content="def add(a, b):\n    return a - b\n", requirement_ids=[]),
                GeneratedFile(path="test_main.py", content="from main import add\n\ndef test_add():\n    assert add(2, 3) == 5\n", requirement_ids=[])
            ],
            entrypoint="",
            run_command="",
            test_command="python -m pytest",
            dependencies=["pytest"],
            requirement_coverage={}
        )
        self.sandbox_config = {"timeout_seconds": 60, "allow_network_for_dependencies": True}

    def test_debug_retest_loop_fix_on_first(self):
        test_agent = TestingAgent(MockTestLLMProvider(), sandbox_config=self.sandbox_config)
        
        # Initial test (should fail)
        test_agent.run(self.state)
        self.assertEqual(self.state.test_result.status, "FAILED")
        
        debug_agent = DebuggingAgent(MockDebugLLMProvider("fix_on_first"))
        
        # Iteration 1 debug
        debug_result = debug_agent.run(self.state)
        self.assertTrue(debug_result.success)
        
        # Iteration 1 test
        test_agent.run(self.state)
        self.assertEqual(self.state.test_result.status, "PASSED")
        
        self.assertEqual(len(self.state.debugging_history), 1)

    def test_debug_retest_loop_fix_on_second(self):
        test_agent = TestingAgent(MockTestLLMProvider(), sandbox_config=self.sandbox_config)
        debug_agent = DebuggingAgent(MockDebugLLMProvider("fix_on_second"))
        
        # We manually simulate the workflow loop
        test_agent.run(self.state)
        
        # Loop 1
        debug_agent.run(self.state)
        test_agent.run(self.state)
        self.assertEqual(self.state.test_result.status, "FAILED")
        
        # Loop 2
        debug_agent.run(self.state)
        test_agent.run(self.state)
        self.assertEqual(self.state.test_result.status, "PASSED")
        
        self.assertEqual(len(self.state.debugging_history), 2)

    def test_workflow_orchestration_limit(self):
        # We'll use run_phase7_workflow but we need to mock phase6
        with patch("orchestration.workflow.run_phase6_workflow") as mock_phase6:
            # Setup initial state with a failed test
            test_agent = TestingAgent(MockTestLLMProvider(), sandbox_config=self.sandbox_config)
            test_agent.run(self.state)
            mock_phase6.return_value = self.state
            
            final_state = run_phase7_workflow(
                run_id="run-docker-debug",
                user_requirement="test",
                supervisor_provider=MockTestLLMProvider(),
                architecture_provider=MockTestLLMProvider(),
                coding_provider=MockTestLLMProvider(),
                testing_provider=MockTestLLMProvider(),
                debugging_provider=MockDebugLLMProvider("never_fix"),
                sandbox_config=self.sandbox_config,
                max_debug_iterations=2
            )
            
            self.assertEqual(final_state.test_result.status, "FAILED")
            self.assertEqual(len(final_state.debugging_history), 2)
            self.assertEqual(final_state.metadata.get("debugging_error"), "DEBUG_ITERATION_LIMIT")

if __name__ == '__main__':
    unittest.main()
