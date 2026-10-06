import re

with open("orchestration/workflow.py", "r") as f:
    content = f.read()

# Add Verification Agent to workflow
new_workflow = """
def run_phase9_workflow(
    run_id: str, 
    user_requirement: str, 
    supervisor_provider: LLMProvider, 
    architecture_provider: LLMProvider,
    coding_provider: LLMProvider,
    testing_provider: LLMProvider,
    debugging_provider: LLMProvider,
    verification_provider: LLMProvider,
    sandbox_config: Optional[dict] = None,
    max_debug_iterations: int = 3,
    use_rag: bool = False,
    use_memory: bool = False
) -> ProjectState:
    
    state = run_phase7_workflow(
        run_id, user_requirement, supervisor_provider, architecture_provider, coding_provider, testing_provider, debugging_provider, sandbox_config, max_debug_iterations, use_rag, use_memory
    )
    
    from agents.verification import VerificationAgent
    verification_agent = VerificationAgent(provider=verification_provider)
    verification_result = verification_agent.run(state)
    
    if not verification_result.success:
        state.metadata["verification_error"] = verification_result.error_message
        
    return state
"""

content = content + "\n" + new_workflow

with open("orchestration/workflow.py", "w") as f:
    f.write(content)

print("Updated workflow.py with Phase 9")
