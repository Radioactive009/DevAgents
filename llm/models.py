from dataclasses import dataclass
from typing import Optional, Any, Dict

@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_seconds: Optional[float] = None
    finish_reason: Optional[str] = None
    raw_metadata: Optional[Dict[str, Any]] = None
