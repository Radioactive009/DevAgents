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
        
        response_text = "{}"
        
        combined = (system_prompt or "") + " " + prompt
        
        if "Project Plan:" in prompt and "Architecture Specification:" not in prompt:
            # ArchitectureAgent
            response_text = '{\n  "components": [\n    {\n      "name": "calculator.py",\n      "type": "module",\n      "description": "Main logic",\n      "dependencies": [],\n      "requirement_ids": ["REQ-01", "REQ-02"]\n    },\n    {\n      "name": "test_calculator.py",\n      "type": "test",\n      "description": "Tests",\n      "dependencies": ["pytest"],\n      "requirement_ids": ["REQ-01", "REQ-02"]\n    }\n  ]\n}'
        elif "Architecture Specification:" in prompt or "Generate the complete project implementation" in prompt:
            # CodingAgent or SingleAgentBaseline
            response_text = '{\n  "project_name": "Calculator",\n  "entrypoint": "calculator.py",\n  "run_command": "python calculator.py",\n  "test_command": "python test_calculator.py",\n  "dependencies": [],\n  "files": [\n    {\n      "path": "calculator.py",\n      "content": "def add(a, b):\\n    return a + b\\n\\ndef subtract(a, b):\\n    return a - b\\n\\ndef multiply(a, b):\\n    return a * b\\n\\ndef divide(a, b):\\n    if b == 0:\\n        raise ValueError(\\"Division by zero\\")\\n    return (a / b) + 1",\n      "description": "calc",\n      "requirement_ids": ["REQ-01", "REQ-02"]\n    },\n    {\n      "path": "test_calculator.py",\n      "content": "import sys\\nfrom calculator import add, subtract, multiply, divide\\n\\ntry:\\n    assert add(2, 3) == 5\\n    assert divide(6, 2) == 3\\n    print(\\"Tests passed!\\")\\nexcept AssertionError:\\n    print(\\"Test failed!\\")\\n    sys.exit(1)",\n      "description": "test",\n      "requirement_ids": ["REQ-01", "REQ-02"]\n    }\n  ],\n  "requirement_coverage": {"REQ-01": ["calculator.py", "test_calculator.py"], "REQ-02": ["calculator.py", "test_calculator.py"]}\n}'
        elif "DebugPatch" in combined:
            # DebuggingAgent
            response_text = '{\n  "root_cause": "bug",\n  "failure_category": "LOGIC_ERROR",\n  "explanation": "fix",\n  "changes": []\n}'
        elif "Verification" in combined or "VERIFIED" in combined:
            # VerificationAgent
            response_text = '{\n  "status": "VERIFIED",\n  "issues": [],\n  "requirement_coverage": 1.0,\n  "summary": "All tests passed and requirements met."\n}'
        elif "supervisor" in combined.lower() or "projectplan" in combined.lower() or "requirements" in combined.lower() or "calculator" in combined.lower():
            # SupervisorAgent (default if matching supervisor/planning context)
            response_text = '{\n  "project_name": "Calculator",\n  "requirements": [\n    {\n      "id": "REQ-01",\n      "description": "Implement calculator with add, subtract, multiply, divide"\n    },\n    {\n      "id": "REQ-02",\n      "description": "Handle division by zero"\n    }\n  ],\n  "summary": "Calculator project planned."\n}'
        else:
            response_text = "This is a mock LLM response."
            
        return LLMResponse(
            text=response_text,
            provider="mock",
            model="mock-model",
            input_tokens=10,
            output_tokens=20,
            total_tokens=30,
            latency_seconds=0.1,
            finish_reason="stop"
        )
