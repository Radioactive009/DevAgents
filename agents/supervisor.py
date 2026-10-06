import os
import json
from typing import Optional

from agents.base import Agent
from agents.models import AgentResult
from agents.schema import ProjectPlan, parse_json_response
from orchestration.state import ProjectState

class SupervisorAgent(Agent):
    def __init__(self, provider):
        super().__init__("SupervisorAgent", "Supervisor", provider)
        self.prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "supervisor_prompt.txt")
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    def run(self, state: ProjectState) -> AgentResult:
        prompt = f"User Requirement:\n{state.user_requirement}"
        
        # We allow 1 retry on structured output failure
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
                    project_plan = ProjectPlan.from_dict(parsed_json)
                    state.project_plan = project_plan
                    
                    return self._create_result(
                        success=True,
                        run_id=state.run_id,
                        output=project_plan,
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
                    # Loop continues for retry
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
