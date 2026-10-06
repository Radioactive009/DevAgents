import unittest
import os
from dotenv import load_dotenv

# Load .env file explicitly for integration tests
load_dotenv(override=True)

from llm.providers.groq_provider import GroqProvider
from llm.providers.gemini_provider import GeminiProvider
from llm.providers.huggingface_provider import HuggingFaceProvider
from llm.models import LLMResponse

@unittest.skipUnless(os.environ.get("RUN_LLM_INTEGRATION_TESTS") == "true", "Requires RUN_LLM_INTEGRATION_TESTS=true")
class TestLLMProvidersIntegration(unittest.TestCase):
    
    def test_groq_live(self):
        # Using a fast, well-known model on Groq
        provider = GroqProvider(model="qwen/qwen3.8-27b")
        response = provider.generate("Say hello in one word.")
        
        self.assertIsInstance(response, LLMResponse)
        self.assertTrue(len(response.text) > 0)
        self.assertEqual(response.provider, "groq")
        self.assertIsNotNone(response.input_tokens)
        self.assertIsNotNone(response.output_tokens)
        self.assertIsNotNone(response.total_tokens)
        self.assertIsNotNone(response.latency_seconds)
        self.assertTrue(response.latency_seconds > 0)
        
    def test_gemini_live(self):
        # Using the default configured model on Gemini
        provider = GeminiProvider(model=None)
        response = provider.generate("Reply with exactly: OK")
        
        self.assertIsInstance(response, LLMResponse)
        self.assertTrue(len(response.text) > 0)
        self.assertEqual(response.provider, "gemini")
        # Gemini does provide usage_metadata
        self.assertIsNotNone(response.input_tokens)
        self.assertIsNotNone(response.output_tokens)
        self.assertIsNotNone(response.total_tokens)
        self.assertIsNotNone(response.latency_seconds)
        self.assertTrue(response.latency_seconds > 0)
        
    def test_huggingface_live(self):
        # Using a fast, well-known model on HuggingFace
        provider = HuggingFaceProvider(model="meta-llama/Meta-Llama-3-8B-Instruct")
        response = provider.generate("Say hello in one word.")
        
        self.assertIsInstance(response, LLMResponse)
        self.assertTrue(len(response.text) > 0)
        self.assertEqual(response.provider, "huggingface")
        # HF may or may not provide token counts depending on backend, but we check latency and text
        self.assertIsNotNone(response.latency_seconds)
        self.assertTrue(response.latency_seconds > 0)

if __name__ == "__main__":
    unittest.main()
