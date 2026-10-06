from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

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
    ) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The main user prompt.
            system_prompt: Optional system instructions.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the generated response.
            **kwargs: Additional provider-specific arguments.

        Returns:
            The generated text string.
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
    ) -> str:
        return "This is a mock LLM response."
