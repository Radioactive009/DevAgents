from typing import Dict, Any, Optional, List
from observability.logger import TelemetryLogger
from observability.schema import (
    AgentEvent, LLMEvent, ToolEvent, RetrievalEvent, TestEvent, DebugEvent, VerificationEvent, ErrorEvent, RunRecord
)
from observability.context import ObservabilityContext
from datetime import datetime, timezone

class Telemetry:
    _instance = None
    
    def __init__(self, log_dir: str = "logs/runs"):
        self.logger = TelemetryLogger(log_dir=log_dir)
        self.runs: Dict[str, RunRecord] = {}

    @classmethod
    def get_instance(cls, log_dir: str = "logs/runs") -> "Telemetry":
        if cls._instance is None:
            cls._instance = cls(log_dir)
        return cls._instance

    def start_run(self, run_id: str, task_id: str, configuration: Dict[str, Any], provider: str = "", model: str = "") -> None:
        try:
            record = RunRecord(
                run_id=run_id,
                task_id=task_id,
                timestamp_start=datetime.now(timezone.utc).isoformat(),
                configuration=configuration,
                provider=provider,
                model=model
            )
            self.runs[run_id] = record
        except Exception:
            pass

    def record_agent(self, event: AgentEvent) -> None:
        try:
            self.logger.write_event(event.to_dict())
        except Exception:
            pass

    def record_llm(self, event: LLMEvent) -> None:
        try:
            if event.run_id in self.runs:
                self.runs[event.run_id].total_llm_calls += 1
                if event.total_tokens:
                    self.runs[event.run_id].total_tokens += event.total_tokens
            self.logger.write_event(event.to_dict())
        except Exception:
            pass

    def record_tool(self, event: ToolEvent) -> None:
        try:
            if event.run_id in self.runs:
                self.runs[event.run_id].total_tool_calls += 1
            self.logger.write_event(event.to_dict())
        except Exception:
            pass

    def record_retrieval(self, event: RetrievalEvent) -> None:
        try:
            if event.run_id in self.runs and event.enabled:
                if event.retrieval_type == "rag":
                    self.runs[event.run_id].total_rag_queries += 1
                elif event.retrieval_type == "memory":
                    self.runs[event.run_id].total_memory_queries += 1
            self.logger.write_event(event.to_dict())
        except Exception:
            pass

    def record_test(self, event: TestEvent) -> None:
        try:
            if event.run_id in self.runs:
                self.runs[event.run_id].test_pass_rate = event.test_pass_rate
            self.logger.write_event(event.to_dict())
        except Exception:
            pass

    def record_debug(self, event: DebugEvent) -> None:
        try:
            if event.run_id in self.runs:
                self.runs[event.run_id].debugging_iterations = max(self.runs[event.run_id].debugging_iterations, event.iteration)
            self.logger.write_event(event.to_dict())
        except Exception:
            pass

    def record_verification(self, event: VerificationEvent) -> None:
        try:
            if event.run_id in self.runs:
                self.runs[event.run_id].verification_status = event.status
                self.runs[event.run_id].requirement_coverage = event.requirement_coverage
            self.logger.write_event(event.to_dict())
        except Exception:
            pass

    def record_error(self, event: ErrorEvent) -> None:
        try:
            if event.run_id in self.runs:
                self.runs[event.run_id].error_count += 1
            self.logger.write_event(event.to_dict())
        except Exception:
            pass

    def end_run(self, run_id: str, success: bool, final_status: str) -> None:
        try:
            if run_id in self.runs:
                record = self.runs[run_id]
                record.timestamp_end = datetime.now(timezone.utc).isoformat()
                record.success = success
                record.final_status = final_status
                
                # Calculate duration
                start = datetime.fromisoformat(record.timestamp_start)
                end = datetime.fromisoformat(record.timestamp_end)
                record.duration_s = (end - start).total_seconds()
                
                self.logger.write_event({"event_type": "run_summary", **record.to_dict()})
        except Exception:
            pass
