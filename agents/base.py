from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING
import json

from llm.base import LLMProvider
from agents.models import AgentResult

if TYPE_CHECKING:
    from orchestration.state import ProjectState

class Agent(ABC):
    def __init__(self, name: str, role: str, provider: LLMProvider):
        self.name = name
        self.role = role
        self.provider = provider

    @abstractmethod
    def run(self, state: 'ProjectState') -> AgentResult:

        pass

    def _create_result(self, success: bool, run_id: str, output: Any, raw_response_available: bool,
                       provider_name: Optional[str] = None, model_name: Optional[str] = None,
                       latency: Optional[float] = None, token_usage: Optional[int] = None,
                       generated_file_count: Optional[int] = None, requirement_coverage: Optional[float] = None,
                       error_category: Optional[str] = None, error_message: Optional[str] = None) -> AgentResult:
        return AgentResult(
            success=success,
            agent_name=self.name,
            run_id=run_id,
            output=output,
            raw_response_available=raw_response_available,
            provider=provider_name,
            model=model_name,
            latency=latency,
            token_usage=token_usage,
            generated_file_count=generated_file_count,
            requirement_coverage=requirement_coverage,
            error_category=error_category,
            error_message=error_message
        )
