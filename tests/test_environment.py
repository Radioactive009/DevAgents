import os
import subprocess
from benchmarks.swebench_adapter import SWEBenchAdapter
from benchmarks.swebench_execution import SWEBenchExecutionLayer

def test_environments():
    adapter = SWEBenchAdapter()
    executor = SWEBenchExecutionLayer()
    
    # 1. Pytest
    task_id = "pytest-dev__pytest-11143"
    print(f"\nVerifying environment for {task_id}")
    meta = adapter.get_task_metadata(task_id)
    workspace = executor.prepare_repository(meta["repository"], meta["base_commit"])
    
    venv_dir = os.path.join(workspace, "venv")
    subprocess.run(["python", "-m", "venv", venv_dir], check=True)
    pip_exe = os.path.join(venv_dir, "Scripts", "pip") if os.name == "nt" else os.path.join(venv_dir, "bin", "pip")
    python_exe = os.path.join(venv_dir, "Scripts", "python") if os.name == "nt" else os.path.join(venv_dir, "bin", "python")
    
    print("Installing Pytest...")
    subprocess.run([pip_exe, "install", "-e", "."], cwd=workspace, check=True, capture_output=True)
    
    print("Running a simple import test...")
    res = subprocess.run([python_exe, "-c", "import pytest; print(f'Pytest version: {pytest.__version__}')"], cwd=workspace, capture_output=True, text=True)
    print(res.stdout.strip())
    assert res.returncode == 0
    print("Pytest environment verified!")
    
    # 2. Django
    task_id = "django__django-16816"
    print(f"\nVerifying environment for {task_id}")
    meta = adapter.get_task_metadata(task_id)
    workspace = executor.prepare_repository(meta["repository"], meta["base_commit"])
    
    venv_dir = os.path.join(workspace, "venv")
    subprocess.run(["python", "-m", "venv", venv_dir], check=True)
    pip_exe = os.path.join(venv_dir, "Scripts", "pip") if os.name == "nt" else os.path.join(venv_dir, "bin", "pip")
    python_exe = os.path.join(venv_dir, "Scripts", "python") if os.name == "nt" else os.path.join(venv_dir, "bin", "python")
    
    print("Installing Django...")
    subprocess.run([pip_exe, "install", "-e", "."], cwd=workspace, check=True, capture_output=True)
    
    print("Running a simple import test...")
    res = subprocess.run([python_exe, "-c", "import django; print(f'Django version: {django.__version__}')"], cwd=workspace, capture_output=True, text=True)
    print(res.stdout.strip())
    assert res.returncode == 0
    print("Django environment verified!")

if __name__ == '__main__':
    test_environments()
