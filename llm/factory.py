from typing import Dict, Any
from .base import LLMProvider, MockLLMProvider
from .errors import LLMConfigurationError

def create_llm_provider(config: Dict[str, Any]) -> LLMProvider:
    provider_name = config.get("provider", config.get("llm_provider", "")).lower()
    model_name = config.get("model", config.get("llm_model", "mock-model"))
    
    if provider_name == "mock":
        return MockLLMProvider()
    elif provider_name == "groq":
        from .providers.groq_provider import GroqProvider
        return GroqProvider(model=model_name)
    elif provider_name == "openrouter":
        from .providers.openrouter_provider import OpenRouterProvider
        return OpenRouterProvider(model=model_name)
    else:
        raise LLMConfigurationError(f"Unsupported LLM provider: {provider_name}")
