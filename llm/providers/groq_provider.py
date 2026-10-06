import os
import time
from typing import Optional, Any
from ..base import LLMProvider
from ..models import LLMResponse
from ..errors import LLMAuthenticationError, LLMAPIError, LLMRateLimitError, LLMMalformedResponseError

class GroqProvider(LLMProvider):
    def __init__(self, model: str):
        self.model = model
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise LLMAuthenticationError("GROQ_API_KEY environment variable is not set")
        try:
            from groq import Groq
            import groq
        except ImportError:
            raise LLMAPIError("groq package is not installed")
        self.client = Groq(api_key=api_key)
        self.groq_exceptions = groq

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
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        except self.groq_exceptions.AuthenticationError as e:
            raise LLMAuthenticationError(str(e))
        except self.groq_exceptions.RateLimitError as e:
            raise LLMRateLimitError(str(e))
        except self.groq_exceptions.APIConnectionError as e:
            raise LLMAPIError(f"Connection error: {e}")
        except self.groq_exceptions.APIStatusError as e:
            raise LLMAPIError(f"API status error: {e}")
        except Exception as e:
            raise LLMAPIError(str(e))
            
        latency = time.time() - start_time

        if not response.choices:
            raise LLMMalformedResponseError("No choices in response")
            
        choice = response.choices[0]
        text = choice.message.content
        finish_reason = choice.finish_reason

        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None
        total_tokens = usage.total_tokens if usage else None

        return LLMResponse(
            text=text,
            provider="groq",
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            latency_seconds=latency,
            finish_reason=finish_reason,
            raw_metadata=response.model_dump() if hasattr(response, "model_dump") else None
        )
