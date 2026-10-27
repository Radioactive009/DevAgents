import os
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from deployment.models import (
    DeploymentStage,
    DeploymentRecord,
    GitHubRepoInfo,
    CIWorkflowInfo,
    VercelDeploymentInfo,
    HealthCheckResult
)
from deployment.github_service import GitHubPublishingService, GitHubPublishingError
from deployment.ci_service import CIService
from deployment.vercel_service import VercelService, VercelIntegrationError
from deployment.health_service import HealthCheckService
from deployment.manager import DeploymentManager

# =====================================================================
# 1. GITHUB SERVICE TESTS
# =====================================================================

def test_github_auth_check_success():
    def mock_runner(cmd):
        if "gh auth status" in cmd:
            return 0, "Logged in to github.com as Radioactive009 (keyring)\n✓ Token: gho_****", ""
        return 0, "", ""
    
    gh = GitHubPublishingService(command_runner=mock_runner)
    auth = gh.check_auth()
    assert auth["authenticated"] is True
    assert auth["user"] == "Radioactive009"
    assert "gho_****" not in auth["user"]

def test_github_auth_check_failure():
    def mock_runner(cmd):
        return 1, "", "You are not logged into any GitHub hosts."
    
    gh = GitHubPublishingService(command_runner=mock_runner)
    auth = gh.check_auth()
    assert auth["authenticated"] is False
    assert "not authenticated" in auth["message"]

def test_github_repo_naming_and_collision_handling():
    gh = GitHubPublishingService()
    # Normalize special characters and length
    normalized = gh.normalize_repo_name("My Super App! (v2.0) & More", "run-12345678")
    assert normalized.startswith("devagents-my-super-app-v20-more")
    assert normalized.endswith("-12345678")
    # Empty name fallback
    fallback = gh.normalize_repo_name("", "run-abcdef12")
    assert fallback == "devagents-app-abcdef12"

def test_github_secret_exclusion():
    gh = GitHubPublishingService()
    files = {
        "index.html": "<h1>App</h1>",
        "src/app.js": "console.log('test')",
        ".env": "SECRET_KEY=12345",
        ".env.local": "TOKEN=abc",
        "id_rsa": "-----BEGIN RSA PRIVATE KEY-----",
        "key.pem": "private",
        "local.db": "binary database data"
    }
    filtered, excluded = gh.filter_sensitive_files(files)
    assert "index.html" in filtered
    assert "src/app.js" in filtered
    assert ".env" not in filtered
    assert ".env.local" not in filtered
    assert "id_rsa" not in filtered
    assert "key.pem" not in filtered
    assert "local.db" not in filtered
    assert len(excluded) == 5

def test_github_publish_project_private_by_default(tmp_path):
    commands_run = []
    def mock_runner(cmd):
        commands_run.append(cmd)
        if "gh auth status" in cmd:
            return 0, "Logged in to github.com as Radioactive009", ""
        if "git rev-parse" in cmd:
            return 0, "mock-commit-sha-abcdef", ""
        return 0, "", ""
    
    gh = GitHubPublishingService(
        workspace_dir=str(tmp_path),
        command_runner=mock_runner
    )
    
    files = {"index.html": "<h1>Test App</h1>"}
    info = gh.publish_project(
        run_id="run-1234",
        project_name="Test Widget",
        files=files,
        is_private=True,
        ci_workflow_content="name: CI\non: push\njobs: {}"
    )
    
    assert info.is_private is True
    assert info.owner == "Radioactive009"
    assert info.repo_url == f"https://github.com/Radioactive009/{info.repo_name}"
    assert info.commit_sha == "mock-commit-sha-abcdef"
    
    # Verify --private flag was passed to gh repo create
    create_cmds = [c for c in commands_run if "gh repo create" in c]
    assert len(create_cmds) == 1
    assert "--private" in create_cmds[0]

def test_github_publish_fails_cleanly_on_git_error(tmp_path):
    def mock_runner(cmd):
        if "gh auth status" in cmd:
            return 0, "Logged in", ""
        if "gh repo create" in cmd:
            return 1, "", "fatal: repository creation failed: name already exists"
        return 0, "", ""
    
    gh = GitHubPublishingService(
        workspace_dir=str(tmp_path),
        command_runner=mock_runner
    )
    
    with pytest.raises(GitHubPublishingError) as exc_info:
        gh.publish_project("run-1234", "App", {"index.html": "<h1>Hi</h1>"})
    assert "GitHub repository creation failed" in str(exc_info.value)

# =====================================================================
# 2. CI SERVICE TESTS
# =====================================================================

def test_ci_detect_project_types():
    ci = CIService()
    
    # Next.js detection
    next_files = {"package.json": '{"dependencies": {"next": "14.0.0"}}'}
    info = ci.detect_project_type(next_files)
    assert info["type"] == "nextjs"
    assert info["framework_preset"] == "nextjs"
    
    # Vite detection
    vite_files = {"package.json": '{"devDependencies": {"vite": "5.0.0"}}'}
    info = ci.detect_project_type(vite_files)
    assert info["type"] == "vite"
    assert info["framework_preset"] == "vite"
    
    # Python detection
    py_files = {"requirements.txt": "fastapi\nuvicorn\npytest"}
    info = ci.detect_project_type(py_files)
    assert info["type"] == "python"
    assert info["framework_preset"] is None
    
    # Static HTML
    html_files = {"index.html": "<h1>Test</h1>", "style.css": "body { color: red; }"}
    info = ci.detect_project_type(html_files)
    assert info["type"] == "static_html"
    assert info["framework_preset"] is None

def test_ci_workflow_generation_structure():
    ci = CIService()
    files = {
        "package.json": '{"scripts": {"test": "jest", "build": "vite build"}}',
        "src/App.tsx": "export default () => <div>App</div>"
    }
    workflow = ci.generate_ci_workflow(files, project_name="my-frontend")
    
    # Check least privilege permissions
    assert "permissions:\n  contents: read" in workflow
    # Check trigger rules
    assert "on:\n  push:" in workflow
    assert "pull_request:" in workflow
    # Check steps
    assert "actions/checkout@v4" in workflow
    assert "actions/setup-node@v4" in workflow
    assert "npm run test" in workflow
    assert "npm run build" in workflow

def test_ci_workflow_python_structure():
    ci = CIService()
    files = {"requirements.txt": "pytest\nrequests"}
    workflow = ci.generate_ci_workflow(files, project_name="my-backend")
    assert "actions/setup-python@v5" in workflow
    assert "pip install" in workflow
    assert "pytest" in workflow

# =====================================================================
# 3. VERCEL SERVICE TESTS
# =====================================================================

def test_vercel_auth_missing_token():
    vc = VercelService(token=None)
    auth = vc.check_auth()
    assert auth["authenticated"] is False
    assert "VERCEL_TOKEN is not configured" in auth["message"]

def test_vercel_auth_valid_token():
    def mock_request(method, endpoint, **kwargs):
        if endpoint == "/v2/user":
            return {"user": {"username": "testdev", "id": "usr_123"}}
        return {}
    
    vc = VercelService(token="secret-token-1234", request_fn=mock_request)
    auth = vc.check_auth()
    assert auth["authenticated"] is True
    assert auth["username"] == "testdev"

def test_vercel_auth_invalid_token():
    def mock_request(method, endpoint, **kwargs):
        raise VercelIntegrationError("Invalid token or unauthorized")
    
    vc = VercelService(token="bad-token", request_fn=mock_request)
    auth = vc.check_auth()
    assert auth["authenticated"] is False
    assert "Unauthorized" in auth["message"]

def test_vercel_get_or_create_project():
    created = False
    def mock_request(method, endpoint, **kwargs):
        nonlocal created
        if method == "GET" and "/v9/projects/my-app" in endpoint:
            if not created:
                raise VercelIntegrationError("Project not found (HTTP 404)")
            return {"id": "prj_999", "name": "my-app"}
        if method == "POST" and "/v9/projects" in endpoint:
            created = True
            return {"id": "prj_999", "name": "my-app"}
        return {}
        
    vc = VercelService(token="valid_token", request_fn=mock_request)
    res = vc.get_or_create_project("my-app", framework_preset="vite")
    assert res["id"] == "prj_999"
    assert res["name"] == "my-app"

def test_vercel_create_and_wait_deployment():
    def mock_request(method, endpoint, **kwargs):
        if method == "POST" and "/v13/deployments" in endpoint:
            return {
                "id": "dpl_abc123",
                "url": "my-app-preview.vercel.app",
                "readyState": "BUILDING"
            }
        if method == "GET" and "/v13/deployments/dpl_abc123" in endpoint:
            return {
                "id": "dpl_abc123",
                "url": "my-app-preview.vercel.app",
                "readyState": "READY",
                "meta": {}
            }
        return {}
        
    vc = VercelService(token="valid_token", request_fn=mock_request)
    dep = vc.create_deployment(
        project_name="my-app",
        files={"index.html": "<h1>Vercel Live</h1>"}
    )
    assert dep.deployment_id == "dpl_abc123"
    assert dep.state == "BUILDING"
    
    final_dep = vc.wait_for_deployment(dep.deployment_id, timeout_seconds=5, poll_interval_seconds=0.1)
    assert final_dep.state == "READY"
    assert final_dep.deployment_url == "https://my-app-preview.vercel.app"

# =====================================================================
# 4. HEALTH CHECK SERVICE TESTS
# =====================================================================

def test_health_check_success():
    def mock_fetch(url):
        return 200, "<html><body><h1>Markdown Editor</h1></body></html>"
        
    hc = HealthCheckService(fetch_fn=mock_fetch)
    res = hc.verify_deployment_health("https://my-app.vercel.app", expected_content="Markdown Editor")
    assert res.is_healthy is True
    assert res.status_code == 200
    assert res.content_verified is True
    assert res.latency_ms > 0

def test_health_check_http_500_failure():
    def mock_fetch(url):
        return 500, "Internal Server Error"
        
    hc = HealthCheckService(fetch_fn=mock_fetch)
    res = hc.verify_deployment_health("https://my-app.vercel.app", max_retries=1, retry_delay_seconds=0.01)
    assert res.is_healthy is False
    assert res.status_code == 500

def test_health_check_content_mismatch_failure():
    def mock_fetch(url):
        return 200, "Default blank page"
        
    hc = HealthCheckService(fetch_fn=mock_fetch)
    res = hc.verify_deployment_health("https://my-app.vercel.app", expected_content="Missing Expected Header", max_retries=1)
    assert res.is_healthy is False
    assert res.status_code == 200
    assert "content did not contain" in res.error_message

# =====================================================================
# 5. DEPLOYMENT MANAGER & LIFECYCLE TESTS
# =====================================================================

def test_deployment_manager_mock_pipeline_e2e(tmp_path):
    mgr = DeploymentManager(storage_dir=str(tmp_path))
    files = {
        "index.html": "<!DOCTYPE html><html><body><h1>Task App</h1></body></html>",
        "style.css": "body { margin: 0; }"
    }
    
    record = mgr.deploy_run(
        run_id="run-test1234",
        project_name="Task App",
        files=files,
        is_private=True,
        use_mock=True
    )
    
    assert record.stage == DeploymentStage.HEALTH_CHECK_PASSED
    assert record.github is not None
    assert record.github.is_private is True
    assert record.github.repo_name.startswith("devagents-task-app")
    assert record.ci is not None
    assert record.vercel is not None
    assert record.vercel.state == "READY"
    assert record.health_check is not None
    assert record.health_check.is_healthy is True
    assert len(record.history) >= 5
    
    # Verify persistence
    loaded = mgr.get_deployment_record("run-test1234")
    assert loaded is not None
    assert loaded.stage == DeploymentStage.HEALTH_CHECK_PASSED
    assert loaded.github.repo_url == record.github.repo_url

def test_deployment_manager_idempotency_prevents_duplicate_repo(tmp_path):
    mgr = DeploymentManager(storage_dir=str(tmp_path))
    files = {"index.html": "<h1>Test</h1>"}
    
    # Pass 1
    r1 = mgr.deploy_run("run-idem1", "IdemApp", files, use_mock=True)
    initial_repo = r1.github.repo_url
    
    # Pass 2 (Retry)
    r2 = mgr.deploy_run("run-idem1", "IdemApp", files, use_mock=True)
    assert r2.retry_count == 2
    # Should maintain the same repository URL rather than re-creating duplicate
    assert r2.github.repo_url == initial_repo

# =====================================================================
# 6. FASTAPI API ENDPOINTS TESTS
# =====================================================================

def test_api_deployment_endpoints(tmp_path):
    from fastapi.testclient import TestClient
    from api.main import app, active_runs_state
    from orchestration.state import ProjectState, GeneratedProject, FileContent
    
    client = TestClient(app)
    
    # 1. Test /api/deployment/config
    res = client.get("/api/deployment/config")
    assert res.status_code == 200
    config_data = res.json()
    assert "github" in config_data
    assert "vercel" in config_data
    # Check that secrets are NEVER leaked in config responses
    assert "token" not in config_data.get("vercel", {})
    
    # 2. Setup mock run with files
    run_id = "run-api-test"
    state = ProjectState(run_id=run_id, user_requirement="Build a counter app")
    state.generated_project = GeneratedProject(
        files=[
            FileContent(path="index.html", content="<h1>Counter</h1>"),
            FileContent(path="app.js", content="let count = 0;")
        ],
        dependencies=[]
    )
    active_runs_state[run_id] = state
    
    # 3. Test /api/runs/{run_id}/deploy with mock=True
    deploy_res = client.post(f"/api/runs/{run_id}/deploy", json={"use_mock": True, "is_private": True})
    assert deploy_res.status_code == 200
    assert deploy_res.json()["status"] == "DEPLOYMENT_STARTED"
    
    # Allow background thread to finish
    import time
    time.sleep(0.5)
    
    # 4. Test /api/runs/{run_id}/deployment
    status_res = client.get(f"/api/runs/{run_id}/deployment")
    assert status_res.status_code == 200
    stat_data = status_res.json()
    assert stat_data["status"] in ["HEALTH_CHECK_PASSED", "DEPLOYMENT_READY", "GITHUB_PUBLISHED"]
    assert stat_data["record"]["github"]["is_private"] is True
