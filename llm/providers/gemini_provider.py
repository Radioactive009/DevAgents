import os
import time
from typing import Optional, Any
from ..base import LLMProvider
from ..models import LLMResponse
from ..errors import LLMAuthenticationError, LLMAPIError

class GeminiProvider(LLMProvider):
    def __init__(self, model: str):
        self.model = model
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise LLMAuthenticationError("GEMINI_API_KEY environment variable is not set")
        try:
            from google import genai
            from google.genai import types
            from google.genai.errors import APIError
        except ImportError:
            raise LLMAPIError("google-genai package is not installed")
        
        self.client = genai.Client(api_key=api_key)
        self.types = types
        self.APIError = APIError

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any
    ) -> LLMResponse:
        start_time = time.time()
        
        config = self.types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
            system_instruction=system_prompt,
            **kwargs
        )
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
        except Exception as e:
            # Simple error handling for now as we don't have specifics
            raise LLMAPIError(str(e))
            
        latency = time.time() - start_time
        
        text = response.text
        
        input_tokens = None
        output_tokens = None
        total_tokens = None
        
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, 'prompt_token_count', None)
            output_tokens = getattr(response.usage_metadata, 'candidates_token_count', None)
            total_tokens = getattr(response.usage_metadata, 'total_token_count', None)
            
        return LLMResponse(
            text=text or "",
            provider="gemini",
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_seconds=latency,
            finish_reason=None, # Not explicitly available in a consistent way yet
            raw_metadata=None
        )
