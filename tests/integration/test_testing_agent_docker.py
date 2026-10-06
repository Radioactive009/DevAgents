import unittest
import os
import time

from agents.schema import GeneratedProject, GeneratedFile
from orchestration.state import ProjectState
from agents.testing import TestingAgent
from execution.docker_sandbox import check_docker_available

class MockLLMProvider:
    pass

@unittest.skipUnless(check_docker_available(), "Docker is not available")
class TestTestingAgentDocker(unittest.TestCase):
    def setUp(self):
        self.agent = TestingAgent(MockLLMProvider(), sandbox_config={"timeout_seconds": 60, "allow_network_for_dependencies": True})
        self.state = ProjectState(run_id="docker-run", user_requirement="test")
        
    def test_passing_project(self):
        self.state.generated_project = GeneratedProject(
            project_name="pass_test",
            files=[
                GeneratedFile(path="main.py", content="def add(a, b): return a + b"),
                GeneratedFile(path="test_main.py", content="from main import add\n\ndef test_add():\n    assert add(1, 1) == 2")
            ],
            entrypoint="main.py",
            run_command="python main.py",
            test_command="python -m pytest",
            dependencies=["pytest"],
            requirement_coverage={}
        )
        
        result = self.agent.run(self.state)
        self.assertTrue(result.success)
        self.assertEqual(result.output.status, "PASSED")
        self.assertEqual(result.output.tests_passed, 1)

    def test_failing_project(self):
        self.state.generated_project = GeneratedProject(
            project_name="fail_test",
            files=[
                GeneratedFile(path="test_main.py", content="def test_fail():\n    assert 1 + 1 == 3")
            ],
            entrypoint="",
            run_command="",
            test_command="python -m pytest",
            dependencies=["pytest"],
            requirement_coverage={}
        )
        
        result = self.agent.run(self.state)
        self.assertFalse(result.success)
        self.assertEqual(result.output.status, "FAILED")
        self.assertEqual(result.output.tests_failed, 1)

    def test_runtime_error(self):
        self.state.generated_project = GeneratedProject(
            project_name="error_test",
            files=[
                GeneratedFile(path="test_main.py", content="def test_err():\n    raise ValueError('boom')")
            ],
            entrypoint="",
            run_command="",
            test_command="python -m pytest",
            dependencies=["pytest"],
            requirement_coverage={}
        )
        
        result = self.agent.run(self.state)
        self.assertFalse(result.success)
        self.assertEqual(result.output.status, "FAILED")
        self.assertEqual(result.output.tests_failed, 1)
        self.assertIn("ValueError", result.output.stdout)

    def test_timeout(self):
        self.agent = TestingAgent(MockLLMProvider(), sandbox_config={"timeout_seconds": 2})
        self.state.generated_project = GeneratedProject(
            project_name="timeout_test",
            files=[
                GeneratedFile(path="test_main.py", content="import time\ndef test_timeout():\n    time.sleep(10)\ntest_timeout()")
            ],
            entrypoint="",
            run_command="",
            test_command="python test_main.py",
            dependencies=[],
            requirement_coverage={}
        )
        
        result = self.agent.run(self.state)
        self.assertFalse(result.success)
        self.assertEqual(result.output.status, "TIMEOUT")
        self.assertTrue(result.output.timed_out)

    def test_dependency_failure(self):
        self.state.generated_project = GeneratedProject(
            project_name="dep_fail_test",
            files=[],
            entrypoint="",
            run_command="",
            test_command="python -m pytest",
            dependencies=["thispackagedoesnotexist-12345"],
            requirement_coverage={}
        )
        
        result = self.agent.run(self.state)
        self.assertFalse(result.success)
        self.assertEqual(result.output.status, "DEPENDENCY_INSTALLATION_FAILED")
        self.assertIn("thispackagedoesnotexist", result.output.stderr + result.output.stdout)

    def test_filesystem_isolation(self):
        self.state.generated_project = GeneratedProject(
            project_name="fs_test",
            files=[
                GeneratedFile(path="test_main.py", content="import os\ndef test_fs():\n    assert os.path.exists('/.dockerenv')")
            ],
            entrypoint="",
            run_command="",
            test_command="python -m pytest",
            dependencies=["pytest"],
            requirement_coverage={}
        )
        
        result = self.agent.run(self.state)
        self.assertTrue(result.success)

if __name__ == '__main__':
    unittest.main()
