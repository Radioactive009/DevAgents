from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class ExecutionResult:
    success: bool
    exit_code: Optional[int]
    stdout: str
    stderr: str
    command: str
    duration: float
    timed_out: bool = False
    sandbox_id: Optional[str] = None
    failure_category: Optional[str] = None
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
