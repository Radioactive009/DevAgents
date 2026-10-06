import os
import re
import shlex
from typing import Dict, Any, Optional

from agents.base import Agent
from agents.models import AgentResult
from orchestration.state import ProjectState
from agents.schema import TestResult, GeneratedProject
from execution.docker_sandbox import DockerSandbox, SandboxConfigurationError

class TestingAgent(Agent):
    def __init__(self, provider, sandbox_config: Optional[Dict[str, Any]] = None):
        super().__init__("TestingAgent", "Testing", provider)
        self.sandbox_config = sandbox_config or {}

    def run(self, state: ProjectState) -> AgentResult:
        if not state.generated_project:
            return self._create_result(
                success=False,
                run_id=state.run_id,
                output=None,
                raw_response_available=False,
                error_category="MISSING_GENERATED_PROJECT",
                error_message="TestingAgent requires a valid generated_project in state."
            )
            
        project = state.generated_project
        if not project.test_command:
            return self._create_result(
                success=False,
                run_id=state.run_id,
                output=None,
                raw_response_available=False,
                error_category="NO_TEST_COMMAND",
                error_message="No test command provided in GeneratedProject."
            )

        sandbox = None
        try:
            if hasattr(state, "sandbox") and state.sandbox:
                sandbox = state.sandbox
            else:
                sandbox = DockerSandbox(self.sandbox_config)
                sandbox.create_workspace()
                state.sandbox = sandbox
            
            # 1. Write files safely
            for f in project.files:
                path = f.path
                if os.path.isabs(path) or path.startswith("/") or path.startswith("\\") or ".." in path:
                    raise SandboxConfigurationError(f"Unsafe path detected: {path}")
                sandbox.write_file(path, f.content)
            
            # 2. Install dependencies (if allowed)
            allow_network = self.sandbox_config.get("allow_network_for_dependencies", False)
            if project.dependencies or "requirements.txt" in [f.path for f in project.files]:
                original_network = sandbox.network_enabled
                sandbox.network_enabled = allow_network
                
                req_cmd = ["python", "-m", "pip", "install", "--target", "/app/.deps"]
                if "requirements.txt" in [f.path for f in project.files]:
                    req_cmd.extend(["-r", "requirements.txt"])
                else:
                    req_cmd.extend(project.dependencies)
                
                dep_res = sandbox.run_command(req_cmd)
                sandbox.network_enabled = original_network
                
                if not dep_res.success:
                    test_result = TestResult(
                        success=False,
                        status="DEPENDENCY_INSTALLATION_FAILED",
                        command=dep_res.command,
                        exit_code=dep_res.exit_code,
                        stdout=self._sanitize(dep_res.stdout),
                        stderr=self._sanitize(dep_res.stderr),
                        duration=dep_res.duration,
                        timed_out=dep_res.timed_out,
                        failure_category="DEPENDENCY_INSTALLATION_FAILED",
                        sandbox_id=sandbox.sandbox_id,
                        project_name=project.project_name
                    )
                    state.test_result = test_result
                    return self._create_result(
                        success=False,
                        run_id=state.run_id,
                        output=test_result,
                        raw_response_available=False,
                        error_category="DEPENDENCY_INSTALLATION_FAILED",
                        error_message="Failed to install dependencies"
                    )

            # 3. Run tests
            test_cmd_raw = project.test_command
            test_cmd = shlex.split(test_cmd_raw)
            if project.dependencies or "requirements.txt" in [f.path for f in project.files]:
                # If we installed deps to /app/.deps, we need to add it to PYTHONPATH
                sandbox.network_enabled = False # disable network during test execution for isolation
                
                # To ensure PYTHONPATH is evaluated in the container, we might need to wrap in a shell
                # But DockerSandbox just passes command array directly.
                # Let's prepend PYTHONPATH to the python execution if possible, or just rely on DockerSandbox environment
                # Actually, DockerSandbox doesn't let us pass environment variables right now!
                # Wait, we can run python -c "import sys, subprocess; sys.path.insert(0, '/app/.deps'); subprocess.run(...)"
                # A simpler way: we modify execution/docker_sandbox.py to accept environment variables?
                # For now, let's inject it into the command if it's a python command.
                if test_cmd[0] == "python":
                    test_cmd = ["env", "PYTHONPATH=/app/.deps"] + test_cmd
                else:
                    test_cmd = ["env", "PYTHONPATH=/app/.deps"] + test_cmd
                    
            run_res = sandbox.run_tests(test_cmd)
            
            # 4. Parse results
            status = "PASSED" if run_res.success else "FAILED"
            if run_res.timed_out:
                status = "TIMEOUT"
            elif run_res.exit_code is None or run_res.exit_code < 0:
                status = "ERROR"
                
            stdout = self._sanitize(run_res.stdout)
            stderr = self._sanitize(run_res.stderr)
            
            parsed_metrics = self._parse_pytest_output(stdout)
            
            test_result = TestResult(
                success=run_res.success,
                status=status,
                command=run_res.command,
                exit_code=run_res.exit_code,
                stdout=stdout,
                stderr=stderr,
                duration=run_res.duration,
                timed_out=run_res.timed_out,
                tests_total=parsed_metrics.get("total"),
                tests_passed=parsed_metrics.get("passed"),
                tests_failed=parsed_metrics.get("failed"),
                tests_skipped=parsed_metrics.get("skipped"),
                tests_errors=parsed_metrics.get("errors"),
                failure_category=run_res.failure_category,
                sandbox_id=sandbox.sandbox_id,
                test_framework="pytest" if "pytest" in test_cmd else "unknown",
                project_name=project.project_name,
                requirement_results=project.requirement_coverage
            )
            
            state.test_result = test_result
            
            return self._create_result(
                success=test_result.success,
                run_id=state.run_id,
                output=test_result,
                raw_response_available=False,
                error_category=run_res.failure_category if not run_res.success else None,
                error_message=None
            )
            
        except SandboxConfigurationError as e:
            return self._create_result(
                success=False,
                run_id=state.run_id,
                output=None,
                raw_response_available=False,
                error_category="SANDBOX_ERROR",
                error_message=str(e)
            )
        except Exception as e:
            return self._create_result(
                success=False,
                run_id=state.run_id,
                output=None,
                raw_response_available=False,
                error_category="SANDBOX_ERROR",
                error_message=str(e)
            )
        finally:
            if sandbox:
                sandbox.cleanup()

    def _sanitize(self, text: str) -> str:
        """Sanitize secrets from logs."""
        keys_to_hide = []
        if os.environ.get("GROQ_API_KEY"):
            keys_to_hide.append(os.environ["GROQ_API_KEY"])
        if os.environ.get("OPENROUTER_API_KEY"):
            keys_to_hide.append(os.environ["OPENROUTER_API_KEY"])
            
        for key in keys_to_hide:
            if key and len(key) > 5:
                text = text.replace(key, "***REDACTED***")
        return text
        
    def _parse_pytest_output(self, stdout: str) -> Dict[str, int]:
        """Simple deterministic parsing for pytest output."""
        metrics = {}
        # Example: ==== 1 failed, 2 passed, 1 skipped in 0.12s ====
        match = re.search(r'=+ (.*?) in ', stdout)
        if match:
            summary = match.group(1)
            for part in summary.split(','):
                part = part.strip()
                if 'passed' in part:
                    metrics['passed'] = int(part.split(' ')[0])
                elif 'failed' in part:
                    metrics['failed'] = int(part.split(' ')[0])
                elif 'skipped' in part:
                    metrics['skipped'] = int(part.split(' ')[0])
                elif 'error' in part:
                    metrics['errors'] = int(part.split(' ')[0])
            
            total = sum(metrics.values())
            if total > 0:
                metrics['total'] = total
        
        return metrics
