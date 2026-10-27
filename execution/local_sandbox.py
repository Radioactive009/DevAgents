import os
import uuid
import time
import shutil
import tempfile
import subprocess
import sys
from typing import List, Dict, Optional, Any
from .sandbox import Sandbox
from .models import ExecutionResult
from .exceptions import SandboxConfigurationError

class LocalProcessSandbox(Sandbox):
    """Fallback local filesystem & subprocess sandbox when Docker is unavailable."""
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.timeout_seconds = self.config.get("timeout_seconds", 30)
        self.network_enabled = self.config.get("network_enabled", False)
        self.sandbox_id = f"devagents-local-{uuid.uuid4()}"
        self.workspace_dir: Optional[str] = None

    def create_workspace(self) -> None:
        self.workspace_dir = tempfile.mkdtemp(prefix=self.sandbox_id)

    def write_file(self, filename: str, content: str) -> None:
        if not self.workspace_dir:
            raise SandboxConfigurationError("Workspace not created yet.")
        filepath = os.path.normpath(os.path.join(self.workspace_dir, filename))
        if not filepath.startswith(self.workspace_dir):
            raise SandboxConfigurationError("Attempted to write outside workspace")
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    def read_file(self, filename: str) -> str:
        if not self.workspace_dir:
            raise SandboxConfigurationError("Workspace not created yet.")
        filepath = os.path.normpath(os.path.join(self.workspace_dir, filename))
        if not filepath.startswith(self.workspace_dir):
            raise SandboxConfigurationError("Attempted to read outside workspace")
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    def run_command(self, command: List[str]) -> ExecutionResult:
        if not self.workspace_dir:
            raise SandboxConfigurationError("Workspace not created yet.")
        start_time = time.time()
        
        cmd = list(command)
        env = os.environ.copy()
        env["PYTHONPATH"] = self.workspace_dir

        # Handle 'env PYTHONPATH=...' prefix cleanly on Windows
        if len(cmd) >= 2 and cmd[0] == "env" and cmd[1].startswith("PYTHONPATH="):
            custom_path = cmd[1].split("=", 1)[1]
            env["PYTHONPATH"] = f"{custom_path}{os.pathsep}{self.workspace_dir}"
            cmd = cmd[2:]

        # Replace 'python' or 'pytest' with sys.executable if needed
        if cmd and cmd[0] == "python":
            cmd[0] = sys.executable
        elif cmd and cmd[0] == "pytest":
            cmd = [sys.executable, "-m", "pytest"] + cmd[1:]
        elif cmd and not os.path.isabs(cmd[0]):
            resolved = shutil.which(cmd[0])
            if resolved:
                cmd[0] = resolved

        try:
            res = subprocess.run(
                cmd,
                cwd=self.workspace_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )
            success = (res.returncode == 0)
            failure_cat = "SUCCESS" if success else "NONZERO_EXIT"
            return ExecutionResult(
                success=success,
                exit_code=res.returncode,
                stdout=res.stdout,
                stderr=res.stderr,
                command=" ".join(command),
                duration=time.time() - start_time,
                timed_out=False,
                sandbox_id=self.sandbox_id,
                failure_category=failure_cat
            )
        except subprocess.TimeoutExpired as e:
            stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout.decode("utf-8", "replace") if e.stdout else "")
            stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr.decode("utf-8", "replace") if e.stderr else "")
            return ExecutionResult(
                success=False,
                exit_code=None,
                stdout=stdout,
                stderr=stderr,
                command=" ".join(command),
                duration=time.time() - start_time,
                timed_out=True,
                sandbox_id=self.sandbox_id,
                failure_category="TIMEOUT"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                command=" ".join(command),
                duration=time.time() - start_time,
                timed_out=False,
                sandbox_id=self.sandbox_id,
                failure_category="EXECUTION_ERROR"
            )

    def run_tests(self, test_command: List[str] = ["python", "-m", "pytest"]) -> ExecutionResult:
        return self.run_command(test_command)

    def cleanup(self) -> None:
        if self.workspace_dir and os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir, ignore_errors=True)
