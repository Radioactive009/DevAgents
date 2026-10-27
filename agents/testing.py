import os
import re
import shlex
from typing import Dict, Any, Optional

from agents.base import Agent
from agents.models import AgentResult
from orchestration.state import ProjectState
from agents.schema import TestResult, GeneratedProject
from execution.docker_sandbox import DockerSandbox, check_docker_available, SandboxConfigurationError
from execution.local_sandbox import LocalProcessSandbox

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
            elif check_docker_available():
                sandbox = DockerSandbox(self.sandbox_config)
                sandbox.create_workspace()
                state.sandbox = sandbox
            else:
                sandbox = LocalProcessSandbox(self.sandbox_config)
                sandbox.create_workspace()
                state.sandbox = sandbox
            
            # 1. Write files safely
            for f in project.files:
                path = f.path
                if os.path.isabs(path) or path.startswith("/") or path.startswith("\\") or ".." in path:
                    raise SandboxConfigurationError(f"Unsafe path detected: {path}")
                sandbox.write_file(path, f.content)
            
            # 2. Install dependencies (if allowed and needed)
            allow_network = self.sandbox_config.get("allow_network_for_dependencies", False)
            deps_installed = False
            is_local = isinstance(sandbox, LocalProcessSandbox)
            deps_target = os.path.join(sandbox.workspace_dir, ".deps") if is_local else "/app/.deps"
            file_paths = [f.path for f in project.files]
            has_package_json = "package.json" in file_paths
            has_python_deps = "requirements.txt" in file_paths or (bool(project.dependencies) and not has_package_json)

            # 2a. Node.js dependencies
            if has_package_json and (allow_network or not is_local):
                original_network = sandbox.network_enabled
                sandbox.network_enabled = allow_network
                npm_cmd = ["npm", "install"]
                dep_res = sandbox.run_command(npm_cmd)
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
                        error_message="Failed to install npm dependencies"
                    )
                deps_installed = True

            # 2b. Python dependencies
            elif has_python_deps and (allow_network or not is_local):
                original_network = sandbox.network_enabled
                sandbox.network_enabled = allow_network
                
                req_cmd = ["python", "-m", "pip", "install", "--target", deps_target]
                if "requirements.txt" in file_paths:
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
                deps_installed = True

            # 3. Run tests
            test_cmd_raw = (project.test_command or "").strip()
            code_match = re.search(r'`+([^`\n]+)`+', test_cmd_raw)
            if code_match:
                test_cmd_raw = code_match.group(1).strip()
            elif "\n" in test_cmd_raw:
                for line in test_cmd_raw.splitlines():
                    cleaned_line = line.strip().strip("`").strip()
                    if any(cleaned_line.startswith(p) for p in ["node", "python", "py", "pytest", "npm", "npx"]):
                        test_cmd_raw = cleaned_line
                        break
                else:
                    test_cmd_raw = test_cmd_raw.splitlines()[0].strip()

            test_cmd = shlex.split(test_cmd_raw) if test_cmd_raw else ["python", "-m", "pytest"]
            if deps_installed and not has_package_json:
                sandbox.network_enabled = False # disable network during test execution for isolation
                test_cmd = ["env", f"PYTHONPATH={deps_target}"] + test_cmd
                    
            run_res = sandbox.run_tests(test_cmd)
            
            # 4. Parse results
            status = "PASSED" if run_res.success else "FAILED"
            if run_res.timed_out:
                status = "TIMEOUT"
            elif run_res.exit_code is None or run_res.exit_code < 0:
                status = "ERROR"
                
            stdout = self._sanitize(run_res.stdout)
            stderr = self._sanitize(run_res.stderr)
            full_out = stdout + "\n" + stderr
            
            parsed_metrics = self._parse_pytest_output(full_out)
            if not parsed_metrics:
                parsed_metrics = self._parse_jest_output(full_out)
            if not parsed_metrics:
                parsed_metrics = {}
                
            if run_res.success and not parsed_metrics.get("passed"):
                parsed_metrics["total"] = parsed_metrics.get("total") or 1
                parsed_metrics["passed"] = parsed_metrics.get("passed") or 1
                parsed_metrics["failed"] = 0
            
            # Identify test framework
            cmd_lower = " ".join(test_cmd).lower()
            if "jest" in cmd_lower:
                detected_framework = "jest"
            elif "vitest" in cmd_lower:
                detected_framework = "vitest"
            elif "npm" in cmd_lower:
                detected_framework = "npm-test"
            elif "pytest" in cmd_lower:
                detected_framework = "pytest"
            else:
                detected_framework = "custom"

            # Classify failure using Phase 10 taxonomy engine if test failed
            failure_cat = run_res.failure_category
            if not run_res.success:
                from evaluation.failure_classifier import classify_failure
                classified = classify_failure(full_out, run_res.exit_code)
                failure_cat = classified["category"]
                state.metadata["failure_classification"] = classified

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
                failure_category=failure_cat,
                sandbox_id=sandbox.sandbox_id,
                test_framework=detected_framework,
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
            err_result = TestResult(
                success=False,
                status="ERROR",
                command=getattr(project, "test_command", "unknown"),
                exit_code=None,
                stdout="",
                stderr=str(e),
                duration=0.0,
                timed_out=False,
                failure_category="SANDBOX_ERROR",
                sandbox_id=getattr(sandbox, "sandbox_id", None),
                project_name=getattr(project, "project_name", "unknown")
            )
            state.test_result = err_result
            return self._create_result(
                success=False,
                run_id=state.run_id,
                output=err_result,
                raw_response_available=False,
                error_category="SANDBOX_ERROR",
                error_message=str(e)
            )
        except Exception as e:
            err_result = TestResult(
                success=False,
                status="ERROR",
                command=getattr(project, "test_command", "unknown"),
                exit_code=None,
                stdout="",
                stderr=str(e),
                duration=0.0,
                timed_out=False,
                failure_category="EXECUTION_ERROR",
                sandbox_id=getattr(sandbox, "sandbox_id", None),
                project_name=getattr(project, "project_name", "unknown")
            )
            state.test_result = err_result
            return self._create_result(
                success=False,
                run_id=state.run_id,
                output=err_result,
                raw_response_available=False,
                error_category="EXECUTION_ERROR",
                error_message=str(e)
            )
        finally:
            if sandbox:
                sandbox.cleanup()

    def _sanitize(self, text: str) -> str:
        """Sanitize secrets and API keys from logs and output."""
        if not text:
            return text
        keys_to_hide = []
        for env_var, val in os.environ.items():
            if ("KEY" in env_var.upper() or "TOKEN" in env_var.upper() or "SECRET" in env_var.upper()) and val and len(val) >= 6:
                keys_to_hide.append(val)
            
        for key in keys_to_hide:
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

    def _parse_jest_output(self, text: str) -> Dict[str, int]:
        """Parse Jest / Vitest / Node test output."""
        metrics = {}
        # Jest: Tests:       1 failed, 4 passed, 5 total
        match = re.search(r'Tests:\s+(.*)', text)
        if match:
            line = match.group(1)
            for part in line.split(','):
                part = part.strip()
                if 'passed' in part:
                    m = re.search(r'(\d+)\s+passed', part)
                    if m: metrics['passed'] = int(m.group(1))
                elif 'failed' in part:
                    m = re.search(r'(\d+)\s+failed', part)
                    if m: metrics['failed'] = int(m.group(1))
                elif 'skipped' in part or 'pending' in part:
                    m = re.search(r'(\d+)\s+(?:skipped|pending)', part)
                    if m: metrics['skipped'] = int(m.group(1))
                elif 'total' in part:
                    m = re.search(r'(\d+)\s+total', part)
                    if m: metrics['total'] = int(m.group(1))
            if 'total' not in metrics and (metrics.get('passed') or metrics.get('failed')):
                metrics['total'] = (metrics.get('passed', 0) + metrics.get('failed', 0) + metrics.get('skipped', 0))

        # Vitest: Tests  1 failed | 4 passed (5)
        if not metrics:
            match = re.search(r'Tests\s+(.*?)(?:\n|$)', text)
            if match:
                line = match.group(1)
                for part in line.split('|'):
                    part = part.strip()
                    if 'passed' in part:
                        m = re.search(r'(\d+)\s+passed', part)
                        if m: metrics['passed'] = int(m.group(1))
                    elif 'failed' in part:
                        m = re.search(r'(\d+)\s+failed', part)
                        if m: metrics['failed'] = int(m.group(1))
                m_tot = re.search(r'\((\d+)\)', line)
                if m_tot:
                    metrics['total'] = int(m_tot.group(1))
                elif 'passed' in metrics or 'failed' in metrics:
                    metrics['total'] = metrics.get('passed', 0) + metrics.get('failed', 0)
        return metrics
