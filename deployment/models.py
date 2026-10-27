import os
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

class DeploymentStage(str, Enum):
    NOT_DEPLOYED = "NOT_DEPLOYED"
    GITHUB_CREATING = "GITHUB_CREATING"
    GITHUB_PUSHING = "GITHUB_PUSHING"
    GITHUB_PUBLISHED = "GITHUB_PUBLISHED"
    CI_CONFIGURED = "CI_CONFIGURED"
    VERCEL_PROJECT_CREATING = "VERCEL_PROJECT_CREATING"
    DEPLOYMENT_PENDING = "DEPLOYMENT_PENDING"
    DEPLOYMENT_BUILDING = "DEPLOYMENT_BUILDING"
    DEPLOYMENT_READY = "DEPLOYMENT_READY"
    DEPLOYMENT_FAILED = "DEPLOYMENT_FAILED"
    HEALTH_CHECK_RUNNING = "HEALTH_CHECK_RUNNING"
    HEALTH_CHECK_PASSED = "HEALTH_CHECK_PASSED"
    HEALTH_CHECK_FAILED = "HEALTH_CHECK_FAILED"

@dataclass
class GitHubRepoInfo:
    repo_name: str
    repo_url: str
    owner: str
    is_private: bool = True
    default_branch: str = "main"
    commit_sha: Optional[str] = None
    repo_id: Optional[int] = None
    created_at: Optional[str] = None

@dataclass
class CIWorkflowInfo:
    workflow_file: str
    workflow_name: str
    ci_status: str = "CONFIGURED"  # CONFIGURED, RUNNING, PASSED, FAILED
    workflow_url: Optional[str] = None
    checks_summary: Optional[str] = None

@dataclass
class VercelDeploymentInfo:
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    deployment_id: Optional[str] = None
    deployment_url: Optional[str] = None
    production_url: Optional[str] = None
    state: str = "INITIALIZING"  # BUILDING, READY, ERROR, CANCELED
    framework_preset: Optional[str] = None
    build_logs: Optional[str] = None
    error_summary: Optional[str] = None

@dataclass
class HealthCheckResult:
    target_url: str
    status_code: Optional[int] = None
    is_healthy: bool = False
    latency_ms: Optional[float] = None
    content_verified: bool = False
    error_message: Optional[str] = None
    checked_at: Optional[str] = None

@dataclass
class DeploymentRecord:
    run_id: str
    project_name: str
    stage: DeploymentStage = DeploymentStage.NOT_DEPLOYED
    github: Optional[GitHubRepoInfo] = None
    ci: Optional[CIWorkflowInfo] = None
    vercel: Optional[VercelDeploymentInfo] = None
    health_check: Optional[HealthCheckResult] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeploymentRecord':
        github_data = data.get("github")
        ci_data = data.get("ci")
        vercel_data = data.get("vercel")
        health_data = data.get("health_check")

        stage_val = data.get("stage", DeploymentStage.NOT_DEPLOYED.value)
        try:
            stage_enum = DeploymentStage(stage_val)
        except ValueError:
            stage_enum = DeploymentStage.NOT_DEPLOYED

        return cls(
            run_id=data.get("run_id", ""),
            project_name=data.get("project_name", ""),
            stage=stage_enum,
            github=GitHubRepoInfo(**github_data) if github_data else None,
            ci=CIWorkflowInfo(**ci_data) if ci_data else None,
            vercel=VercelDeploymentInfo(**vercel_data) if vercel_data else None,
            health_check=HealthCheckResult(**health_data) if health_data else None,
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            history=data.get("history", [])
        )
