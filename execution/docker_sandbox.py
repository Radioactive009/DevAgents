import os
import uuid
import time
import shutil
import tempfile
import shlex
from typing import List, Dict, Optional, Any
from .sandbox import Sandbox
from .models import ExecutionResult
from .exceptions import DockerUnavailableError, SandboxConfigurationError

try:
    import docker
    from docker.errors import DockerException, ContainerError, APIError, ImageNotFound
except ImportError:
    docker = None

def check_docker_available() -> bool:
    if docker is None:
        return False
    try:
        client = docker.from_env()
        client.ping()
        
        # Test if credential helper is missing by listing images, though pull is the real test.
        # But if docker is not in PATH, we can't pull.
        import shutil
        if not shutil.which("docker"):
            print("Docker CLI not in PATH, credential helper will fail.")
            return False
            
        return True
    except Exception:
        return False

class DockerSandbox(Sandbox):
    def __init__(self, config: Dict[str, Any]):
        if not check_docker_available():
            raise DockerUnavailableError("Docker is not installed or daemon is not accessible.")
            
        self.client = docker.from_env()
        self.image = config.get("image", "python:3.11-slim")
        self.timeout_seconds = config.get("timeout_seconds", 30)
        self.memory_limit = config.get("memory_limit_mb", 512)
        self.cpu_limit = config.get("cpu_limit", 1.0)
        self.network_enabled = config.get("network_enabled", False)
        
        self.sandbox_id = f"devagents-run-{uuid.uuid4()}"
        self.workspace_dir = None
        self.container = None

    def create_workspace(self) -> None:
        # Create a temporary directory on the host to mount into the container
        self.workspace_dir = tempfile.mkdtemp(prefix=self.sandbox_id)

    def write_file(self, filename: str, content: str) -> None:
        if not self.workspace_dir:
            raise SandboxConfigurationError("Workspace not created yet.")
            
        # Prevent writing outside workspace
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
        cmd_str = shlex.join(command)
        
        try:
            container_args = {
                "image": self.image,
                "command": command,
                "volumes": {self.workspace_dir: {'bind': '/app', 'mode': 'rw'}},
                "working_dir": "/app",
                "mem_limit": f"{self.memory_limit}m",
                "nano_cpus": int(self.cpu_limit * 1e9),
                "network_mode": "bridge" if self.network_enabled else "none",
                "environment": {},  # Empty environment variables!
                "detach": True
            }
            
            try:
                self.container = self.client.containers.run(**container_args)
            except ImageNotFound:
                return self._create_result(False, cmd_str, start_time, 1, "", "Image not found", "IMAGE_ERROR")
                
            try:
                result = self.container.wait(timeout=self.timeout_seconds)
                exit_code = result.get("StatusCode", -1)
                stdout = self.container.logs(stdout=True, stderr=False).decode('utf-8', errors='replace')
                stderr = self.container.logs(stdout=False, stderr=True).decode('utf-8', errors='replace')
                
                success = (exit_code == 0)
                failure_category = "NONZERO_EXIT" if not success else "SUCCESS"
                return self._create_result(success, cmd_str, start_time, exit_code, stdout, stderr, failure_category)
                
            except Exception as e: # Catch wait timeout wrapper (docker uses requests exceptions for timeout sometimes)
                from requests.exceptions import ReadTimeout
                if isinstance(e, ReadTimeout) or "timeout" in str(e).lower() or "timed out" in str(e).lower():
                    self.container.stop(timeout=1)
                    return self._create_result(False, cmd_str, start_time, None, "", "Execution timed out", "TIMEOUT", timed_out=True)
                raise
                
        except Exception as e:
            # Fallback for unexpected docker errors
            return self._create_result(False, cmd_str, start_time, -1, "", str(e), "DOCKER_ERROR")
        finally:
            if self.container:
                try:
                    self.container.remove(force=True)
                except Exception:
                    pass
                self.container = None

    def _create_result(self, success, command, start_time, exit_code, stdout, stderr, failure_category, timed_out=False):
        return ExecutionResult(
            success=success,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            command=command,
            duration=time.time() - start_time,
            timed_out=timed_out,
            sandbox_id=self.sandbox_id,
            failure_category=failure_category
        )

    def run_tests(self, test_command: List[str] = ["python", "-m", "pytest"]) -> ExecutionResult:
        return self.run_command(test_command)

    def cleanup(self) -> None:
        if self.container:
            try:
                self.container.remove(force=True)
            except Exception:
                pass
            self.container = None
            
        if self.workspace_dir and os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir, ignore_errors=True)
