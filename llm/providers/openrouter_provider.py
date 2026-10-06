import os
import time
import json
import urllib.request
from typing import Optional, Any, Dict
from ..base import LLMProvider
from ..models import LLMResponse
from ..errors import (
    LLMAuthenticationError, 
    LLMAPIError, 
    LLMRateLimitError, 
    LLMTimeoutError,
    LLMConfigurationError
)

class OpenRouterProvider(LLMProvider):
    def __init__(self, model: str):
        self.model = model
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise LLMAuthenticationError("OPENROUTER_API_KEY environment variable is not set")
            
        # Cost safety verification
        self._verify_free_model()
        
    def _verify_free_model(self):
        """Validates that the selected model is free to use on OpenRouter."""
        # A simple heuristic: if it has ':free' suffix, it's typically free.
        # But we must verify pricing via API.
        try:
            req = urllib.request.Request("https://openrouter.ai/api/v1/models")
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                models = data.get('data', [])
                
                for m in models:
                    if m.get('id') == self.model:
                        pricing = m.get('pricing', {})
                        prompt_cost = float(pricing.get('prompt', -1))
                        completion_cost = float(pricing.get('completion', -1))
                        
                        if prompt_cost == 0 and completion_cost == 0:
                            return # Verified free!
                        else:
                            raise LLMConfigurationError(f"Model '{self.model}' is NOT free. Paid models are disabled for this project.")
                            
                raise LLMConfigurationError(f"Model '{self.model}' was not found in the OpenRouter model list.")
        except urllib.error.URLError as e:
            # If network error prevents validation, we can fail loudly for safety
            raise LLMConfigurationError(f"Failed to fetch OpenRouter pricing to verify model is free: {str(e)}")
        except Exception as e:
            if isinstance(e, LLMConfigurationError):
                raise
            raise LLMConfigurationError(f"Unexpected error validating model pricing: {str(e)}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any
    ) -> LLMResponse:
        start_time = time.time()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/Radioactive009/DevAgents",
                "X-Title": "DevAgents"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                status_code = response.getcode()
                response_body = response.read().decode('utf-8')
                data = json.loads(response_body)
                
                text = data['choices'][0]['message']['content']
                
                usage = data.get('usage', {})
                input_tokens = usage.get('prompt_tokens')
                output_tokens = usage.get('completion_tokens')
                total_tokens = usage.get('total_tokens')
                
                latency = time.time() - start_time
                
                return LLMResponse(
                    text=text,
                    provider="openrouter",
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    latency_seconds=latency,
                    raw_metadata=data
                )
                
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8')
            if e.code == 401 or e.code == 403:
                raise LLMAuthenticationError(f"OpenRouter Auth Error ({e.code})")
            elif e.code == 429:
                raise LLMRateLimitError(f"OpenRouter Rate Limited ({e.code})")
            elif e.code == 400 or e.code == 404:
                raise LLMAPIError(f"OpenRouter Request Error ({e.code})")
            else:
                raise LLMAPIError(f"OpenRouter Error ({e.code})")
        except urllib.error.URLError as e:
            if "timeout" in str(e.reason).lower():
                raise LLMTimeoutError("OpenRouter Timeout")
            raise LLMAPIError(f"OpenRouter Network Error: {str(e.reason)}")
        except Exception as e:
            raise LLMAPIError(str(e))
