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

def run_phase7_workflow(
    run_id: str, 
    user_requirement: str, 
    supervisor_provider: LLMProvider, 
    architecture_provider: LLMProvider,
    coding_provider: LLMProvider,
    testing_provider: LLMProvider,
    debugging_provider: LLMProvider,
    sandbox_config: Optional[dict] = None,
    max_debug_iterations: int = 3,
    use_rag: bool = False,
    use_memory: bool = False
) -> ProjectState:
    

    # Phase 8 RAG and Memory Initialization
    from rag.schemas import RAGConfig
    from rag.retriever import Retriever
    from rag.memory import ProjectMemory
    from rag.pipeline import RAGPipeline
    
    rag_config = RAGConfig(use_rag=use_rag, use_memory=use_memory)
    
    retriever = None
    if use_rag:
        pipeline = RAGPipeline(rag_config)
        pipeline.vector_store.load()
        retriever = Retriever(pipeline.embedder, pipeline.vector_store)
        
    memory = None
    if use_memory:
        memory = ProjectMemory(rag_config.memory_store_path)
        
    state.metadata['retriever'] = retriever
    state.metadata['memory'] = memory
    
    # Run the workflow
    state = run_phase6_workflow(
        run_id, user_requirement, supervisor_provider, architecture_provider, coding_provider, testing_provider, sandbox_config
    )
    
    if not state.test_result:
        return state
        
    from agents.debugging import DebuggingAgent
    debug_agent = DebuggingAgent(provider=debugging_provider)
    test_agent = TestingAgent(provider=testing_provider, sandbox_config=sandbox_config)
    
    iterations = 0
    while state.test_result.status != "PASSED" and iterations < max_debug_iterations:
        debug_result = debug_agent.run(state)
        
        if not debug_result.success:
            state.metadata["debugging_error"] = debug_result.error_message
            break
            
        test_result = test_agent.run(state)
        iterations += 1
        
        if not test_result.success:
            state.metadata["testing_error"] = test_result.error_message
            break
            
    if state.test_result.status != "PASSED" and iterations >= max_debug_iterations:
        state.metadata["debugging_error"] = "DEBUG_ITERATION_LIMIT"
        
    return state
