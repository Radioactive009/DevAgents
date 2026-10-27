import os
import pytest
from unittest.mock import patch

from deployment.models import DeploymentStage
from deployment.github_service import GitHubPublishingService, GitHubPublishingError
from deployment.ci_service import CIService
from deployment.vercel_service import VercelService, VercelIntegrationError
from deployment.health_service import HealthCheckService
from deployment.manager import DeploymentManager

def test_deeply_nested_secret_exclusion():
    gh = GitHubPublishingService()
    files = {
        "src/components/App.tsx": "const a = 1;",
        "src/config/.env.production": "SECRET=123",
        "keys/ssl/server.pem": "-----BEGIN CERTIFICATE-----",
        "keys/id_rsa_backup": "private_key",
        "data/app.sqlite3": "binary",
        "public/robots.txt": "User-agent: *"
    }
    allowed, excluded = gh.filter_sensitive_files(files)
    assert "src/components/App.tsx" in allowed
    assert "public/robots.txt" in allowed
    assert "src/config/.env.production" in excluded
    assert "keys/ssl/server.pem" in excluded
    assert "keys/id_rsa_backup" in excluded
    assert "data/app.sqlite3" in excluded
    assert len(excluded) == 4

def test_path_traversal_rejection_security(tmp_path):
    gh = GitHubPublishingService(command_runner=lambda cmd, **kw: (0, "", ""))
    files = {
        "../../etc/passwd": "root:x:0:0:",
        "normal.txt": "hello"
    }
    with pytest.raises(GitHubPublishingError) as exc_info:
        gh.publish_project("run-evil", "EvilProject", files)
    assert "Unsafe path traversal rejected" in str(exc_info.value)

def test_missing_vercel_token_halts_real_deployment_without_leaking(tmp_path):
    mock_gh = GitHubPublishingService(command_runner=lambda cmd, **kw: (0, "", ""))
    mgr = DeploymentManager(storage_dir=str(tmp_path), github_service=mock_gh)
    files = {"index.html": "<h1>Test</h1>"}
    
    # Pre-populate record with GitHub published so it advances to Vercel stage
    rec = mgr.deploy_run("run-notoken", "NoTokenApp", files, use_mock=True)
    # Now try real deployment without token
    with patch.dict(os.environ, {}, clear=True):
        record = mgr.deploy_run(
            run_id="run-notoken-real",
            project_name="NoTokenApp",
            files=files,
            use_mock=False
        )
    assert record.stage == DeploymentStage.DEPLOYMENT_FAILED
    # Either GitHub auth or Vercel auth is safely reported
    assert "not configured" in record.error or "unavailable" in record.error
    # Ensure no secrets or tokens leaked
    assert "Bearer" not in record.error
    assert "ghp_" not in record.error

def test_ci_workflow_has_secret_rejection_step():
    ci = CIService()
    files = {"index.html": "<h1>App</h1>"}
    workflow = ci.generate_ci_workflow(files, project_name="AuditApp")
    assert "Verify Secret Exclusion" in workflow
    assert "if [ -f .env ]; then" in workflow
    assert "exit 1" in workflow

def test_health_check_timeout_handling():
    def slow_request(url, timeout=10):
        # Simulate network timeout
        return 0, b"Connection timed out", 10000.0
        
    hc = HealthCheckService(request_fn=slow_request)
    res = hc.verify_deployment_health("https://slow.vercel.app", max_retries=2)
    assert res.is_healthy is False
    assert res.status_code == 0
    assert "timed out" in res.error_message
