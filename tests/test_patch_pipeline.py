import os
import uuid
from benchmarks.swebench_adapter import SWEBenchAdapter
from benchmarks.swebench_execution import SWEBenchExecutionLayer
from benchmarks.swebench_evaluator import SWEBenchNativeEvaluator
from dotenv import load_dotenv

load_dotenv()

def run_patch_pipeline():
    task_id = "pytest-dev__pytest-11143"
    print(f"\n========== PATCH_PIPELINE_SMOKE_TEST {task_id} ==========")
    
    adapter = SWEBenchAdapter()
    executor = SWEBenchExecutionLayer()
    evaluator = SWEBenchNativeEvaluator()
    
    meta = adapter.get_task_metadata(task_id)
    
    print("1. Preparing base repository...")
    workspace = executor.prepare_repository(meta["repository"], meta["base_commit"])
    
    print("2. Making a deterministic local modification...")
    target_file = os.path.join(workspace, "src", "_pytest", "assertion", "__init__.py")
    with open(target_file, "a") as f:
        f.write("\n# PATCH_PIPELINE_SMOKE_TEST modification\n")
        
    print("3. Extracting non-empty patch...")
    patch = executor.extract_patch(workspace, meta["base_commit"])
    patch_size = len(patch.encode('utf-8'))
    print(f"Patch extracted: {patch_size} bytes")
    assert patch_size > 0, "Patch size must be > 0"
    
    print("4. Running Native Evaluator (applies patch to fresh workspace)...")
    eval_result = evaluator.evaluate(task_id, patch)
    
    print("Evaluation result:", eval_result)
    
if __name__ == '__main__':
    run_patch_pipeline()
