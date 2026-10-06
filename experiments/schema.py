from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class ExperimentConfigSystem:
    name: str

@dataclass
class LLMConfig:
    provider: str
    model: str
    temperature: float = 0.2
    max_tokens: int = 4096

@dataclass
class ExecutionConfig:
    docker_image: str
    cpu_limit: float
    memory_limit: str
    timeout_seconds: int
    network_policy: str
    max_debug_iterations: int

@dataclass
class ReproducibilityConfig:
    random_seed: int
    git_commit: str
    prompt_version: str

@dataclass
class ExperimentProtocol:
    name: str
    version: str
    research_question: str
    benchmark_name: str
    benchmark_version: str
    task_manifest: str
    task_count: int
    systems: List[str]
    llm: LLMConfig
    execution: ExecutionConfig
    reproducibility: ReproducibilityConfig

    @classmethod
    def from_dict(cls, data: dict) -> 'ExperimentProtocol':
        return cls(
            name=data["experiment"]["name"],
            version=data["experiment"]["version"],
            research_question=data["experiment"]["research_question"],
            benchmark_name=data["benchmark"]["name"],
            benchmark_version=data["benchmark"]["version"],
            task_manifest=data["benchmark"]["task_manifest"],
            task_count=data["benchmark"]["task_count"],
            systems=data["systems"],
            llm=LLMConfig(**data["llm"]),
            execution=ExecutionConfig(**data["execution"]),
            reproducibility=ReproducibilityConfig(**data["reproducibility"])
        )

@dataclass
class TaskManifestEntry:
    task_id: str
    benchmark: str
    benchmark_version: str
    repository: str
    issue_id: str
    task_description: str
    expected_evaluation: str
    difficulty: str
    inclusion_status: str

@dataclass
class ExperimentRunResult:
    run_id: str
    experiment_id: str
    task_id: str
    benchmark: str
    benchmark_version: str
    configuration: str
    provider: str
    model: str
    prompt_version: str
    protocol_version: str
    git_commit: str
    timestamp: str

    # Outcome
    success: bool
    final_test_pass: bool
    test_pass_rate: float
    requirement_coverage: float
    code_coverage: float
    bug_fix_success: bool
    verification_status: str

    # Debugging
    debug_iterations: int
    max_debug_iterations: int
    failure_category: Optional[str]

    # Resource/use metrics
    llm_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    tool_calls: int
    test_calls: int
    execution_time_seconds: float
    llm_latency_seconds: float
    test_execution_seconds: float
    human_intervention: bool

    # RAG
    rag_enabled: bool
    rag_calls: int
    rag_latency_seconds: float

    # Memory
    memory_enabled: bool
    memory_calls: int
    memory_latency_seconds: float

    # Errors
    error_type: Optional[str]
    error_message_sanitized: Optional[str]
