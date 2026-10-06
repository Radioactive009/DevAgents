import os
import time
from typing import Optional, Any
from ..base import LLMProvider
from ..models import LLMResponse
from ..errors import LLMAuthenticationError, LLMAPIError

class HuggingFaceProvider(LLMProvider):
    def __init__(self, model: str):
        self.model = model
        api_key = os.environ.get("HF_API_KEY")
        if not api_key:
            raise LLMAuthenticationError("HF_API_KEY environment variable is not set")
        try:
            from huggingface_hub import InferenceClient
        except ImportError:
            raise LLMAPIError("huggingface_hub package is not installed")
        self.client = InferenceClient(api_key=api_key)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any
    ) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        start_time = time.time()
        try:
            response = self.client.chat_completion(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        except Exception as e:
            raise LLMAPIError(str(e))
            
        latency = time.time() - start_time
        
        choice = response.choices[0]
        text = choice.message.content
        finish_reason = getattr(choice, 'finish_reason', None)

        input_tokens = None
        output_tokens = None
        total_tokens = None
        
        if hasattr(response, 'usage') and response.usage:
            input_tokens = getattr(response.usage, 'prompt_tokens', None)
            output_tokens = getattr(response.usage, 'completion_tokens', None)
            total_tokens = getattr(response.usage, 'total_tokens', None)
            
        return LLMResponse(
            text=text,
            provider="huggingface",
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_seconds=latency,
            finish_reason=finish_reason,
            raw_metadata=None
        )
