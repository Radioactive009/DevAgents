import unittest
import os
import ast

from llm.factory import create_llm_provider
from orchestration.workflow import run_phase5_workflow

@unittest.skipUnless(os.environ.get("RUN_LLM_INTEGRATION_TESTS", "").lower() == "true", "Live integration tests disabled")
class TestCodingAgentLive(unittest.TestCase):
    def test_live_coding_agent_workflow(self):
        # We assume the config specifies models, but we can also manually instantiate the providers
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            self.skipTest("GROQ_API_KEY not found in environment")
            
        provider = create_llm_provider_provider(
            "groq", 
            api_key=api_key, 
            default_model="llama3-70b-8192"
        )
        
        user_requirement = (
            "Create a Python CLI calculator with addition, subtraction, "
            "multiplication and division."
        )
        
        state = run_phase5_workflow(
            run_id="live-test-coding-1", 
            user_requirement=user_requirement,
            supervisor_provider=provider,
            architecture_provider=provider,
            coding_provider=provider
        )
        
        # Verify supervisor output
        self.assertIsNotNone(state.project_plan)
        
        # Verify architecture output
        self.assertIsNotNone(state.architecture)
        
        # Verify coding output
        self.assertIsNotNone(state.generated_project)
        project = state.generated_project
        self.assertTrue(len(project.files) > 0)
        self.assertTrue(hasattr(project, "project_name"))
        
        # Check files syntax
        for f in project.files:
            if f.path.endswith(".py"):
                try:
                    ast.parse(f.content)
                except SyntaxError as e:
                    self.fail(f"Generated python file {f.path} has syntax error: {e}")
                    
        # Check no absolute paths
        for f in project.files:
            self.assertFalse(f.path.startswith("/"))
            self.assertFalse(f.path.startswith("C:"))
            self.assertNotIn("..", f.path)

if __name__ == '__main__':
    unittest.main()
