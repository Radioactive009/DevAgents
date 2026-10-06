import os
import json
import ast
import dataclasses
from typing import Optional

from agents.base import Agent
from agents.models import AgentResult
from agents.schema import DebugPatch, DebugResult, GeneratedFile, parse_json_response
from orchestration.state import ProjectState

class DebuggingAgent(Agent):
    def __init__(self, provider, max_retries=2):
        super().__init__("DebuggingAgent", "Debugging", provider)
        self.max_retries = max_retries
        self.prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "debugging_prompt.txt")
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

        self.protected_files = [".env", ".git"]

    def run(self, state: ProjectState) -> AgentResult:
        if state.test_result and state.test_result.status == "PASSED":
            # Do not debug if tests passed
            return self._create_result(
                success=True,
                run_id=state.run_id,
                output=None,
                raw_response_available=False,
                error_category=None,
                error_message="Tests passed, debugging skipped."
            )

        if not state.generated_project or not state.test_result:
            return self._create_result(
                success=False,
                run_id=state.run_id,
                output=None,
                raw_response_available=False,
                error_category="MISSING_CONTEXT",
                error_message="DebuggingAgent requires generated_project and test_result in state."
            )

        # Count iteration
        iteration = len(state.debugging_history) + 1

        prompt = self._build_prompt(state)

        for attempt in range(self.max_retries):
            try:
                response = self.provider.generate(
                    prompt=prompt,
                    system_prompt=self.system_prompt,
                    temperature=0.2
                )

                try:
                    parsed_json = parse_json_response(response.text)
                    patch = DebugPatch.from_dict(parsed_json)
                    
                    # Validation checks
                    self._validate_patch(patch, state)
                    
                    # Apply changes to state's generated_project
                    self._apply_patch(patch, state)
                    
                    debug_result = DebugResult(
                        success=True,
                        agent_name=self.name,
                        root_cause=patch.root_cause,
                        failure_category=patch.failure_category,
                        affected_files=[c.path for c in patch.changes],
                        changes=patch.changes,
                        reasoning_summary=patch.explanation,
                        requirement_ids=list(set(req for c in patch.changes for req in c.requirement_ids)),
                        debug_iteration=iteration,
                        previous_test_status=state.test_result.status,
                        provider=response.provider,
                        model=response.model,
                        latency=response.latency_seconds,
                        token_usage=response.total_tokens
                    )
                    
                    # Record history
                    state.debugging_history.append({
                        "iteration": iteration,
                        "failure_category": patch.failure_category,
                        "root_cause": patch.root_cause,
                        "files_changed": debug_result.affected_files,
                        "test_status_before": state.test_result.status,
                        "model": response.model,
                        "token_usage": response.total_tokens
                    })

                    return self._create_result(
                        success=True,
                        run_id=state.run_id,
                        output=debug_result,
                        raw_response_available=True,
                        provider_name=response.provider,
                        model_name=response.model,
                        latency=response.latency_seconds,
                        token_usage=response.total_tokens
                    )
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        error_category = getattr(e, "error_category", "STRUCTURED_OUTPUT_ERROR")
                        return self._create_result(
                            success=False,
                            run_id=state.run_id,
                            output=response.text,
                            raw_response_available=True,
                            provider_name=response.provider,
                            model_name=response.model,
                            latency=response.latency_seconds,
                            token_usage=response.total_tokens,
                            error_category=error_category,
                            error_message=str(e)
                        )
                    # Modify prompt for retry
                    prompt += f"\n\nYour previous response failed validation: {str(e)}\nPlease fix the structural or validation issue."
            except Exception as e:
                return self._create_result(
                    success=False,
                    run_id=state.run_id,
                    output=None,
                    raw_response_available=False,
                    error_category="LLM_ERROR",
                    error_message=str(e)
                )

        return self._create_result(
            success=False,
            run_id=state.run_id,
            output=None,
            raw_response_available=False,
            error_category="RETRY_EXHAUSTED",
            error_message="Exhausted retries."
        )

    def _build_prompt(self, state: ProjectState) -> str:
        req_json = ""
        arch_json = ""
        
        if state.project_plan:
            req_json = json.dumps([dataclasses.asdict(r) for r in state.project_plan.requirements], indent=2)
            
        if state.architecture:
            arch_json = json.dumps(dataclasses.asdict(state.architecture), indent=2)
            
        files_json = json.dumps([{ "path": f.path, "content": f.content } for f in state.generated_project.files], indent=2)
        test_json = json.dumps(dataclasses.asdict(state.test_result), indent=2)
        history_json = json.dumps(state.debugging_history, indent=2)
        
        ml_prediction = ""
        if state.failure_classification:
            ml_prediction = f"ML Failure Classification Prediction:\n{json.dumps(state.failure_classification, indent=2)}\n\n(Treat this as supporting evidence only)"
        
        return (
            f"Requirements:\n{req_json}\n\n"
            f"Architecture:\n{arch_json}\n\n"
            f"Current Project Files:\n{files_json}\n\n"
            f"Current Test Result (FAILURE):\n{test_json}\n\n"
            f"{ml_prediction}\n\n"
            f"Debugging History:\n{history_json}\n\n"
            f"Provide the exact DebugPatch JSON to fix the failure."
        )

    def _validate_patch(self, patch: DebugPatch, state: ProjectState):
        valid_req_ids = set()
        if state.project_plan:
            valid_req_ids = {r.id for r in state.project_plan.requirements}
            
        project_paths = {f.path for f in state.generated_project.files}
        
        seen_paths = set()
        for change in patch.changes:
            path = change.path
            
            if os.path.isabs(path) or path.startswith("/") or path.startswith("\\") or ".." in path:
                e = ValueError(f"Unsafe path: {path}")
                e.error_category = "PATH_SECURITY_ERROR"
                raise e
                
            if any(path.startswith(p) for p in self.protected_files):
                e = ValueError(f"Protected file modification not allowed: {path}")
                e.error_category = "SECURITY_ERROR"
                raise e
                
            if path in seen_paths:
                e = ValueError(f"Duplicate change for path: {path}")
                e.error_category = "VALIDATION_ERROR"
                raise e
            seen_paths.add(path)
            
            if change.action not in ["modify", "create", "delete"]:
                e = ValueError(f"Invalid action: {change.action}")
                e.error_category = "VALIDATION_ERROR"
                raise e
                
            if change.action in ["modify", "delete"] and path not in project_paths:
                e = ValueError(f"Cannot {change.action} file {path} because it does not exist.")
                e.error_category = "VALIDATION_ERROR"
                raise e
                
            if change.action == "create" and path in project_paths:
                e = ValueError(f"Cannot create file {path} because it already exists.")
                e.error_category = "VALIDATION_ERROR"
                raise e
                
            for req_id in change.requirement_ids:
                if req_id not in valid_req_ids:
                    e = ValueError(f"Unknown requirement ID: {req_id}")
                    e.error_category = "UNKNOWN_REQUIREMENT_ERROR"
                    raise e
                    
            if change.action in ["modify", "create"] and path.endswith(".py"):
                try:
                    ast.parse(change.new_content)
                except SyntaxError as ex:
                    e = ValueError(f"Syntax error in applied patch for {path}: {ex}")
                    e.error_category = "SYNTAX_ERROR"
                    raise e

    def _apply_patch(self, patch: DebugPatch, state: ProjectState):
        project = state.generated_project
        files_map = {f.path: f for f in project.files}
        
        for change in patch.changes:
            if change.action == "create":
                new_file = GeneratedFile(
                    path=change.path,
                    content=change.new_content,
                    description=change.reason,
                    requirement_ids=change.requirement_ids
                )
                files_map[change.path] = new_file
                for req in change.requirement_ids:
                    if req not in project.requirement_coverage:
                        project.requirement_coverage[req] = []
                    project.requirement_coverage[req].append(change.path)
            elif change.action == "modify":
                f = files_map[change.path]
                f.content = change.new_content
                # Update coverage if new requirement added
                for req in change.requirement_ids:
                    if req not in f.requirement_ids:
                        f.requirement_ids.append(req)
                        if req not in project.requirement_coverage:
                            project.requirement_coverage[req] = []
                        if change.path not in project.requirement_coverage[req]:
                            project.requirement_coverage[req].append(change.path)
            elif change.action == "delete":
                del files_map[change.path]
                for req, paths in project.requirement_coverage.items():
                    if change.path in paths:
                        paths.remove(change.path)
                        
        project.files = list(files_map.values())
