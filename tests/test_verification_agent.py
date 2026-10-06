import unittest
from llm.base import MockLLMProvider
from orchestration.state import ProjectState
from agents.verification import VerificationAgent
from llm.base import LLMProvider, LLMResponse
from agents.schema import GeneratedProject, TestResult, ProjectPlan, Requirement

class MockVerificationProvider(LLMProvider):
    def __init__(self):
        self.response_queue = []
    def generate(self, prompt, **kwargs):
        text = self.response_queue.pop(0) if self.response_queue else "{}"
        return LLMResponse(text=text, provider="mock", model="mock", total_tokens=10)


class TestVerificationAgent(unittest.TestCase):
    def test_missing_project(self):
        state = ProjectState(run_id="test", user_requirement="test")
        agent = VerificationAgent(provider=MockVerificationProvider())
        agent.provider.response_queue.append('{"status": "VERIFIED"}') # Should be overridden by deterministic checks
        
        result = agent.run(state)
        
        self.assertTrue(result.success)
        self.assertEqual(state.verification_result.status, "PARTIALLY_VERIFIED")
        self.assertIn("Project does not exist.", state.verification_result.failed_checks)

    def test_malformed_llm_response(self):
        state = ProjectState(run_id="test", user_requirement="test")
        state.generated_project = GeneratedProject(project_name="t", files=[], entrypoint="", run_command="", test_command="", dependencies=[], requirement_coverage={})
        state.test_result = TestResult(success=True, status="PASSED", command="", exit_code=0, stdout="", stderr="", duration=0, timed_out=False)
        agent = VerificationAgent(provider=MockVerificationProvider())
        agent.provider.response_queue.append('invalid json')
        
        result = agent.run(state)
        self.assertFalse(result.success)
        self.assertEqual(state.verification_result.status, "NOT_VERIFIED")
        
    def test_verified_success(self):
        state = ProjectState(run_id="test", user_requirement="test")
        state.generated_project = GeneratedProject(project_name="t", files=[], entrypoint="", run_command="", test_command="", dependencies=[], requirement_coverage={})
        state.test_result = TestResult(success=True, status="PASSED", command="", exit_code=0, stdout="", stderr="", duration=0, timed_out=False)
        state.project_plan = ProjectPlan(project_summary="", requirements=[Requirement("R1", "desc", "high")], non_functional_requirements=[], tasks=[], testing_requirements=[], assumptions=[])
        
        agent = VerificationAgent(provider=MockVerificationProvider())
        agent.provider.response_queue.append('{"status": "VERIFIED", "criteria": [{"status": "VERIFIED"}]}')
        
        result = agent.run(state)
        self.assertTrue(result.success)
        self.assertEqual(state.verification_result.status, "VERIFIED")
        self.assertEqual(state.verification_result.requirement_coverage, 1.0)
        
if __name__ == '__main__':
    unittest.main()
