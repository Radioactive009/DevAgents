import os
import json
import time
import dataclasses
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from agents.base import Agent
from agents.models import AgentResult
from orchestration.state import ProjectState
from agents.schema import VerificationResult, VerificationCriterion, parse_json_response
from rag.context import ContextBuilder

class VerificationAgent(Agent):
    def __init__(self, provider, **kwargs):
        super().__init__(name="VerificationAgent", role="Verifier", provider=provider)
        prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "verification_prompt.txt")
        with open(prompt_path, "r") as f:
            self.system_prompt = f.read()

    def run(self, state: ProjectState) -> AgentResult:
        start_time = time.time()
        
        # Deterministic checks
        failed_checks = []
        if not state.generated_project:
            failed_checks.append("Project does not exist.")
        if not state.test_result:
            failed_checks.append("Test result does not exist.")
        elif state.test_result.exit_code is None:
            failed_checks.append("Test exit code is not available.")
            
        # Build prompt context
        context_builder = ContextBuilder()
        
        req_json = ""
        arch_json = ""
        if state.project_plan:
            req_json = json.dumps([dataclasses.asdict(r) for r in state.project_plan.requirements], indent=2)
        if state.architecture:
            arch_json = json.dumps(dataclasses.asdict(state.architecture), indent=2)
            
        files_json = "[]"
        if state.generated_project:
            files_json = json.dumps([{ "path": f.path, "content": f.content } for f in state.generated_project.files], indent=2)
            
        test_json = "{}"
        if state.test_result:
            test_json = json.dumps(dataclasses.asdict(state.test_result), indent=2)
            
        history_json = json.dumps(state.debugging_history, indent=2)
        
        task_info = f"Requirements:\\n{req_json}\\n\\nArchitecture:\\n{arch_json}\\n\\nCurrent Project Files:\\n{files_json}\\n\\nFailed Deterministic Checks:\\n{json.dumps(failed_checks)}"
        
        retriever = state.metadata.get('retriever')
        memory = state.metadata.get('memory')
        
        rag_chunks = None
        if retriever and state.test_result:
            query = f"Verification query: {state.user_requirement}"
            chunks, latency = retriever.retrieve(query, top_k=3)
            rag_chunks = chunks
            
        memory_records = None
        if memory and state.test_result:
            query = f"Verification query: {state.user_requirement}"
            records, latency = memory.retrieve_relevant_memory(query, top_k=3)
            memory_records = records
            
        safe_context = context_builder.build_context(
            task_info=task_info,
            test_result=dataclasses.asdict(state.test_result) if state.test_result else None,
            debug_history=state.debugging_history,
            rag_chunks=rag_chunks,
            memory_records=memory_records
        )
        
        response = self.provider.generate(
            prompt=safe_context,
            system_prompt=self.system_prompt
        )
        response_text = response.text
        token_usage = response.total_tokens
        
        try:
            parsed = parse_json_response(response_text)
            
            # Post-process with deterministic metrics
            total_reqs = len(state.project_plan.requirements) if state.project_plan else 0
            if total_reqs > 0:
                verified_reqs = len([c for c in parsed.get("criteria", []) if c.get("status") == "VERIFIED"])
                req_coverage = verified_reqs / total_reqs
            else:
                req_coverage = 0.0
                
            test_pass_rate = 0.0
            if state.test_result and state.test_result.tests_total and state.test_result.tests_total > 0:
                test_pass_rate = (state.test_result.tests_passed or 0) / state.test_result.tests_total
                
            duration = time.time() - start_time
            
            # Create object
            result = VerificationResult.from_dict({
                **parsed,
                "requirement_coverage": req_coverage,
                "test_pass_rate": test_pass_rate,
                "verification_duration": duration,
                "agent_name": "VerificationAgent",
                "provider": getattr(self.provider, "name", "unknown"),
                "model": getattr(self.provider, "model", "unknown"),
                "token_usage": token_usage,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "failed_checks": failed_checks + parsed.get("failed_checks", [])
            })
            
            if failed_checks and result.status == "VERIFIED":
                result.status = "PARTIALLY_VERIFIED"
                result.verified = False
                result.warnings.append("Demoted to PARTIALLY_VERIFIED due to failing deterministic checks.")
                
            state.verification_result = result
            return self._create_result(
                success=True,
                run_id=state.run_id,
                output=result,
                raw_response_available=True,
                provider_name=getattr(self.provider, "name", "unknown"),
                model_name=getattr(self.provider, "model", "unknown"),
                latency=getattr(response, "latency_seconds", None),
                token_usage=token_usage
            )
            
        except Exception as e:
            # Fallback
            result = VerificationResult(
                status="NOT_VERIFIED",
                verified=False,
                summary=f"Failed to parse verification result: {str(e)}",
                criteria=[],
                unmet_requirements=[r.id for r in state.project_plan.requirements] if state.project_plan else [],
                evidence="",
                failed_checks=failed_checks + ["LLM response parsing failed"],
                warnings=["Malformed LLM response"],
                requirement_coverage=0.0,
                test_pass_rate=0.0,
                verification_duration=time.time() - start_time,
                agent_name="VerificationAgent",
                provider=getattr(self.provider, "name", "unknown"),
                model=getattr(self.provider, "model", "unknown"),
                token_usage=token_usage,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            state.verification_result = result
            return self._create_result(
                success=False,
                run_id=state.run_id,
                output=result,
                raw_response_available=True,
                provider_name=getattr(self.provider, "name", "unknown"),
                model_name=getattr(self.provider, "model", "unknown"),
                latency=getattr(response, "latency_seconds", None),
                token_usage=token_usage,
                error_category="VERIFICATION_ERROR",
                error_message=f"Verification parsing failed: {str(e)}"
            )
