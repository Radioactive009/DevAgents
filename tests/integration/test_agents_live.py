import unittest
import os

from llm.factory import LLMProviderFactory
from orchestration.workflow import run_phase4_workflow

@unittest.skipUnless(os.environ.get("RUN_LLM_INTEGRATION_TESTS", "").lower() == "true", "Live integration tests disabled")
class TestAgentsLive(unittest.TestCase):
    def test_live_agents_workflow(self):
        # We assume the config specifies models, but we can also manually instantiate the providers
        # Since this is an integration test, we'll try to use the groq or openrouter providers if keys are available
        
        # Test if Groq API key is available
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            self.skipTest("GROQ_API_KEY not found in environment")
            
        provider = LLMProviderFactory.create_provider(
            "groq", 
            api_key=api_key, 
            default_model="llama3-70b-8192"
        )
        
        user_requirement = (
            "Build a REST API for a task management application. "
            "Users should be able to create, update, delete and list tasks. "
            "The application should use PostgreSQL for persistent storage "
            "and JWT-based authentication."
        )
        
        state = run_phase4_workflow(
            run_id="live-test-1", 
            user_requirement=user_requirement,
            supervisor_provider=provider,
            architecture_provider=provider
        )
        
        # Verify supervisor output
        self.assertIsNotNone(state.project_plan)
        self.assertTrue(len(state.project_plan.requirements) > 0)
        self.assertTrue(len(state.project_plan.tasks) > 0)
        
        # Verify architecture output
        self.assertIsNotNone(state.architecture)
        self.assertTrue(len(state.architecture.components) > 0)
        
        # Verify some structure content based on prompt
        self.assertIn("PostgreSQL", str(state.architecture.technology_stack))
        
if __name__ == '__main__':
    unittest.main()
