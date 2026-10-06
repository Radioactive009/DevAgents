import os
import subprocess
import tempfile
import uuid

class SWEBenchExecutionLayer:
    def __init__(self, work_dir_base: str = "tmp_workspaces"):
        self.work_dir_base = os.path.abspath(work_dir_base)
        os.makedirs(self.work_dir_base, exist_ok=True)

    def prepare_repository(self, repository: str, base_commit: str) -> str:
        workspace = os.path.join(self.work_dir_base, f"workspace_{uuid.uuid4().hex[:8]}")
        
        # Clone repo
        repo_url = f"https://github.com/{repository}.git"
        subprocess.run(["git", "clone", repo_url, workspace], check=True, capture_output=True)
        
        # Checkout base commit
        subprocess.run(["git", "checkout", base_commit], cwd=workspace, check=True, capture_output=True)
        
        # Verify HEAD
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=workspace, check=True, capture_output=True, text=True)
        if result.stdout.strip() != base_commit:
            raise RuntimeError("Base commit mismatch")
            
        return workspace

    def extract_patch(self, workspace: str, base_commit: str) -> str:
        # We assume git is tracking changes
        subprocess.run(["git", "add", "."], cwd=workspace, capture_output=True)
        result = subprocess.run(
            ["git", "diff", "--no-color", "--cached"],
            cwd=workspace,
            capture_output=True,
            text=True
        )
        return result.stdout
