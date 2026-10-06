from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ToolContext:
    project_root: str
    task_id: str
    agent_name: str
    allowed_tools: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    
    def has_permission(self, tool_name: str) -> bool:
        return tool_name in self.allowed_tools
