import os
import json
import ast
import dataclasses
from typing import Optional

from agents.base import Agent
from agents.models import AgentResult
from agents.schema import GeneratedProject, GeneratedFile, DebugPatch, parse_json_response
from orchestration.state import ProjectState

class SingleAgentBaseline(Agent):
    def __init__(self, provider, max_retries=2):
        super().__init__("SingleAgentBaseline", "Coding/Debugging", provider)
        self.max_retries = max_retries
        self.system_prompt = (
            "You are a general-purpose AI software engineering agent. "
            "You are responsible for writing, testing, and fixing code to meet the user's requirements. "
            "You must ALWAYS return your output as a valid JSON object matching the requested schema. "
            "Do NOT include conversational text outside the JSON."
        )

    def run(self, state: ProjectState) -> AgentResult:
        if not state.generated_project:
            return self._generate_initial_project(state)
        else:
            return self._debug_project(state)

    def _generate_initial_project(self, state: ProjectState) -> AgentResult:
        prompt = (
            f"User Requirement:\n{state.user_requirement}\n\n"
            "Generate the complete project implementation matching the following JSON schema:\n"
            "{\n"
            "  \"project_name\": \"string\",\n"
            "  \"files\": [\n"
            "    {\n"
            "      \"path\": \"string\",\n"
            "      \"content\": \"string\",\n"
            "      \"description\": \"string\",\n"
            "      \"requirement_ids\": []\n"
            "    }\n"
            "  ],\n"
            "  \"requirement_coverage\": {}\n"
            "}"
        )

        for attempt in range(self.max_retries):
            try:
                response = self.provider.generate(
                    prompt=prompt,
                    system_prompt=self.system_prompt,
                    temperature=0.2
                )
                
                try:
                    parsed_json = parse_json_response(response.text)
                    project = GeneratedProject.from_dict(parsed_json)
                    
                    self._validate_initial_project(project)
                    self._validate_syntax(project)
                    
                    state.generated_project = project
                    
                    return self._create_result(
                        success=True,
                        run_id=state.run_id,
                        output=project,
                        raw_response_available=True,
                        provider_name=response.provider,
                        model_name=response.model,
                        latency=response.latency_seconds,
                        token_usage=response.total_tokens,
                        generated_file_count=len(project.files)
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
                    prompt += f"\n\nYour previous response failed validation: {str(e)}\nPlease fix the structural or validation issue."
            except Exception as e:
                return self._create_result(
                    success=False, run_id=state.run_id, output=None, raw_response_available=False,
                    error_category="LLM_ERROR", error_message=str(e)
                )

        return self._create_result(
            success=False, run_id=state.run_id, output=None, raw_response_available=False,
            error_category="RETRY_EXHAUSTED", error_message="Exhausted retries."
        )

    def _debug_project(self, state: ProjectState) -> AgentResult:
        if state.test_result and state.test_result.status == "PASSED":
            return self._create_result(
                success=True, run_id=state.run_id, output=None, raw_response_available=False,
                error_category=None, error_message="Tests passed, debugging skipped."
            )
            
        files_json = json.dumps([{ "path": f.path, "content": f.content } for f in state.generated_project.files], indent=2)
        test_json = json.dumps(dataclasses.asdict(state.test_result), indent=2) if state.test_result else "{}"
        
        prompt = (
            f"User Requirement:\n{state.user_requirement}\n\n"
            f"Current Project Files:\n{files_json}\n\n"
            f"Test Result:\n{test_json}\n\n"
            "The tests failed. Analyze the failure and provide a patch to fix the code.\n"
            "Return the exact DebugPatch JSON:\n"
            "{\n"
            "  \"root_cause\": \"string\",\n"
            "  \"failure_category\": \"string\",\n"
            "  \"explanation\": \"string\",\n"
            "  \"changes\": [\n"
            "    {\n"
            "      \"path\": \"string\",\n"
            "      \"action\": \"modify\" | \"create\" | \"delete\",\n"
            "      \"new_content\": \"string\",\n"
            "      \"reason\": \"string\",\n"
            "      \"requirement_ids\": []\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        for attempt in range(self.max_retries):
            try:
                response = self.provider.generate(
                    prompt=prompt, system_prompt=self.system_prompt, temperature=0.2
                )

                try:
                    parsed_json = parse_json_response(response.text)
                    patch = DebugPatch.from_dict(parsed_json)
                    
                    self._validate_patch(patch, state)
                    self._apply_patch(patch, state)
                    
                    return self._create_result(
                        success=True, run_id=state.run_id, output=patch, raw_response_available=True,
                        provider_name=response.provider, model_name=response.model,
                        latency=response.latency_seconds, token_usage=response.total_tokens
                    )
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        return self._create_result(
                            success=False, run_id=state.run_id, output=response.text, raw_response_available=True,
                            provider_name=response.provider, model_name=response.model,
                            latency=response.latency_seconds, token_usage=response.total_tokens,
                            error_category=getattr(e, "error_category", "STRUCTURED_OUTPUT_ERROR"), error_message=str(e)
                        )
                    prompt += f"\n\nYour previous response failed validation: {str(e)}\nPlease fix the structural or validation issue."
            except Exception as e:
                return self._create_result(
                    success=False, run_id=state.run_id, output=None, raw_response_available=False,
                    error_category="LLM_ERROR", error_message=str(e)
                )

        return self._create_result(
            success=False, run_id=state.run_id, output=None, raw_response_available=False,
            error_category="RETRY_EXHAUSTED", error_message="Exhausted retries."
        )

    def _validate_initial_project(self, project: GeneratedProject):
        if not project.project_name or not project.files:
            e = ValueError("Invalid project structure")
            e.error_category = "VALIDATION_ERROR"
            raise e
        seen_paths = set()
        for f in project.files:
            path = f.path
            if os.path.isabs(path) or path.startswith("/") or path.startswith("\\") or ":" in path or ".." in path:
                e = ValueError(f"Unsafe path: {path}")
                e.error_category = "PATH_SECURITY_ERROR"
                raise e
            if path in seen_paths:
                e = ValueError(f"Duplicate file path: {path}")
                e.error_category = "DUPLICATE_FILE_ERROR"
                raise e
            seen_paths.add(path)

    def _validate_syntax(self, project: GeneratedProject):
        for f in project.files:
            if f.path.endswith(".py"):
                try:
                    ast.parse(f.content)
                except SyntaxError as e:
                    err = ValueError(f"Syntax error in {f.path}: {e}")
                    err.error_category = "SYNTAX_ERROR"
                    raise err

    def _validate_patch(self, patch: DebugPatch, state: ProjectState):
        project_paths = {f.path for f in state.generated_project.files}
        seen_paths = set()
        for change in patch.changes:
            path = change.path
            if os.path.isabs(path) or path.startswith("/") or path.startswith("\\") or ".." in path:
                e = ValueError(f"Unsafe path: {path}")
                e.error_category = "PATH_SECURITY_ERROR"
                raise e
            if change.action in ["modify", "delete"] and path not in project_paths:
                e = ValueError(f"Cannot {change.action} file {path} because it does not exist.")
                e.error_category = "VALIDATION_ERROR"
                raise e
            if change.action == "create" and path in project_paths:
                e = ValueError(f"Cannot create file {path} because it already exists.")
                e.error_category = "VALIDATION_ERROR"
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
                files_map[change.path] = GeneratedFile(
                    path=change.path, content=change.new_content,
                    description=change.reason, requirement_ids=change.requirement_ids
                )
            elif change.action == "modify":
                files_map[change.path].content = change.new_content
            elif change.action == "delete":
                if change.path in files_map:
                    del files_map[change.path]
        project.files = list(files_map.values())
