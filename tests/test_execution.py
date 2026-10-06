from benchmarks.swebench_adapter import SWEBenchAdapter
from benchmarks.swebench_execution import SWEBenchExecutionLayer
import os

def test_execution():
    adapter = SWEBenchAdapter()
    executor = SWEBenchExecutionLayer()
    
    tasks = ["pytest-dev__pytest-11143", "django__django-16816"]
    
    for task_id in tasks:
        print(f"Preparing {task_id}...")
        meta = adapter.get_task_metadata(task_id)
        
        # Clone & checkout
        workspace = executor.prepare_repository(meta["repository"], meta["base_commit"])
        print(f"Workspace ready at {workspace}")
        
        # Make fake edit
        test_file = os.path.join(workspace, "fake_edit.txt")
        with open(test_file, "w") as f:
            f.write("agent was here")
            
        # Extract patch
        patch = executor.extract_patch(workspace, meta["base_commit"])
        print(f"Patch extracted: {len(patch)} bytes")
        assert "agent was here" in patch

if __name__ == '__main__':
    test_execution()
    print("ALL TESTS PASSED")
