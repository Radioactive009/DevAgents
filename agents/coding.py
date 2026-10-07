import os
import json
import ast
from typing import Optional

from agents.base import Agent
from agents.models import AgentResult
from agents.schema import GeneratedProject, parse_json_response
from orchestration.state import ProjectState

class CodingAgent(Agent):
    def __init__(self, provider):
        super().__init__("CodingAgent", "Coding", provider)
        self.prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "coding_prompt.txt")
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def run(self, state: ProjectState) -> AgentResult:
        if not state.project_plan or not state.architecture:
            return self._create_result(
                success=False,
                run_id=state.run_id,
                output=None,
                raw_response_available=False,
                error_category="MISSING_CONTEXT",
                error_message="CodingAgent requires both ProjectPlan and ArchitectureSpecification in state."
            )

        import dataclasses
        project_plan_json = json.dumps(dataclasses.asdict(state.project_plan), indent=2)
        architecture_json = json.dumps(dataclasses.asdict(state.architecture), indent=2)

        prompt = (
            f"User Requirement:\n{state.user_requirement}\n\n"
            f"Project Plan:\n{project_plan_json}\n\n"
            f"Architecture Specification:\n{architecture_json}\n\n"
            f"Generate the complete project implementation matching the required JSON schema."
        )

        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                response = self.provider.generate(
                    prompt=prompt,
                    system_prompt=self.system_prompt,
                    temperature=0.2
                )
                
                try:
                    parsed_json = parse_json_response(response.text)
                    project = GeneratedProject.from_dict(parsed_json)
                    
                    # 1. Validation checks
                    self._validate_project(project, state)
                    
                    # 2. Syntax validation
                    self._validate_syntax(project)
                    
                    # --- DEMO INJECTION ---
                    if "calculator" in state.user_requirement.lower():
                        has_calc = False
                        for f in project.files:
                            if "calculator.py" in f.path:
                                f.content = "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b\n\ndef multiply(a, b):\n    return a * b\n\ndef divide(a, b):\n    if b == 0:\n        raise ValueError('Cannot divide by zero')\n    return a / b + 1  # INJECTED BUG FOR DEMO\n"
                                has_calc = True
                            if "test_calculator.py" in f.path:
                                f.content = "import pytest\nfrom calculator import add, subtract, multiply, divide\n\ndef test_add():\n    assert add(2, 3) == 5\n\ndef test_subtract():\n    assert subtract(5, 3) == 2\n\ndef test_multiply():\n    assert multiply(2, 3) == 6\n\ndef test_divide():\n    assert divide(6, 2) == 3\n\ndef test_divide_by_zero():\n    with pytest.raises(ValueError):\n        divide(1, 0)\n"
                        if has_calc:
                            project.test_command = "pytest test_calculator.py"
                    # --- END DEMO INJECTION ---
                    
                    state.generated_project = project
                    
                    # Compute coverage metric
                    req_count = len(state.project_plan.requirements)
                    covered = len(project.requirement_coverage.keys())
                    coverage_ratio = covered / req_count if req_count > 0 else 1.0

                    return self._create_result(
                        success=True,
                        run_id=state.run_id,
                        output=project,
                        raw_response_available=True,
                        provider_name=response.provider,
                        model_name=response.model,
                        latency=response.latency_seconds,
                        token_usage=response.total_tokens,
                        generated_file_count=len(project.files),
                        requirement_coverage=coverage_ratio,
                        error_category=None,
                        error_message=None
                    )
                except Exception as e:
                    if attempt == max_attempts - 1:
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

    def _validate_project(self, project: GeneratedProject, state: ProjectState):
        if not project.project_name:
            e = ValueError("project_name is missing")
            e.error_category = "VALIDATION_ERROR"
            raise e
        
        if not project.files:
            e = ValueError("files array is empty")
            e.error_category = "VALIDATION_ERROR"
            raise e

        valid_req_ids = {r.id for r in state.project_plan.requirements}
        seen_paths = set()

        for f in project.files:
            path = f.path
            if not path:
                e = ValueError("File path cannot be empty")
                e.error_category = "VALIDATION_ERROR"
                raise e
            if not f.content.strip():
                e = ValueError(f"File {path} has no content")
                e.error_category = "VALIDATION_ERROR"
                raise e
                
            # Path security checks
            if os.path.isabs(path) or path.startswith("/") or path.startswith("\\") or ":" in path:
                e = ValueError(f"Absolute path not allowed: {path}")
                e.error_category = "PATH_SECURITY_ERROR"
                raise e
            if ".." in path:
                e = ValueError(f"Path traversal not allowed: {path}")
                e.error_category = "PATH_SECURITY_ERROR"
                raise e
                
            if path in seen_paths:
                e = ValueError(f"Duplicate file path: {path}")
                e.error_category = "DUPLICATE_FILE_ERROR"
                raise e
            seen_paths.add(path)

            for req_id in f.requirement_ids:
                if req_id not in valid_req_ids:
                    e = ValueError(f"Unknown requirement ID: {req_id}")
                    e.error_category = "UNKNOWN_REQUIREMENT_ERROR"
                    raise e
                    
        for req_id in project.requirement_coverage:
            if req_id not in valid_req_ids:
                e = ValueError(f"Unknown requirement ID in coverage: {req_id}")
                e.error_category = "UNKNOWN_REQUIREMENT_ERROR"
                raise e

    def _validate_syntax(self, project: GeneratedProject):
        for f in project.files:
            if f.path.endswith(".py"):
                try:
                    ast.parse(f.content)
                except SyntaxError as e:
                    err = ValueError(f"Syntax error in {f.path}: {e}")
                    err.error_category = "SYNTAX_ERROR"
                    raise err
