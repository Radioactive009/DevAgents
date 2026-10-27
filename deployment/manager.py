import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .models import (
    DeploymentStage,
    DeploymentRecord,
    GitHubRepoInfo,
    CIWorkflowInfo,
    VercelDeploymentInfo,
    HealthCheckResult
)
from .github_service import GitHubPublishingService, GitHubPublishingError
from .ci_service import CIService
from .vercel_service import VercelService, VercelIntegrationError
from .health_service import HealthCheckService

logger = logging.getLogger(__name__)

class DeploymentManager:
    def __init__(
        self,
        github_service: Optional[GitHubPublishingService] = None,
        vercel_service: Optional[VercelService] = None,
        ci_service: Optional[CIService] = None,
        health_service: Optional[HealthCheckService] = None,
        storage_dir: str = "logs/runs"
    ):
        self.github = github_service or GitHubPublishingService()
        self.vercel = vercel_service or VercelService()
        self.ci = ci_service or CIService()
        self.health = health_service or HealthCheckService()
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def _get_record_path(self, run_id: str) -> str:
        return os.path.join(self.storage_dir, f"{run_id}_deployment.json")

    def get_deployment_record(self, run_id: str) -> Optional[DeploymentRecord]:
        path = self._get_record_path(run_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return DeploymentRecord.from_dict(data)
            except Exception as e:
                logger.error(f"Error reading deployment record for {run_id}: {e}")
        return None

    def save_deployment_record(self, record: DeploymentRecord) -> None:
        record.updated_at = datetime.utcnow().isoformat()
        path = self._get_record_path(record.run_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, indent=2)

    def _record_stage(self, record: DeploymentRecord, stage: DeploymentStage, note: str = ""):
        record.stage = stage
        record.history.append({
            "stage": stage.value,
            "timestamp": datetime.utcnow().isoformat(),
            "note": note
        })
        self.save_deployment_record(record)

    def deploy_run(
        self,
        run_id: str,
        project_name: str,
        files: Dict[str, str],
        is_private: bool = True,
        use_mock: bool = False
    ) -> DeploymentRecord:
        """
        Execute full autonomous end-to-end DevOps pipeline:
        Files -> CI Workflow -> Private GitHub Repo -> Vercel Project -> Vercel Deployment -> Health Check.
        """
        record = self.get_deployment_record(run_id)
        if not record:
            record = DeploymentRecord(
                run_id=run_id,
                project_name=project_name,
                stage=DeploymentStage.NOT_DEPLOYED,
                created_at=datetime.utcnow().isoformat()
            )
        record.retry_count += 1
        record.error = None

        try:
            # --- STAGE 1: CI WORKFLOW GENERATION ---
            self._record_stage(record, DeploymentStage.CI_CONFIGURED, "Generating GitHub Actions CI workflow")
            ci_content = self.ci.generate_ci_workflow(files, project_name=project_name)
            record.ci = CIWorkflowInfo(
                workflow_file=".github/workflows/ci.yml",
                workflow_name="CI Pipeline & Quality Gate",
                ci_status="CONFIGURED"
            )

            # --- STAGE 2: GITHUB PUBLICATION ---
            if not record.github or not record.github.repo_url:
                self._record_stage(record, DeploymentStage.GITHUB_CREATING, "Creating private GitHub repository")
                
                if use_mock:
                    repo_name = self.github.normalize_repo_name(project_name, run_id)
                    record.github = GitHubRepoInfo(
                        repo_name=repo_name,
                        repo_url=f"https://github.com/mock-user/{repo_name}",
                        owner="mock-user",
                        is_private=is_private,
                        default_branch="main",
                        commit_sha="mock-commit-sha-001",
                        created_at=datetime.utcnow().isoformat()
                    )
                else:
                    self._record_stage(record, DeploymentStage.GITHUB_PUSHING, "Pushing code to GitHub repository")
                    github_info = self.github.publish_project(
                        run_id=run_id,
                        project_name=project_name,
                        files=files,
                        is_private=is_private,
                        ci_workflow_content=ci_content
                    )
                    record.github = github_info

            self._record_stage(record, DeploymentStage.GITHUB_PUBLISHED, f"Repository ready at {record.github.repo_url}")

            # --- STAGE 3: VERCEL PROJECT CREATION ---
            self._record_stage(record, DeploymentStage.VERCEL_PROJECT_CREATING, "Configuring Vercel project")
            project_type_info = self.ci.detect_project_type(files)
            framework_preset = project_type_info.get("framework_preset")
            
            vercel_project_name = self.github.normalize_repo_name(project_name, run_id)
            github_repo_slug = f"{record.github.owner}/{record.github.repo_name}"

            if use_mock:
                record.vercel = VercelDeploymentInfo(
                    project_id=f"prj_{run_id}",
                    project_name=vercel_project_name,
                    deployment_id=f"dpl_{run_id}",
                    deployment_url=f"https://{vercel_project_name}-preview.vercel.app",
                    production_url=f"https://{vercel_project_name}.vercel.app",
                    state="READY",
                    framework_preset=framework_preset
                )
            else:
                # Check Vercel token auth
                auth_info = self.vercel.check_auth()
                if not auth_info["authenticated"]:
                    raise VercelIntegrationError(auth_info["message"])

                # Create or get Vercel project
                prj_data = self.vercel.get_or_create_project(
                    project_name=vercel_project_name,
                    github_repo=github_repo_slug,
                    framework_preset=framework_preset
                )

                # --- STAGE 4: VERCEL DEPLOYMENT ---
                self._record_stage(record, DeploymentStage.DEPLOYMENT_BUILDING, "Deploying application bundle to Vercel")
                
                # Include CI workflow in uploaded files
                all_files = dict(files)
                all_files[".github/workflows/ci.yml"] = ci_content

                git_source = None
                repo_id = getattr(record.github, "repo_id", None)
                if not repo_id and record.github and record.github.owner and record.github.repo_name:
                    try:
                        code, out, _ = self.github._runner(["gh", "api", f"repos/{record.github.owner}/{record.github.repo_name}", "-q", ".id"])
                        if code == 0 and out.strip().isdigit():
                            repo_id = int(out.strip())
                            record.github.repo_id = repo_id
                    except Exception:
                        pass

                if repo_id:
                    git_source = {
                        "type": "github",
                        "repoId": repo_id,
                        "ref": getattr(record.github, "default_branch", "main") or "main"
                    }

                dep_info = self.vercel.create_deployment(
                    project_name=vercel_project_name,
                    files=all_files,
                    git_source=git_source
                )
                record.vercel = dep_info

                # Wait for deployment to finish building
                if dep_info.deployment_id:
                    self._record_stage(record, DeploymentStage.DEPLOYMENT_BUILDING, "Waiting for Vercel deployment to finish")
                    dep_ready = self.vercel.wait_for_deployment(dep_info.deployment_id, timeout_seconds=120)
                    record.vercel = dep_ready

                    if dep_ready.state != "READY":
                        raise VercelIntegrationError(dep_ready.error_summary or "Deployment failed to reach READY state")

            self._record_stage(record, DeploymentStage.DEPLOYMENT_READY, f"Deployed to {record.vercel.production_url or record.vercel.deployment_url}")

            # --- STAGE 5: POST-DEPLOYMENT HEALTH CHECK & SMOKE TEST ---
            target_url = record.vercel.production_url or record.vercel.deployment_url
            if target_url:
                self._record_stage(record, DeploymentStage.HEALTH_CHECK_RUNNING, f"Running smoke test against {target_url}")
                
                if use_mock:
                    record.health_check = HealthCheckResult(
                        target_url=target_url,
                        status_code=200,
                        is_healthy=True,
                        latency_ms=115.4,
                        content_verified=True,
                        checked_at=datetime.utcnow().isoformat()
                    )
                else:
                    health_res = self.health.verify_deployment_health(
                        deployment_url=target_url,
                        expected_content=None,
                        max_retries=3
                    )
                    record.health_check = health_res
                    if not health_res.is_healthy:
                        self._record_stage(record, DeploymentStage.HEALTH_CHECK_FAILED, health_res.error_message or "Health check failed")
                        return record

                self._record_stage(record, DeploymentStage.HEALTH_CHECK_PASSED, "Live smoke tests passed successfully!")

        except Exception as e:
            logger.error(f"DevOps pipeline error for {run_id}: {e}")
            record.error = str(e)
            record.stage = DeploymentStage.DEPLOYMENT_FAILED
            self.save_deployment_record(record)

        return record
