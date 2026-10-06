import os
import subprocess
from typing import Dict, Any

from benchmarks.swebench_adapter import SWEBenchAdapter
from benchmarks.swebench_execution import SWEBenchExecutionLayer

class SWEBenchNativeEvaluator:
    def __init__(self):
        self.adapter = SWEBenchAdapter()
        self.executor = SWEBenchExecutionLayer(work_dir_base="tmp_eval_workspaces")
        
    def evaluate(self, task_id: str, patch_content: str) -> Dict[str, Any]:
        meta = self.adapter.get_task_metadata(task_id)
        eval_meta = self.adapter.get_evaluation_metadata(task_id)
        
        # 2. Create a completely fresh evaluation workspace
        # 3. Checkout EXACT base_commit
        workspace = self.executor.prepare_repository(meta["repository"], meta["base_commit"])
        
        # 4. Prepare the validated task environment (Native VENV)
        venv_dir = os.path.join(workspace, "venv")
        subprocess.run(["python", "-m", "venv", venv_dir], check=True, capture_output=True)
        pip_exe = os.path.join(venv_dir, "Scripts", "pip") if os.name == "nt" else os.path.join(venv_dir, "bin", "pip")
        python_exe = os.path.join(venv_dir, "Scripts", "python") if os.name == "nt" else os.path.join(venv_dir, "bin", "python")
        pytest_exe = os.path.join(venv_dir, "Scripts", "pytest") if os.name == "nt" else os.path.join(venv_dir, "bin", "pytest")
        
        if "pytest" in task_id:
            subprocess.run([pip_exe, "install", "-e", ".[testing]"], cwd=workspace, check=True, capture_output=True)
        else:
            subprocess.run([pip_exe, "install", "-e", "."], cwd=workspace, check=True, capture_output=True)
        
        # 5. Apply ONLY the agent-generated patch
        if patch_content and patch_content.strip():
            patch_file = os.path.join(workspace, "agent.patch")
            with open(patch_file, "w") as f:
                f.write(patch_content)
            res = subprocess.run(["git", "apply", "agent.patch"], cwd=workspace, capture_output=True, text=True)
            if res.returncode != 0:
                return {
                    "status": "FAIL",
                    "failure_category": "PATCH_APPLICATION_FAILURE",
                    "details": res.stderr
                }
                
        # 6. Execute authoritative task test/evaluation commands
        # For simplicity in native evaluation, we run the specific test patch files if we know them
        # SWE-bench native evaluation is tricky because we must run specific tests. 
        # We will apply the hidden test_patch first
        test_patch_file = os.path.join(workspace, "eval.patch")
        with open(test_patch_file, "w") as f:
            f.write(eval_meta["test_patch"])
        subprocess.run(["git", "apply", "eval.patch"], cwd=workspace, capture_output=True, text=True)
        
        # Now run tests
        test_cmd = [pytest_exe] if "pytest" in task_id else [python_exe, "tests/runtests.py", "--settings=test_sqlite"]
        test_res = subprocess.run(test_cmd, cwd=workspace, capture_output=True, text=True)
        
        status = "PASS" if test_res.returncode == 0 else "FAIL"
        category = "TEST_FAILURE" if status == "FAIL" else None
        
        return {
            "status": status,
            "failure_category": category,
            "exit_code": test_res.returncode,
            "stdout": test_res.stdout,
            "stderr": test_res.stderr
        }
