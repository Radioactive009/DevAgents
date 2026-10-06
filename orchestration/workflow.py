from orchestration.state import ProjectState
from agents.supervisor import SupervisorAgent
from agents.architecture import ArchitectureAgent
from llm.base import LLMProvider
from typing import Optional

def run_phase4_workflow(
    run_id: str, 
    user_requirement: str, 
    supervisor_provider: LLMProvider, 
    architecture_provider: LLMProvider
) -> ProjectState:
    
    state = ProjectState(run_id=run_id, user_requirement=user_requirement)
    
    supervisor = SupervisorAgent(provider=supervisor_provider)
    supervisor_result = supervisor.run(state)
    
    if not supervisor_result.success:
        state.metadata["supervisor_error"] = supervisor_result.error_message
        return state
        
    architecture = ArchitectureAgent(provider=architecture_provider)
    arch_result = architecture.run(state)
    
    if not arch_result.success:
        state.metadata["architecture_error"] = arch_result.error_message
        return state
        
    return state

def run_phase5_workflow(
    run_id: str, 
    user_requirement: str, 
    supervisor_provider: LLMProvider, 
    architecture_provider: LLMProvider,
    coding_provider: LLMProvider
) -> ProjectState:
    
    state = run_phase4_workflow(
        run_id, user_requirement, supervisor_provider, architecture_provider
    )
    
    if not state.project_plan or not state.architecture:
        return state
        
    from agents.coding import CodingAgent
    coding = CodingAgent(provider=coding_provider)
    coding_result = coding.run(state)
    
    if not coding_result.success:
        state.metadata["coding_error"] = coding_result.error_message
        
    return state

def run_phase6_workflow(
    run_id: str, 
    user_requirement: str, 
    supervisor_provider: LLMProvider, 
    architecture_provider: LLMProvider,
    coding_provider: LLMProvider,
    testing_provider: LLMProvider,
    sandbox_config: Optional[dict] = None
) -> ProjectState:
    
    state = run_phase5_workflow(
        run_id, user_requirement, supervisor_provider, architecture_provider, coding_provider
    )
    
    if not state.generated_project:
        return state
        
    from agents.testing import TestingAgent
    testing = TestingAgent(provider=testing_provider, sandbox_config=sandbox_config)
    testing_result = testing.run(state)
    
    if not testing_result.success:
        state.metadata["testing_error"] = testing_result.error_message
        
    return state
