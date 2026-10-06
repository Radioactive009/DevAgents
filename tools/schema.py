from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class ToolRequest:
    request_id: str
    tool_name: str
    arguments: Dict[str, Any]
    agent_name: str

@dataclass
class ToolResult:
    request_id: str
    tool_name: str
    success: bool
    output: Any
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
