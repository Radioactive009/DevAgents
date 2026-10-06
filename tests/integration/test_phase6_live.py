import unittest
import os
import time

from llm.factory import create_llm_provider
from orchestration.workflow import run_phase6_workflow

@unittest.skipUnless(os.environ.get("RUN_LLM_INTEGRATION_TESTS", "").lower() == "true", "Live integration tests disabled")
class TestPhase6Live(unittest.TestCase):
    def test_live_testing_agent_workflow(self):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            self.skipTest("GROQ_API_KEY not found in environment")
            
        provider = create_llm_provider_provider(
            "groq", 
            api_key=api_key, 
            default_model="llama3-70b-8192"
        )
        
        user_requirement = (
            "Create a Python calculator with add and subtract functions and pytest tests."
        )
        
        sandbox_config = {
            "allow_network_for_dependencies": True,
            "timeout_seconds": 30
        }
        
        state = run_phase6_workflow(
            run_id="live-test-phase6", 
            user_requirement=user_requirement,
            supervisor_provider=provider,
            architecture_provider=provider,
            coding_provider=provider,
            testing_provider=provider,
            sandbox_config=sandbox_config
        )
        
        # Verify testing output
        self.assertIsNotNone(state.test_result)
        result = state.test_result
        
        # Print for observation
        print(f"Status: {result.status}")
        print(f"Passed: {result.tests_passed}, Failed: {result.tests_failed}")
        
        # It's possible the LLM generated failing tests, so we don't assert PASSED,
        # but we assert that execution completed and provided output
        self.assertIsNotNone(result.stdout)
        self.assertIsNotNone(result.duration)
        self.assertNotIn("GROQ_API_KEY", result.stdout)

if __name__ == '__main__':
    unittest.main()
