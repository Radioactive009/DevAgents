from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid

def generate_event_id() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

@dataclass
class BaseEvent:
    event_type: str
    run_id: str
    event_id: str = field(default_factory=generate_event_id)
    timestamp: str = field(default_factory=get_utc_now)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class AgentEvent(BaseEvent):
    event_type: str = "agent"
    agent_name: str = ""
    phase: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_ms: float = 0.0
    success: bool = False
    status: str = ""
    input_summary: str = ""
    output_summary: str = ""
    provider: Optional[str] = None
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    error_info: Optional[str] = None

@dataclass
class LLMEvent(BaseEvent):
    event_type: str = "llm"
    provider: str = ""
    model: str = ""
    latency_ms: float = 0.0
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    success: bool = True
    error_type: Optional[str] = None

@dataclass
class ToolEvent(BaseEvent):
    event_type: str = "tool"
    request_id: str = ""
    agent_name: str = ""
    tool_name: str = ""
    duration_ms: float = 0.0
    success: bool = True
    error_type: Optional[str] = None
    metadata_summary: str = ""

@dataclass
class RetrievalEvent(BaseEvent):
    event_type: str = "retrieval"
    retrieval_type: str = "rag" # 'rag' or 'memory'
    query: str = ""
    top_k: int = 0
    duration_ms: float = 0.0
    result_count: int = 0
    retrieved_ids: List[str] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    enabled: bool = True

@dataclass
class TestEvent(BaseEvent):
    event_type: str = "test"
    test_command: str = ""
    duration_ms: float = 0.0
    exit_code: Optional[int] = None
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    test_pass_rate: float = 0.0
    coverage: Optional[float] = None
    timeout: bool = False
    success: bool = False

@dataclass
class DebugEvent(BaseEvent):
    event_type: str = "debug"
    iteration: int = 0
    failure_category: str = ""
    affected_files: List[str] = field(default_factory=list)
    success: bool = False
    duration_ms: float = 0.0
    patch_status: str = ""
    test_result_after_fix: Optional[str] = None
    agent_name: str = ""
    provider: Optional[str] = None
    model: Optional[str] = None
    total_tokens: Optional[int] = None

@dataclass
class VerificationEvent(BaseEvent):
    event_type: str = "verification"
    duration_ms: float = 0.0
    status: str = ""
    verified_requirement_count: int = 0
    partially_verified_count: int = 0
    unverified_count: int = 0
    requirement_coverage: float = 0.0
    test_pass_rate: float = 0.0
    warning_count: int = 0
    provider: Optional[str] = None
    model: Optional[str] = None
    total_tokens: Optional[int] = None

@dataclass
class ErrorEvent(BaseEvent):
    event_type: str = "error"
    component: str = ""
    phase: str = ""
    error_type: str = ""
    message: str = ""
    recoverable: bool = False
    agent_name: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None

@dataclass
class RunRecord:
    run_id: str
    task_id: str
    timestamp_start: str
    timestamp_end: Optional[str] = None
    duration_s: float = 0.0
    configuration: Dict[str, Any] = field(default_factory=dict)
    provider: str = ""
    model: str = ""
    success: bool = False
    final_status: str = ""
    total_llm_calls: int = 0
    total_tokens: int = 0
    total_tool_calls: int = 0
    total_rag_queries: int = 0
    total_memory_queries: int = 0
    debugging_iterations: int = 0
    test_pass_rate: float = 0.0
    requirement_coverage: float = 0.0
    verification_status: str = ""
    error_count: int = 0
    human_intervention: Dict[str, Any] = field(default_factory=lambda: {"occurred": False, "count": 0, "events": []})
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
