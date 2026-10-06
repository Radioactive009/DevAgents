import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

from llm.providers.groq_provider import GroqProvider
from llm.providers.gemini_provider import GeminiProvider
from llm.providers.huggingface_provider import HuggingFaceProvider
from llm.errors import (
    LLMAuthenticationError, 
    LLMRateLimitError, 
    LLMTimeoutError, 
    LLMAPIError, 
    LLMMalformedResponseError,
    LLMConfigurationError
)

def classify_error(e: Exception) -> str:
    if isinstance(e, LLMAuthenticationError):
        return "AUTHENTICATION_ERROR"
    elif isinstance(e, LLMRateLimitError):
        return "RATE_LIMITED"
    elif isinstance(e, LLMTimeoutError):
        return "TIMEOUT"
    elif isinstance(e, LLMMalformedResponseError):
        return "PROVIDER_ERROR"
    elif isinstance(e, LLMAPIError):
        # We try to guess based on message if we want to be more specific, 
        # but to be safe and avoid leaking keys, we return PROVIDER_ERROR or AUTHORIZATION_ERROR
        return "PROVIDER_ERROR"
    else:
        return "UNKNOWN_ERROR"

def test_groq():
    if not os.environ.get("GROQ_API_KEY"):
        print("GROQ: FAIL - MISSING_API_KEY")
        return
        
    try:
        # Use smallest model available for Groq
        provider = GroqProvider(model="llama3-8b-8192")
        provider.generate("hi", max_tokens=2)
        print("GROQ: PASS")
    except Exception as e:
        print(f"GROQ: FAIL - {classify_error(e)}")

def test_gemini():
    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI: FAIL - MISSING_API_KEY")
        return
        
    try:
        # Use gemini-1.5-flash as it's the fastest
        provider = GeminiProvider(model="gemini-1.5-flash")
        provider.generate("hi", max_tokens=2)
        print("GEMINI: PASS")
    except Exception as e:
        print(f"GEMINI: FAIL - {classify_error(e)}")

def test_huggingface():
    if not os.environ.get("HF_API_KEY"):
        print("HUGGING_FACE: FAIL - MISSING_API_KEY")
        return
        
    try:
        provider = HuggingFaceProvider(model="meta-llama/Meta-Llama-3-8B-Instruct")
        provider.generate("hi", max_tokens=2)
        print("HUGGING_FACE: PASS")
    except Exception as e:
        print(f"HUGGING_FACE: FAIL - {classify_error(e)}")

if __name__ == "__main__":
    test_groq()
    test_gemini()
    test_huggingface()
