import uuid
import time
import json
import os
import yaml
import random
import dataclasses
from datetime import datetime, UTC
from typing import Dict, Any, Optional, List

from experiments.schema import ExperimentProtocol, TaskManifestEntry, ExperimentRunResult
from orchestration.workflow import run_single_agent_workflow, run_phase11_workflow
from llm.base import create_llm_provider
from observability.telemetry import Telemetry

class ExperimentRunner:
    def __init__(self, protocol_path: str):
        self.protocol_path = protocol_path
        self.protocol = self._load_protocol()
        self.manifest = self._load_manifest()
        
        self.output_dir = os.path.join("experiment_results", self.protocol.name.replace(" ", "_").lower())
        os.makedirs(self.output_dir, exist_ok=True)
        self.runs_file = os.path.join(self.output_dir, "runs.jsonl")
        self.failures_file = os.path.join(self.output_dir, "failures.jsonl")

    def _load_protocol(self) -> ExperimentProtocol:
        if not os.path.exists(self.protocol_path):
            raise FileNotFoundError(f"Protocol not found: {self.protocol_path}")
        with open(self.protocol_path, "r") as f:
            data = yaml.safe_load(f)
        return ExperimentProtocol.from_dict(data)

    def _load_manifest(self) -> List[TaskManifestEntry]:
        path = self.protocol.task_manifest
        if not os.path.exists(path):
            raise FileNotFoundError(f"Task manifest not found: {path}")
        with open(path, "r") as f:
            data = json.load(f)
        return [TaskManifestEntry(**item) for item in data if item.get("inclusion_status") == "INCLUDED"]

    def validate_pre_flight(self):
        """Validates configuration before allowing ANY execution."""
        if not self.manifest:
            raise ValueError("Task manifest is empty or missing.")
            
        task_ids = set()
        for t in self.manifest:
            if t.task_id in task_ids:
                raise ValueError(f"Duplicate task ID in manifest: {t.task_id}")
            task_ids.add(t.task_id)
            
        if len(self.manifest) != self.protocol.task_count:
            print(f"Warning: Manifest length ({len(self.manifest)}) does not match protocol task_count ({self.protocol.task_count}).")
            
        if not self.protocol.systems:
            raise ValueError("No systems defined in protocol.")
            
        for sys in self.protocol.systems:
            if sys not in ["SINGLE_AGENT_BASELINE", "MULTI_AGENT", "MULTI_AGENT_RAG", "MULTI_AGENT_RAG_MEMORY"]:
                raise ValueError(f"Unknown system configuration: {sys}")
                
        # Validate result directory is writable
        if not os.access(self.output_dir, os.W_OK):
            raise ValueError(f"Result directory is not writable: {self.output_dir}")
            
        print("Pre-flight validation passed.")

    def run_one_task(self, task_id: str):
        """Runs all configurations for a single task."""
        self.validate_pre_flight()
        task = next((t for t in self.manifest if t.task_id == task_id), None)
        if not task:
            raise ValueError(f"Task not found: {task_id}")
            
        # Deterministic randomized order based on seed + task_id
        random.seed(f"{self.protocol.reproducibility.random_seed}_{task_id}")
        systems = list(self.protocol.systems)
        random.shuffle(systems)
        
        for sys in systems:
            self._execute_run(task, sys)

    def run_one_configuration(self, system: str):
        """Runs all tasks for a single configuration."""
        self.validate_pre_flight()
        if system not in self.protocol.systems:
            raise ValueError(f"System not in protocol: {system}")
            
        for task in self.manifest:
            self._execute_run(task, system)

    def run_full_experiment(self):
        """Runs all configurations for all tasks."""
        self.validate_pre_flight()
        for task in self.manifest:
            self.run_one_task(task.task_id)

    def _execute_run(self, task: TaskManifestEntry, system: str):
        run_id = f"{task.task_id}_{system}_{uuid.uuid4().hex[:8]}"
        print(f"Executing Run {run_id}...")
        
        # We wrap in a global try-except to never crash the whole experiment runner
        # unless it's a critical infrastructure issue, but even then we log it.
        try:
            sandbox_config = {
                "docker_image": self.protocol.execution.docker_image,
                "timeout_seconds": self.protocol.execution.timeout_seconds,
                "allow_network_for_dependencies": "deps" in self.protocol.execution.network_policy
            }
            
            provider_config = {
                "provider": self.protocol.llm.provider,
                "model": self.protocol.llm.model
            }
            
            provider = create_llm_provider(provider_config)
            
            start_t = time.time()
            timestamp = datetime.now(UTC).isoformat()
            
            if system == "SINGLE_AGENT_BASELINE":
                state = run_single_agent_workflow(
                    run_id=run_id,
                    user_requirement=task.task_description,
                    provider=provider,
                    sandbox_config=sandbox_config,
                    max_iterations=self.protocol.execution.max_debug_iterations
                )
            else:
                use_rag = "RAG" in system
                use_memory = "MEMORY" in system
                
                # Create duplicate providers for each role to match standard pipeline
                state = run_phase11_workflow(
                    run_id=run_id,
                    user_requirement=task.task_description,
                    supervisor_provider=create_llm_provider(provider_config),
                    architecture_provider=create_llm_provider(provider_config),
                    coding_provider=create_llm_provider(provider_config),
                    testing_provider=create_llm_provider(provider_config),
                    debugging_provider=create_llm_provider(provider_config),
                    verification_provider=create_llm_provider(provider_config),
                    use_rag=use_rag,
                    use_memory=use_memory,
                    use_tools=False,
                    sandbox_config=sandbox_config,
                    max_debug_iterations=self.protocol.execution.max_debug_iterations
                )
                
            end_t = time.time()
            
            # Fetch telemetry for this run to populate result schema
            telemetry = Telemetry.get_instance()
            record = telemetry.runs.get(run_id)
            
            if not record:
                raise RuntimeError("Telemetry record not found for run.")
                
            test_pass_rate = 0.0
            bug_fix_success = False
            final_test_pass = False
            
            if state.test_result:
                final_test_pass = (state.test_result.status == "PASSED")
                if state.test_result.tests_total:
                    test_pass_rate = state.test_result.tests_passed / max(1, state.test_result.tests_total)
                bug_fix_success = final_test_pass
                
            error_type = None
            error_msg = None
            if state.metadata.get("coding_error"):
                error_type = "CODING_ERROR"
                error_msg = state.metadata["coding_error"]
            elif state.metadata.get("testing_error"):
                error_type = "TESTING_ERROR"
                error_msg = state.metadata["testing_error"]
            elif state.metadata.get("debugging_error"):
                error_type = "DEBUGGING_ERROR"
                error_msg = state.metadata["debugging_error"]
            elif state.metadata.get("verification_error"):
                error_type = "VERIFICATION_ERROR"
                error_msg = state.metadata["verification_error"]
                
            result = ExperimentRunResult(
                run_id=run_id,
                experiment_id=self.protocol.name,
                task_id=task.task_id,
                benchmark=task.benchmark,
                benchmark_version=task.benchmark_version,
                configuration=system,
                provider=self.protocol.llm.provider,
                model=self.protocol.llm.model,
                prompt_version=self.protocol.reproducibility.prompt_version,
                protocol_version=self.protocol.version,
                git_commit=self.protocol.reproducibility.git_commit,
                timestamp=timestamp,
                success=final_test_pass,
                final_test_pass=final_test_pass,
                test_pass_rate=test_pass_rate,
                requirement_coverage=0.0,
                code_coverage=0.0,
                bug_fix_success=bug_fix_success,
                verification_status=state.verification_result.status if state.verification_result else "UNKNOWN",
                debug_iterations=record.debugging_iterations,
                max_debug_iterations=self.protocol.execution.max_debug_iterations,
                failure_category=state.test_result.failure_category if state.test_result else None,
                llm_calls=record.total_llm_calls,
                input_tokens=getattr(record, 'total_tokens', 0), # Simplified tokens
                output_tokens=0,
                total_tokens=getattr(record, 'total_tokens', 0),
                tool_calls=record.total_tool_calls,
                test_calls=len(record.test_events),
                execution_time_seconds=end_t - start_t,
                llm_latency_seconds=sum(e.duration_ms for e in record.agent_events) / 1000.0,
                test_execution_seconds=sum(e.duration_ms for e in record.test_events) / 1000.0,
                human_intervention=False,
                rag_enabled="RAG" in system,
                rag_calls=record.total_rag_queries,
                rag_latency_seconds=0.0,
                memory_enabled="MEMORY" in system,
                memory_calls=0,
                memory_latency_seconds=0.0,
                error_type=error_type,
                error_message_sanitized=error_msg
            )
            
            with open(self.runs_file, "a") as f:
                f.write(json.dumps(dataclasses.asdict(result)) + "\n")
                
        except Exception as e:
            # Infrastructure failure
            print(f"Run {run_id} failed with infrastructure error: {e}")
            failure_record = {
                "run_id": run_id,
                "task_id": task.task_id,
                "configuration": system,
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat()
            }
            with open(self.failures_file, "a") as f:
                f.write(json.dumps(failure_record) + "\n")
