import os
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
        if not model_name or model_name in ["mock-model", "default", "llama-3.1-8b-instant", "meta-llama/llama-3.1-70b-instruct", "openai/gpt-oss-120b"]:
            model_name = os.environ.get("GROQ_MODEL", "qwen/qwen3.8-27b")
        return GroqProvider(model=model_name)
    elif provider_name in ["openrouter", "or"]:
        from .providers.openrouter_provider import OpenRouterProvider
        if not model_name or model_name in ["mock-model", "default"]:
            model_name = os.environ.get("OPENROUTER_MODEL", "nvidia/nemotron-3.5-lightning:free")
        return OpenRouterProvider(model=model_name)
    elif provider_name in ["gemini", "google"]:
        from .providers.gemini_provider import GeminiProvider
        if not model_name or model_name in ["mock-model", "default", "gemini-2.5-flash"]:
            model_name = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
        return GeminiProvider(model=model_name)
    elif provider_name in ["huggingface", "hf"]:
        from .providers.huggingface_provider import HuggingFaceProvider
        if not model_name or model_name in ["mock-model", "default"]:
            model_name = os.environ.get("HF_MODEL", "meta-llama/Llama-3.2-3B-Instruct")
        return HuggingFaceProvider(model=model_name)
    else:
        raise LLMConfigurationError(f"Unsupported LLM provider: {provider_name}")
