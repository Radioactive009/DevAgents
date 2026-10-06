import os
import json
from typing import Optional

from agents.base import Agent
from agents.models import AgentResult
from agents.schema import ArchitectureSpecification, parse_json_response
from orchestration.state import ProjectState

class ArchitectureAgent(Agent):
    def __init__(self, provider):
        super().__init__("ArchitectureAgent", "Architecture", provider)
        self.prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "architecture_prompt.txt")
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def run(self, state: ProjectState) -> AgentResult:
        if not state.project_plan:
            return self._create_result(
                success=False,
                run_id=state.run_id,
                output=None,
                raw_response_available=False,
                error_category="VALIDATION_ERROR",
                error_message="ArchitectureAgent requires a ProjectPlan in state."
            )
            
        import dataclasses
        project_plan_json = json.dumps(dataclasses.asdict(state.project_plan), indent=2)
            
        prompt = (
            f"User Requirement:\n{state.user_requirement}\n\n"
            f"Project Plan:\n{project_plan_json}"
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
                    architecture = ArchitectureSpecification.from_dict(parsed_json)
                    state.architecture = architecture
                    
                    return self._create_result(
                        success=True,
                        run_id=state.run_id,
                        output=architecture,
                        raw_response_available=True,
                        provider_name=response.provider,
                        model_name=response.model,
                        latency=response.latency_seconds,
                        token_usage=response.total_tokens,
                        error_category=None,
                        error_message=None
                    )
                except Exception as e:
                    if attempt == max_attempts - 1:
                        return self._create_result(
                            success=False,
                            run_id=state.run_id,
                            output=response.text,
                            raw_response_available=True,
                            provider_name=response.provider,
                            model_name=response.model,
                            latency=response.latency_seconds,
                            token_usage=response.total_tokens,
                            error_category="STRUCTURED_OUTPUT_ERROR",
                            error_message=str(e)
                        )
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
