import os
import uuid
from benchmarks.swebench_adapter import SWEBenchAdapter
from benchmarks.swebench_execution import SWEBenchExecutionLayer
from benchmarks.swebench_evaluator import SWEBenchNativeEvaluator
from llm.factory import create_llm_provider
from orchestration.workflow import run_single_agent_workflow
from execution.docker_sandbox import DockerSandbox
from observability.telemetry import Telemetry
from dotenv import load_dotenv

load_dotenv()

def smoke_test():
    task_id = "pytest-dev__pytest-11143"
    print(f"\n========== SMOKE TEST {task_id} ==========")
    
    adapter = SWEBenchAdapter()
    executor = SWEBenchExecutionLayer()
    evaluator = SWEBenchNativeEvaluator()
    
    meta = adapter.get_task_metadata(task_id)
    workspace = executor.prepare_repository(meta["repository"], meta["base_commit"])
    
    run_id = f"smoke_{uuid.uuid4().hex[:8]}"
    provider = create_llm_provider({"provider": "openrouter", "model": "inclusionai/ling-3.1-flash"})
    
    sandbox_config = {
        "docker_image": "python:3.11-slim",
        "timeout_seconds": 60,
        "allow_network_for_dependencies": True
    }
    
    class CustomSandbox(DockerSandbox):
        def create_workspace(self):
            self.workspace_dir = workspace
            self.sandbox_id = run_id
            
    # Need to pass state.sandbox into workflow
    print("Running agent workflow...")
    # Add a hook to workflow.py so we inject CustomSandbox
    state = run_single_agent_workflow(
        run_id=run_id,
        user_requirement=meta["problem_statement"],
        provider=provider,
        sandbox_config=sandbox_config,
        max_iterations=1,
        sandbox_override=CustomSandbox(sandbox_config)
    )
    
    # Manually ensure state.sandbox is available in state object for existing_repo check
    # Wait, in workflow.py `run_single_agent_workflow`, we don't attach `sandbox` to `state`?
    # Let me check if workflow.py attaches sandbox to state.
    
    patch = executor.extract_patch(workspace, meta["base_commit"])
    print(f"Patch extracted: {len(patch)} bytes")
    
    print("Running Native Evaluator...")
    eval_result = evaluator.evaluate(task_id, patch)
    
    print("Evaluation result:", eval_result)
    
if __name__ == '__main__':
    smoke_test()
