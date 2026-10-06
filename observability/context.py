from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class ObservabilityContext:
    run_id: str
    task_id: str
    configuration: Dict[str, Any] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
