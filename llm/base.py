from abc import ABC, abstractmethod
from typing import Optional, Any
from .models import LLMResponse

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Provides a uniform interface independent of the underlying API (Groq, Gemini, HF, etc.).
    """
    
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The main user prompt.
            system_prompt: Optional system instructions.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the generated response.
            **kwargs: Additional provider-specific arguments.

        Returns:
            An LLMResponse containing the generated text and metadata.
        """
        pass

class MockLLMProvider(LLMProvider):
    """
    A mock provider for local testing without making real API calls.
    """
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any
    ) -> LLMResponse:
        return LLMResponse(
            text="This is a mock LLM response.",
            provider="mock",
            model="mock-model",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            latency_seconds=0.1,
            finish_reason="stop"
        )
