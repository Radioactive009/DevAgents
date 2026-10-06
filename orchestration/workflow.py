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

def run_phase11_workflow(
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
    use_memory: bool = False,
    use_tools: bool = True
) -> ProjectState:
    from observability.telemetry import Telemetry
    from observability.schema import AgentEvent, TestEvent, DebugEvent, VerificationEvent, ErrorEvent
    import time
    
    telemetry = Telemetry.get_instance()
    
    config = {
        "use_rag": use_rag,
        "use_memory": use_memory,
        "use_tools": use_tools,
        "max_debug_iterations": max_debug_iterations,
        "sandbox_config": sandbox_config
    }
    telemetry.start_run(run_id, "task-" + run_id, config, getattr(supervisor_provider, "name", "unknown"), getattr(supervisor_provider, "model", "unknown"))

    try:
        state = ProjectState(run_id=run_id, user_requirement=user_requirement)
        
        # Phase 8 RAG and Memory Initialization (from phase 7)
        from rag.schemas import RAGConfig
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

        # Supervisor
        start_t = time.time()
        supervisor = SupervisorAgent(provider=supervisor_provider)
        res = supervisor.run(state)
        telemetry.record_agent(AgentEvent(run_id=run_id, agent_name="SupervisorAgent", phase="supervisor", duration_ms=(time.time()-start_t)*1000, success=res.success))
        if not res.success:
            state.metadata["supervisor_error"] = res.error_message
            telemetry.record_error(ErrorEvent(run_id=run_id, component="SupervisorAgent", phase="supervisor", error_type="AGENT_ERROR", message=str(res.error_message)))
            telemetry.end_run(run_id, False, "SUPERVISOR_FAILED")
            return state

        # Architecture
        start_t = time.time()
        architecture = ArchitectureAgent(provider=architecture_provider)
        res = architecture.run(state)
        telemetry.record_agent(AgentEvent(run_id=run_id, agent_name="ArchitectureAgent", phase="architecture", duration_ms=(time.time()-start_t)*1000, success=res.success))
        if not res.success:
            state.metadata["architecture_error"] = res.error_message
            telemetry.end_run(run_id, False, "ARCHITECTURE_FAILED")
            return state

        # Coding
        from agents.coding import CodingAgent
        start_t = time.time()
        coding = CodingAgent(provider=coding_provider)
        res = coding.run(state)
        telemetry.record_agent(AgentEvent(run_id=run_id, agent_name="CodingAgent", phase="coding", duration_ms=(time.time()-start_t)*1000, success=res.success))
        if not res.success:
            state.metadata["coding_error"] = res.error_message
            telemetry.end_run(run_id, False, "CODING_FAILED")
            return state

        # Testing & Debugging
        from agents.testing import TestingAgent
        from agents.debugging import DebuggingAgent
        test_agent = TestingAgent(provider=testing_provider, sandbox_config=sandbox_config)
        debug_agent = DebuggingAgent(provider=debugging_provider)

        start_t = time.time()
        test_res = test_agent.run(state)
        telemetry.record_test(TestEvent(
            run_id=run_id, duration_ms=(time.time()-start_t)*1000, success=test_res.success,
            exit_code=getattr(state.test_result, "exit_code", None),
            test_pass_rate=(state.test_result.tests_passed / max(1, state.test_result.tests_total)) if state.test_result and state.test_result.tests_total else 0.0
        ))
        
        iterations = 0
        while state.test_result and state.test_result.status != "PASSED" and iterations < max_debug_iterations:
            start_d = time.time()
            debug_res = debug_agent.run(state)
            telemetry.record_debug(DebugEvent(run_id=run_id, iteration=iterations+1, success=debug_res.success, duration_ms=(time.time()-start_d)*1000, agent_name="DebuggingAgent"))
            
            if not debug_res.success:
                state.metadata["debugging_error"] = debug_res.error_message
                break
                
            start_t = time.time()
            test_res = test_agent.run(state)
            iterations += 1
            telemetry.record_test(TestEvent(
                run_id=run_id, duration_ms=(time.time()-start_t)*1000, success=test_res.success,
                exit_code=getattr(state.test_result, "exit_code", None),
                test_pass_rate=(state.test_result.tests_passed / max(1, state.test_result.tests_total)) if state.test_result and state.test_result.tests_total else 0.0
            ))
            
            if not test_res.success:
                state.metadata["testing_error"] = test_res.error_message
                break

        # Verification
        from agents.verification import VerificationAgent
        start_v = time.time()
        verification_agent = VerificationAgent(provider=verification_provider)
        res = verification_agent.run(state)
        telemetry.record_verification(VerificationEvent(
            run_id=run_id, duration_ms=(time.time()-start_v)*1000, status=getattr(state.verification_result, "status", "UNKNOWN"),
            requirement_coverage=getattr(state.verification_result, "requirement_coverage", 0.0)
        ))
        if not res.success:
            state.metadata["verification_error"] = res.error_message
            
        final_status = getattr(state.verification_result, "status", "UNKNOWN")
        telemetry.end_run(run_id, final_status == "VERIFIED", final_status)
        
    except Exception as e:
        telemetry.record_error(ErrorEvent(run_id=run_id, component="workflow", phase="unknown", error_type="WORKFLOW_ERROR", message=str(e)))
        telemetry.end_run(run_id, False, "ERROR")

    return state

def run_single_agent_workflow(
    run_id: str,
    user_requirement: str,
    provider: LLMProvider,
    sandbox_config: Optional[dict] = None,
    max_iterations: int = 3
) -> ProjectState:
    from observability.telemetry import Telemetry
    from observability.schema import AgentEvent, TestEvent, DebugEvent, ErrorEvent
    import time
    
    telemetry = Telemetry.get_instance()
    
    config = {
        "use_rag": False,
        "use_memory": False,
        "max_iterations": max_iterations,
        "sandbox_config": sandbox_config,
        "system": "SINGLE_AGENT_BASELINE"
    }
    telemetry.start_run(run_id, "task-" + run_id, config, getattr(provider, "name", "unknown"), getattr(provider, "model", "unknown"))

    try:
        state = ProjectState(run_id=run_id, user_requirement=user_requirement)
        
        # Single Agent initialization
        from agents.single_agent_baseline import SingleAgentBaseline
        agent = SingleAgentBaseline(provider=provider, max_retries=2)
        
        # 1. Generate code
        start_t = time.time()
        gen_res = agent.run(state)
        telemetry.record_agent(AgentEvent(run_id=run_id, agent_name="SingleAgentBaseline", phase="coding", duration_ms=(time.time()-start_t)*1000, success=gen_res.success))
        
        if not gen_res.success:
            state.metadata["coding_error"] = gen_res.error_message
            telemetry.end_run(run_id, False, "CODING_FAILED")
            return state

        # 2. Test Execution & Debug Loop
        from agents.testing import TestingAgent
        # We reuse testing infrastructure but it's just deterministically executing tests. 
        # It's not a reasoning agent.
        test_executor = TestingAgent(provider=provider, sandbox_config=sandbox_config)
        
        start_t = time.time()
        test_res = test_executor.run(state)
        telemetry.record_test(TestEvent(
            run_id=run_id, duration_ms=(time.time()-start_t)*1000, success=test_res.success,
            exit_code=getattr(state.test_result, "exit_code", None),
            test_pass_rate=(state.test_result.tests_passed / max(1, state.test_result.tests_total)) if state.test_result and state.test_result.tests_total else 0.0
        ))
        
        iterations = 0
        while state.test_result and state.test_result.status != "PASSED" and iterations < max_iterations:
            start_d = time.time()
            debug_res = agent.run(state)
            telemetry.record_debug(DebugEvent(run_id=run_id, iteration=iterations+1, success=debug_res.success, duration_ms=(time.time()-start_d)*1000, agent_name="SingleAgentBaseline"))
            
            if not debug_res.success:
                state.metadata["debugging_error"] = debug_res.error_message
                break
                
            start_t = time.time()
            test_res = test_executor.run(state)
            iterations += 1
            telemetry.record_test(TestEvent(
                run_id=run_id, duration_ms=(time.time()-start_t)*1000, success=test_res.success,
                exit_code=getattr(state.test_result, "exit_code", None),
                test_pass_rate=(state.test_result.tests_passed / max(1, state.test_result.tests_total)) if state.test_result and state.test_result.tests_total else 0.0
            ))
            
            if not test_res.success:
                state.metadata["testing_error"] = test_res.error_message
                break

        final_status = "PASSED" if (state.test_result and state.test_result.status == "PASSED") else "FAILED"
        telemetry.end_run(run_id, final_status == "PASSED", final_status)
        
    except Exception as e:
        telemetry.record_error(ErrorEvent(run_id=run_id, component="workflow", phase="unknown", error_type="WORKFLOW_ERROR", message=str(e)))
        telemetry.end_run(run_id, False, "ERROR")

    return state
