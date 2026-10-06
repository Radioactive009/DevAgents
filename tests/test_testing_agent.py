import unittest
import os
from unittest.mock import patch, MagicMock

from agents.testing import TestingAgent
from orchestration.state import ProjectState
from agents.schema import GeneratedProject, GeneratedFile, TestResult
from llm.base import LLMProvider, LLMResponse
from execution.models import ExecutionResult
from execution.exceptions import SandboxConfigurationError

class MockLLMProvider(LLMProvider):
    def generate(self, prompt, **kwargs):
        return LLMResponse(text="", provider="mock", model="mock")

class MockSandbox:
    def __init__(self, config=None):
        self.config = config or {}
        self.sandbox_id = "mock-123"
        self.workspace_dir = "/mock"
        self.network_enabled = False
        self.files = {}
        self.run_command_mock = MagicMock()
        self.run_tests_mock = MagicMock()
        self.cleanup_mock = MagicMock()

    def create_workspace(self):
        pass

    def write_file(self, filename, content):
        if ".." in filename or filename.startswith("/"):
            raise SandboxConfigurationError("Unsafe path")
        self.files[filename] = content

    def run_command(self, cmd):
        return self.run_command_mock(cmd)

    def run_tests(self, cmd):
        return self.run_tests_mock(cmd)

    def cleanup(self):
        self.cleanup_mock()

class TestTestingAgent(unittest.TestCase):
    def setUp(self):
        self.provider = MockLLMProvider()
        self.agent = TestingAgent(self.provider, sandbox_config={"allow_network_for_dependencies": True})
        self.state = ProjectState(run_id="run-1", user_requirement="test")
        
        self.valid_project = GeneratedProject(
            project_name="test_proj",
            files=[
                GeneratedFile(path="main.py", content="print('hello')", requirement_ids=["REQ-1"]),
                GeneratedFile(path="requirements.txt", content="pytest", requirement_ids=[])
            ],
            entrypoint="main.py",
            run_command="python main.py",
            test_command="pytest",
            dependencies=["pytest"],
            requirement_coverage={"REQ-1": ["main.py"]}
        )

    @patch("agents.testing.DockerSandbox")
    def test_successful_execution(self, mock_docker_sandbox):
        mock_sandbox = MockSandbox()
        
        mock_sandbox.run_command_mock.return_value = ExecutionResult(
            success=True, exit_code=0, stdout="", stderr="", command="pip", duration=1.0
        )
        mock_sandbox.run_tests_mock.return_value = ExecutionResult(
            success=True, exit_code=0, stdout="==== 1 passed in 0.1s ====", stderr="", command="pytest", duration=1.0, sandbox_id="mock-123"
        )
        mock_docker_sandbox.return_value = mock_sandbox
        
        self.state.generated_project = self.valid_project
        result = self.agent.run(self.state)
        
        self.assertTrue(result.success)
        self.assertIsInstance(result.output, TestResult)
        self.assertEqual(result.output.status, "PASSED")
        self.assertEqual(result.output.tests_passed, 1)
        self.assertEqual(result.output.tests_total, 1)
        
        # Check files were written
        self.assertIn("main.py", mock_sandbox.files)
        
        # Check dependencies were installed
        mock_sandbox.run_command_mock.assert_called_once()
        self.assertTrue(mock_sandbox.cleanup_mock.called)
        
    @patch("agents.testing.DockerSandbox")
    def test_missing_project(self, mock_docker_sandbox):
        result = self.agent.run(self.state)
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "MISSING_GENERATED_PROJECT")

    @patch("agents.testing.DockerSandbox")
    def test_missing_test_command(self, mock_docker_sandbox):
        proj = self.valid_project
        proj.test_command = ""
        self.state.generated_project = proj
        
        result = self.agent.run(self.state)
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "NO_TEST_COMMAND")

    @patch("agents.testing.DockerSandbox")
    def test_failing_execution(self, mock_docker_sandbox):
        mock_sandbox = MockSandbox()
        mock_sandbox.run_command_mock.return_value = ExecutionResult(
            success=True, exit_code=0, stdout="", stderr="", command="pip", duration=1.0
        )
        mock_sandbox.run_tests_mock.return_value = ExecutionResult(
            success=False, exit_code=1, stdout="==== 1 failed in 0.1s ====", stderr="", command="pytest", duration=1.0, failure_category="NONZERO_EXIT"
        )
        mock_docker_sandbox.return_value = mock_sandbox
        
        self.state.generated_project = self.valid_project
        result = self.agent.run(self.state)
        
        self.assertFalse(result.success) # It returns false because tests failed
        self.assertEqual(result.output.status, "FAILED")
        self.assertEqual(result.output.tests_failed, 1)
        
    @patch("agents.testing.DockerSandbox")
    def test_dependency_failure(self, mock_docker_sandbox):
        mock_sandbox = MockSandbox()
        mock_sandbox.run_command_mock.return_value = ExecutionResult(
            success=False, exit_code=1, stdout="pip error", stderr="", command="pip", duration=1.0
        )
        mock_docker_sandbox.return_value = mock_sandbox
        
        self.state.generated_project = self.valid_project
        result = self.agent.run(self.state)
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "DEPENDENCY_INSTALLATION_FAILED")
        self.assertEqual(result.output.status, "DEPENDENCY_INSTALLATION_FAILED")

    @patch("agents.testing.DockerSandbox")
    def test_timeout(self, mock_docker_sandbox):
        mock_sandbox = MockSandbox()
        mock_sandbox.run_command_mock.return_value = ExecutionResult(
            success=True, exit_code=0, stdout="", stderr="", command="pip", duration=1.0
        )
        mock_sandbox.run_tests_mock.return_value = ExecutionResult(
            success=False, exit_code=None, stdout="", stderr="", command="pytest", duration=1.0, timed_out=True, failure_category="TIMEOUT"
        )
        mock_docker_sandbox.return_value = mock_sandbox
        
        self.state.generated_project = self.valid_project
        result = self.agent.run(self.state)
        
        self.assertFalse(result.success)
        self.assertEqual(result.output.status, "TIMEOUT")
        self.assertTrue(result.output.timed_out)

    @patch("agents.testing.DockerSandbox")
    def test_unsafe_path(self, mock_docker_sandbox):
        mock_sandbox = MockSandbox()
        mock_docker_sandbox.return_value = mock_sandbox
        
        proj = self.valid_project
        proj.files.append(GeneratedFile(path="../unsafe.py", content="bad", requirement_ids=[]))
        self.state.generated_project = proj
        
        result = self.agent.run(self.state)
        self.assertFalse(result.success)
        self.assertEqual(result.error_category, "SANDBOX_ERROR")

    @patch.dict(os.environ, {"GROQ_API_KEY": "supersecretkey"})
    @patch("agents.testing.DockerSandbox")
    def test_secret_sanitization(self, mock_docker_sandbox):
        mock_sandbox = MockSandbox()
        mock_sandbox.run_command_mock.return_value = ExecutionResult(
            success=True, exit_code=0, stdout="", stderr="", command="pip", duration=1.0
        )
        mock_sandbox.run_tests_mock.return_value = ExecutionResult(
            success=True, exit_code=0, stdout="My key is supersecretkey", stderr="", command="pytest", duration=1.0
        )
        mock_docker_sandbox.return_value = mock_sandbox
        
        self.state.generated_project = self.valid_project
        result = self.agent.run(self.state)
        
        self.assertTrue(result.success)
        self.assertNotIn("supersecretkey", result.output.stdout)
        self.assertIn("***REDACTED***", result.output.stdout)

if __name__ == '__main__':
    unittest.main()
