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
    
    # Run the workflow
    state = run_phase6_workflow(
        run_id, user_requirement, supervisor_provider, architecture_provider, coding_provider, testing_provider, sandbox_config
    )

    # Phase 8 RAG and Memory Initialization
    from rag.schemas import RAGConfig, MemoryRecord
    from rag.retriever import Retriever
    from rag.memory import ProjectMemory
    from rag.pipeline import RAGPipeline
    import uuid
    
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
    
    if memory:
        if state.project_plan:
            memory.add_memory(MemoryRecord(
                memory_id=str(uuid.uuid4()),
                timestamp="",
                project_id=run_id,
                memory_type="REQUIREMENT",
                content=f"Requirements: {len(state.project_plan.requirements)}",
                agent_name="SupervisorAgent"
            ))
        if state.architecture:
            memory.add_memory(MemoryRecord(
                memory_id=str(uuid.uuid4()),
                timestamp="",
                project_id=run_id,
                memory_type="ARCHITECTURE_DECISION",
                content=f"Architecture generated with {len(state.architecture.components)} components.",
                agent_name="ArchitectureAgent"
            ))
    
    if not state.test_result:
        return state
        
    if memory:
        memory.add_memory(MemoryRecord(
            memory_id=str(uuid.uuid4()),
            timestamp="",
            project_id=run_id,
            memory_type="TEST_RESULT",
            content=f"Test result: {state.test_result.status}, failures: {state.test_result.failures}",
            agent_name="TestingAgent"
        ))
        
    from agents.debugging import DebuggingAgent
    from agents.testing import TestingAgent
    debug_agent = DebuggingAgent(provider=debugging_provider)
    test_agent = TestingAgent(provider=testing_provider, sandbox_config=sandbox_config)
    
    iterations = 0
    while state.test_result.status != "PASSED" and iterations < max_debug_iterations:
        debug_result = debug_agent.run(state)
        
        if not debug_result.success:
            state.metadata["debugging_error"] = debug_result.error_message
            if memory:
                memory.add_memory(MemoryRecord(
                    memory_id=str(uuid.uuid4()),
                    timestamp="",
                    project_id=run_id,
                    memory_type="DEBUG_FAILURE",
                    content=f"Debug attempt failed: {debug_result.error_message}",
                    agent_name="DebuggingAgent"
                ))
            break
            
        test_result = test_agent.run(state)
        iterations += 1
        
        if memory:
            memory.add_memory(MemoryRecord(
                memory_id=str(uuid.uuid4()),
                timestamp="",
                project_id=run_id,
                memory_type="TEST_RESULT",
                content=f"Test result after debug: {state.test_result.status}, failures: {state.test_result.failures}",
                agent_name="TestingAgent"
            ))
        
        if not test_result.success:
            state.metadata["testing_error"] = test_result.error_message
            break
            
    if state.test_result.status != "PASSED" and iterations >= max_debug_iterations:
        state.metadata["debugging_error"] = "DEBUG_ITERATION_LIMIT"
    elif state.test_result.status == "PASSED" and memory and iterations > 0:
        memory.add_memory(MemoryRecord(
            memory_id=str(uuid.uuid4()),
            timestamp="",
            project_id=run_id,
            memory_type="DEBUG_SUCCESS",
            content=f"Successfully debugged issue after {iterations} iterations.",
            agent_name="DebuggingAgent"
        ))
        
    return state


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
