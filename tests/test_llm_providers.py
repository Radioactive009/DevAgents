import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Mock modules before importing providers
sys.modules['groq'] = MagicMock()

google_mock = MagicMock()
genai_mock = MagicMock()
types_mock = MagicMock()
errors_mock = MagicMock()

google_mock.genai = genai_mock
genai_mock.types = types_mock
genai_mock.errors = errors_mock

sys.modules['google'] = google_mock
sys.modules['google.genai'] = genai_mock
sys.modules['google.genai.types'] = types_mock
sys.modules['google.genai.errors'] = errors_mock
sys.modules['huggingface_hub'] = MagicMock()

from llm.factory import create_llm_provider
from llm.base import MockLLMProvider
from llm.models import LLMResponse
from llm.errors import LLMConfigurationError, LLMAuthenticationError
from llm.providers.groq_provider import GroqProvider
from llm.providers.gemini_provider import GeminiProvider
from llm.providers.huggingface_provider import HuggingFaceProvider

class TestLLMProviders(unittest.TestCase):
    
    def test_factory_mock(self):
        config = {"provider": "mock", "model": "mock-model"}
        provider = create_llm_provider(config)
        self.assertIsInstance(provider, MockLLMProvider)
        
    def test_factory_invalid(self):
        config = {"provider": "unknown", "model": "mock-model"}
        with self.assertRaises(LLMConfigurationError):
            create_llm_provider(config)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test_key"}, clear=True)
    def test_groq_provider_parsing(self):
        with patch.object(sys.modules['groq'], 'Groq') as mock_groq_class:
            mock_client = MagicMock()
            mock_groq_class.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Groq response"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.completion_tokens = 20
            mock_response.usage.total_tokens = 30
            
            mock_client.chat.completions.create.return_value = mock_response
            
            provider = GroqProvider(model="llama3-8b-8192")
            # Set groq exceptions explicitly since it's used directly
            provider.groq_exceptions = MagicMock()
            
            resp = provider.generate("Hello")
            
            self.assertIsInstance(resp, LLMResponse)
            self.assertEqual(resp.text, "Groq response")
            self.assertEqual(resp.provider, "groq")
            self.assertEqual(resp.input_tokens, 10)
            self.assertEqual(resp.output_tokens, 20)
            self.assertEqual(resp.total_tokens, 30)

    @patch.dict(os.environ, {}, clear=True)
    def test_groq_missing_api_key(self):
        with self.assertRaises(LLMAuthenticationError):
            GroqProvider(model="llama3-8b-8192")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}, clear=True)
    def test_gemini_provider_parsing(self):
        mock_client = MagicMock()
        genai_mock.Client.return_value = mock_client
        
        class MockGeminiResponse:
            def __init__(self):
                self.text = "Gemini response"
                self.usage_metadata = MagicMock()
                self.usage_metadata.prompt_token_count = 15
                self.usage_metadata.candidates_token_count = 25
                self.usage_metadata.total_token_count = 40
        
        mock_response = MockGeminiResponse()
        mock_client.models.generate_content.return_value = mock_response
        
        provider = GeminiProvider(model="gemini-1.5-pro")
        resp = provider.generate("Hello")
        
        self.assertIsInstance(resp, LLMResponse)
        self.assertEqual(resp.text, "Gemini response")
        self.assertEqual(resp.provider, "gemini")
        self.assertEqual(resp.input_tokens, 15)
        self.assertEqual(resp.output_tokens, 25)
        self.assertEqual(resp.total_tokens, 40)

    @patch.dict(os.environ, {"HF_API_KEY": "test_key"}, clear=True)
    def test_huggingface_provider_parsing(self):
        with patch.object(sys.modules['huggingface_hub'], 'InferenceClient') as mock_hf_client_class:
            mock_client = MagicMock()
            mock_hf_client_class.return_value = mock_client
            
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "HF response"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.usage.prompt_tokens = 5
            mock_response.usage.completion_tokens = 15
            mock_response.usage.total_tokens = 20
            
            mock_client.chat_completion.return_value = mock_response
            
            provider = HuggingFaceProvider(model="meta-llama/Meta-Llama-3-8B-Instruct")
            resp = provider.generate("Hello")
            
            self.assertIsInstance(resp, LLMResponse)
            self.assertEqual(resp.text, "HF response")
            self.assertEqual(resp.provider, "huggingface")
            self.assertEqual(resp.input_tokens, 5)
            self.assertEqual(resp.output_tokens, 15)
            self.assertEqual(resp.total_tokens, 20)

if __name__ == '__main__':
    unittest.main()
