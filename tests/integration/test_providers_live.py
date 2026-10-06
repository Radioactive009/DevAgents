import unittest
import os
from dotenv import load_dotenv

load_dotenv(override=True)

from llm.providers.groq_provider import GroqProvider
from llm.providers.openrouter_provider import OpenRouterProvider

@unittest.skipUnless(os.environ.get("RUN_LLM_INTEGRATION_TESTS") == "true", "Requires RUN_LLM_INTEGRATION_TESTS=true")
class TestLLMProvidersIntegration(unittest.TestCase):
    
    def test_groq_live(self):
        try:
            provider = GroqProvider(model="qwen/qwen3.8-27b")
            response = provider.generate("Reply with exactly: OK")
            if response and len(response.text) > 0:
                print("GROQ/qwen/qwen3.8-27b: PASS")
        except Exception as e:
            err_type = type(e).__name__
            print(f"GROQ/qwen/qwen3.8-27b: FAIL - {err_type}")

    def test_openrouter_live_1(self):
        try:
            provider = OpenRouterProvider(model="openrouter/free")
            response = provider.generate("Reply with exactly: OK", max_tokens=10)
            if response and len(response.text) > 0:
                print("OPENROUTER/openrouter/free: PASS")
        except Exception as e:
            import traceback
            traceback.print_exc()
            err_type = type(e).__name__
            print(f"OPENROUTER/openrouter/free: FAIL - {err_type}")
            
    def test_openrouter_live_2(self):
        try:
            provider = OpenRouterProvider(model="google/gemma-4-26b-a4b-it:free")
            response = provider.generate("Reply with exactly: OK", max_tokens=10)
            if response and len(response.text) > 0:
                print("OPENROUTER/google/gemma-4-26b-a4b-it:free: PASS")
        except Exception as e:
            err_type = type(e).__name__
            print(f"OPENROUTER/google/gemma-4-26b-a4b-it:free: FAIL - {err_type}")

if __name__ == "__main__":
    unittest.main()
