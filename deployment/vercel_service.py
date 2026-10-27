import os
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List, Tuple
from .models import VercelDeploymentInfo

VERCEL_API_BASE = "https://api.vercel.com"

class VercelIntegrationError(Exception):
    pass

class VercelService:
    def __init__(self, token: Optional[str] = None, request_fn=None):
        """
        :param token: Optional explicit token. If omitted, loaded securely from VERCEL_TOKEN env var.
        :param request_fn: Optional callable(method, url, headers, data) -> (status_code, response_dict)
                           Used for dependency injection and deterministic unit testing.
        """
        if token is not None:
            self._token = token
        else:
            self._token = os.environ.get("VERCEL_TOKEN")
            if not self._token:
                try:
                    import dotenv
                    dotenv.load_dotenv(override=True)
                    self._token = os.environ.get("VERCEL_TOKEN")
                except Exception:
                    pass
        self._request_fn = request_fn or self._default_request_fn

    @staticmethod
    def _default_request_fn(
        method: str, 
        url: str, 
        headers: Dict[str, str], 
        data: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, Dict[str, Any]]:
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_bytes = resp.read()
                resp_data = json.loads(resp_bytes.decode("utf-8")) if resp_bytes else {}
                return resp.status, resp_data
        except urllib.error.HTTPError as e:
            err_bytes = e.read()
            err_data = {}
            try:
                err_data = json.loads(err_bytes.decode("utf-8")) if err_bytes else {}
            except Exception:
                err_data = {"error": {"message": err_bytes.decode("utf-8", errors="ignore")}}
            return e.code, err_data
        except Exception as e:
            return 500, {"error": {"message": str(e)}}

    def _get_auth_headers(self) -> Dict[str, str]:
        if not self._token:
            raise VercelIntegrationError(
                "VERCEL_TOKEN environment variable is not configured. "
                "Please configure VERCEL_TOKEN in your local .env to enable Vercel cloud deployments."
            )
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

    def check_auth(self) -> Dict[str, Any]:
        """Check Vercel token authentication without exposing the token."""
        if not self._token:
            return {
                "authenticated": False,
                "user": None,
                "message": "VERCEL_TOKEN is not configured in environment"
            }

        headers = {"Authorization": f"Bearer {self._token}"}
        status, data = self._request_fn("GET", f"{VERCEL_API_BASE}/v2/user", headers)
        if status == 200 and "user" in data:
            user_info = data["user"]
            username = user_info.get("username") or user_info.get("name") or "vercel-user"
            return {
                "authenticated": True,
                "user": username,
                "user_id": user_info.get("id"),
                "message": f"Authenticated with Vercel as {username}"
            }
        else:
            err_msg = data.get("error", {}).get("message", "Invalid or expired Vercel token")
            return {
                "authenticated": False,
                "user": None,
                "message": f"Vercel authentication failed ({status}): {err_msg}"
            }

    def get_or_create_project(
        self,
        project_name: str,
        github_repo: Optional[str] = None,
        framework_preset: Optional[str] = None,
        root_directory: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Idempotently get or create a Vercel project and link it to GitHub.
        :param github_repo: In 'owner/repo' format.
        """
        headers = self._get_auth_headers()
        
        # 1. Check if project already exists
        status, data = self._request_fn("GET", f"{VERCEL_API_BASE}/v9/projects/{project_name}", headers)
        if status == 200 and "id" in data:
            return data

        # 2. Create project
        payload: Dict[str, Any] = {
            "name": project_name
        }
        if framework_preset:
            payload["framework"] = framework_preset
        if root_directory:
            payload["rootDirectory"] = root_directory
        if github_repo:
            payload["gitRepository"] = {
                "type": "github",
                "repo": github_repo
            }

        c_status, c_data = self._request_fn("POST", f"{VERCEL_API_BASE}/v9/projects", headers, payload)
        if c_status in [200, 201]:
            return c_data
        
        err_msg = c_data.get("error", {}).get("message", f"Failed to create Vercel project with HTTP {c_status}")
        raise VercelIntegrationError(f"Vercel project creation error: {err_msg}")

    def create_deployment(
        self,
        project_name: str,
        files: Dict[str, str],
        git_source: Optional[Dict[str, str]] = None
    ) -> VercelDeploymentInfo:
        """
        Create a deployment on Vercel for the given project.
        Uses direct file deployment or git-backed deployment.
        """
        headers = self._get_auth_headers()

        # Format files for Vercel Deployments API v13
        # Vercel v13 allows uploading files directly: {"file": path, "data": content, "encoding": "utf-8"}
        vercel_files = []
        for path, content in files.items():
            norm_path = path.replace("\\", "/").strip("/")
            # Exclude prohibited files
            if norm_path.startswith(".env") and not norm_path.endswith(".example"):
                continue
            vercel_files.append({
                "file": norm_path,
                "data": content,
                "encoding": "utf-8"
            })

        payload: Dict[str, Any] = {
            "name": project_name,
            "project": project_name,
            "files": vercel_files,
            "target": "production"
        }
        if git_source and git_source.get("repoId"):
            try:
                repo_id_val = int(git_source["repoId"])
                payload["gitSource"] = {
                    "type": git_source.get("type", "github"),
                    "repoId": repo_id_val,
                    "ref": git_source.get("ref", "main")
                }
            except (ValueError, TypeError):
                pass

        status, data = self._request_fn("POST", f"{VERCEL_API_BASE}/v13/deployments", headers, payload)
        if status not in [200, 201]:
            err_msg = data.get("error", {}).get("message", f"Deployment creation failed with HTTP {status}")
            raise VercelIntegrationError(f"Vercel deployment failed: {err_msg}")

        dep_id = data.get("id")
        dep_url = data.get("url")
        if dep_url and not dep_url.startswith("http"):
            dep_url = f"https://{dep_url}"

        prod_url = f"https://{project_name}.vercel.app"

        return VercelDeploymentInfo(
            project_id=data.get("projectId"),
            project_name=project_name,
            deployment_id=dep_id,
            deployment_url=dep_url,
            production_url=prod_url,
            state=data.get("readyState", data.get("status", "BUILDING")),
            framework_preset=data.get("framework")
        )

    def wait_for_deployment(
        self,
        deployment_id: str,
        timeout_seconds: int = 120,
        poll_interval: float = 3.0
    ) -> VercelDeploymentInfo:
        """
        Poll deployment status until READY, ERROR, or timeout.
        """
        headers = self._get_auth_headers()
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            status, data = self._request_fn("GET", f"{VERCEL_API_BASE}/v13/deployments/{deployment_id}", headers)
            if status == 200:
                ready_state = data.get("readyState", data.get("status", "UNKNOWN"))
                dep_url = data.get("url")
                if dep_url and not dep_url.startswith("http"):
                    dep_url = f"https://{dep_url}"

                if ready_state == "READY":
                    alias_list = data.get("alias", [])
                    prod_url = f"https://{alias_list[0]}" if alias_list else dep_url
                    return VercelDeploymentInfo(
                        project_id=data.get("projectId"),
                        project_name=data.get("name"),
                        deployment_id=deployment_id,
                        deployment_url=dep_url,
                        production_url=prod_url,
                        state="READY"
                    )
                elif ready_state in ["ERROR", "CANCELED"]:
                    err_summary = data.get("error", {}).get("message", f"Deployment failed with state: {ready_state}")
                    return VercelDeploymentInfo(
                        project_id=data.get("projectId"),
                        project_name=data.get("name"),
                        deployment_id=deployment_id,
                        deployment_url=dep_url,
                        state="ERROR",
                        error_summary=err_summary
                    )

            time.sleep(poll_interval)

        return VercelDeploymentInfo(
            deployment_id=deployment_id,
            state="TIMEOUT",
            error_summary=f"Deployment timed out after {timeout_seconds}s"
        )
