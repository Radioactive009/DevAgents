from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class AgentResult:
    success: bool
    agent_name: str
    run_id: str
    output: Any
    raw_response_available: bool
    provider: Optional[str] = None
    model: Optional[str] = None
    latency: Optional[float] = None
    token_usage: Optional[int] = None
    generated_file_count: Optional[int] = None
    requirement_coverage: Optional[float] = None
    error_category: Optional[str] = None
    error_message: Optional[str] = None
