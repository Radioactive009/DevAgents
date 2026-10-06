import unittest
import os
import shutil

from orchestration.workflow import run_phase7_workflow
from orchestration.state import ProjectState
from agents.schema import GeneratedProject, GeneratedFile, TestResult
from llm.base import LLMProvider, LLMResponse
from ml.classifier import FailureClassifier
from ml.schemas import FailureSample

class MockTestingProvider(LLMProvider):
    def generate(self, prompt, **kwargs):
        return LLMResponse(text="", provider="mock", model="mock")

class MockDebugProvider(LLMProvider):
    def generate(self, prompt, **kwargs):
        # Fail the debug to stop loop quickly, or fix it
        patch = {
            "changes": [],
            "root_cause": "Test ML",
            "failure_category": "UNKNOWN_ERROR",
            "explanation": "Test ML"
        }
        import json
        return LLMResponse(text=json.dumps(patch), provider="mock", model="mock")

class TestMLWorkflow(unittest.TestCase):
    def setUp(self):
        # Create a tiny trained model for integration testing
        self.test_dir = "tests/test_ml_workflow_artifacts"
        os.makedirs(self.test_dir, exist_ok=True)
        self.model_path = os.path.join(self.test_dir, "model.joblib")
        
        classifier = FailureClassifier()
        samples = [
            FailureSample("1", "AssertionError", "ASSERTION_FAILURE", "test", "p1", "1"),
            FailureSample("2", "SyntaxError", "SYNTAX_ERROR", "test", "p1", "2")
        ]
        classifier.train(samples)
        classifier.save(self.model_path)
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_ml_classifier_integration(self):
        # We mock run_phase6_workflow to return a state with a failed test result
        from unittest.mock import patch
        
        state = ProjectState(run_id="test", user_requirement="req")
        state.test_result = TestResult(
            success=False, status="FAILED", command="pytest", exit_code=1,
            stdout="AssertionError: assert False", stderr="", duration=1.0, timed_out=False
        )
        
        with patch("orchestration.workflow.run_phase6_workflow") as mock_phase6:
            mock_phase6.return_value = state
            
            # We mock the TestingAgent so it just returns PASSED after the first debug loop
            with patch("agents.testing.TestingAgent.run") as mock_test_run:
                mock_test_run.return_value = TestResult(
                    success=True, status="PASSED", command="pytest", exit_code=0,
                    stdout="", stderr="", duration=1.0, timed_out=False
                )
                
                final_state = run_phase7_workflow(
                    run_id="test",
                    user_requirement="req",
                    supervisor_provider=MockTestingProvider(),
                    architecture_provider=MockTestingProvider(),
                    coding_provider=MockTestingProvider(),
                    testing_provider=MockTestingProvider(),
                    debugging_provider=MockDebugProvider(),
                    use_failure_classifier=True,
                    classifier_model_path=self.model_path
                )
                
                # Check if failure classification was attached to state
                self.assertIsNotNone(final_state.failure_classification)
                self.assertEqual(final_state.failure_classification["predicted_category"], "ASSERTION_FAILURE")

if __name__ == '__main__':
    unittest.main()
