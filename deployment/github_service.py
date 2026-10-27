import os
import re
import shutil
import tempfile
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from .models import GitHubRepoInfo

# Sensitive/prohibited patterns to strictly exclude from public or private Git publication
PROHIBITED_FILE_PATTERNS = [
    r'^\.env(\..+)?$',         # .env, .env.local, .env.production (allow .env.example)
    r'.*\.pem$',               # Certificates and private keys
    r'.*\.key$',
    r'.*id_rsa.*',
    r'.*\.sqlite3?$',          # Local databases
    r'.*\.db$',
    r'.*credentials.*',
    r'.*secret.*\.json$',
    r'.*token.*\.txt$'
]

DEFAULT_GITIGNORE = """# Dependencies
node_modules/
.deps/
__pycache__/
*.pyc

# Environment & secrets
.env
.env.local
.env.*.local
*.pem
*.key

# Build outputs
dist/
build/
.next/
out/

# System files
.DS_Store
Thumbs.db
"""

class GitHubPublishingError(Exception):
    pass

class GitHubPublishingService:
    def __init__(self, command_runner=None):
        """
        :param command_runner: Optional callable(cmd, cwd=None, env=None) -> (returncode, stdout, stderr)
                               Defaults to subprocess.run for production execution.
        """
        self._runner = command_runner or self._default_runner

    @staticmethod
    def _default_runner(cmd: List[str], cwd: Optional[str] = None, env: Optional[Dict[str, str]] = None) -> Tuple[int, str, str]:
        resolved_cmd = list(cmd)
        if resolved_cmd and not os.path.isabs(resolved_cmd[0]):
            found = shutil.which(resolved_cmd[0])
            if found:
                resolved_cmd[0] = found

        run_env = os.environ.copy()
        if env:
            run_env.update(env)

        try:
            res = subprocess.run(
                resolved_cmd,
                cwd=cwd,
                env=run_env,
                capture_output=True,
                text=True,
                timeout=60
            )
            return res.returncode, res.stdout, res.stderr
        except Exception as e:
            return 1, "", str(e)

    def check_auth(self) -> Dict[str, Any]:
        """Verify GitHub CLI or GITHUB_TOKEN authentication without exposing secrets."""
        # 1. Try GitHub CLI (preferred)
        code, out, err = self._runner(["gh", "auth", "status"])
        full_text = out + "\n" + err
        if code == 0 or "Logged in to github.com" in full_text:
            username = None
            # Extract username
            match = re.search(r'account\s+([A-Za-z0-9_-]+)', full_text)
            if match:
                username = match.group(1)
            else:
                u_code, u_out, _ = self._runner(["gh", "api", "user", "-q", ".login"])
                if u_code == 0 and u_out.strip():
                    username = u_out.strip()
            return {
                "authenticated": True,
                "auth_method": "gh_cli",
                "username": username or "authenticated-user",
                "message": "GitHub CLI authenticated"
            }

        # 2. Try GITHUB_TOKEN environment variable fallback
        token = os.environ.get("GITHUB_TOKEN")
        if token and len(token) >= 10:
            return {
                "authenticated": True,
                "auth_method": "env_token",
                "username": os.environ.get("GITHUB_USER", "env-user"),
                "message": "GITHUB_TOKEN present in environment"
            }

        return {
            "authenticated": False,
            "auth_method": "none",
            "username": None,
            "message": "GitHub CLI not logged in (run 'gh auth login') and GITHUB_TOKEN not set"
        }

    @staticmethod
    def is_file_allowed(path: str) -> bool:
        """Filter out prohibited sensitive files."""
        norm_path = path.replace("\\", "/").strip("/")
        basename = os.path.basename(norm_path)
        
        # Explicit exception: .env.example is allowed
        if basename == ".env.example":
            return True

        for pattern in PROHIBITED_FILE_PATTERNS:
            if re.match(pattern, basename, re.IGNORECASE):
                return False
        return True

    @classmethod
    def filter_sensitive_files(cls, files: Dict[str, str]) -> Tuple[Dict[str, str], List[str]]:
        """Separate allowed files from prohibited sensitive files."""
        allowed = {}
        excluded = []
        for path, content in files.items():
            if cls.is_file_allowed(path):
                allowed[path] = content
            else:
                excluded.append(path)
        return allowed, excluded

    @staticmethod
    def normalize_repo_name(project_name: str, run_id: str) -> str:
        """Generate safe, collision-resistant repository name."""
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '-', project_name).strip('-').lower()
        if not clean_name:
            clean_name = "project"
        short_id = run_id.replace("run-", "")[:8]
        return f"devagents-{clean_name}-{short_id}"

    def publish_project(
        self,
        run_id: str,
        project_name: str,
        files: Dict[str, str],
        is_private: bool = True,
        ci_workflow_content: Optional[str] = None
    ) -> GitHubRepoInfo:
        """
        Publish generated files to a brand-new private GitHub repository.
        """
        auth_status = self.check_auth()
        if not auth_status["authenticated"]:
            raise GitHubPublishingError(
                f"GitHub authentication unavailable: {auth_status['message']}. Please execute 'gh auth login' or set GITHUB_TOKEN."
            )

        owner = auth_status["username"]
        repo_name = self.normalize_repo_name(project_name, run_id)
        
        # Create staging workspace
        with tempfile.TemporaryDirectory(prefix=f"devagents-gh-{run_id}-") as staging_dir:
            # 1. Filter and write approved project files
            written_count = 0
            for rel_path, content in files.items():
                if not self.is_file_allowed(rel_path):
                    continue
                
                # Prevent path traversal
                dest = os.path.normpath(os.path.join(staging_dir, rel_path))
                if not dest.startswith(staging_dir):
                    raise GitHubPublishingError(f"Unsafe path traversal rejected: {rel_path}")

                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest, "w", encoding="utf-8") as f:
                    f.write(content)
                written_count += 1

            if written_count == 0:
                raise GitHubPublishingError("No valid files available to publish in project.")

            # 2. Ensure .gitignore exists
            gitignore_path = os.path.join(staging_dir, ".gitignore")
            if not os.path.exists(gitignore_path):
                with open(gitignore_path, "w", encoding="utf-8") as gf:
                    gf.write(DEFAULT_GITIGNORE)

            # 3. Add CI workflow if supplied
            if ci_workflow_content:
                ci_path = os.path.join(staging_dir, ".github", "workflows", "ci.yml")
                os.makedirs(os.path.dirname(ci_path), exist_ok=True)
                with open(ci_path, "w", encoding="utf-8") as wf:
                    wf.write(ci_workflow_content)

            # 4. Initialize Git repository
            init_code, _, init_err = self._runner(["git", "init", "-b", "main"], cwd=staging_dir)
            if init_code != 0:
                # Fallback for older git
                self._runner(["git", "init"], cwd=staging_dir)
                self._runner(["git", "branch", "-M", "main"], cwd=staging_dir)

            self._runner(["git", "config", "user.name", "DevAgents Autonomous Pipeline"], cwd=staging_dir)
            self._runner(["git", "config", "user.email", "pipeline@devagents.ai"], cwd=staging_dir)
            
            self._runner(["git", "add", "."], cwd=staging_dir)
            commit_code, _, commit_err = self._runner(
                ["git", "commit", "-m", f"Initial commit for {project_name} by DevAgents"],
                cwd=staging_dir
            )
            if commit_code != 0:
                raise GitHubPublishingError(f"Failed to create initial git commit: {commit_err}")

            # Get commit SHA
            _, sha_out, _ = self._runner(["git", "rev-parse", "HEAD"], cwd=staging_dir)
            commit_sha = sha_out.strip() if sha_out else None

            # 5. Check if repository already exists (idempotency)
            check_code, _, _ = self._runner(["gh", "repo", "view", f"{owner}/{repo_name}"])
            repo_created = False
            visibility_flag = "--private" if is_private else "--public"

            if check_code != 0:
                # Create repository on GitHub
                create_cmd = ["gh", "repo", "create", repo_name, visibility_flag, "--source=.", "--remote=origin"]
                c_code, c_out, c_err = self._runner(create_cmd, cwd=staging_dir)
                if c_code != 0:
                    raise GitHubPublishingError(f"Failed to create GitHub repository '{repo_name}': {c_err}")
                repo_created = True
            else:
                # Repo already exists; configure origin remote if missing
                self._runner(["git", "remote", "remove", "origin"], cwd=staging_dir)
                remote_url = f"https://github.com/{owner}/{repo_name}.git"
                self._runner(["git", "remote", "add", "origin", remote_url], cwd=staging_dir)

            # 6. Push to remote
            push_cmd = ["git", "push", "-u", "origin", "main"]
            p_code, p_out, p_err = self._runner(push_cmd, cwd=staging_dir)
            if p_code != 0:
                # Retry with force push if idempotently updating existing test repo
                p_code, p_out, p_err = self._runner(["git", "push", "-u", "origin", "main", "--force"], cwd=staging_dir)
                if p_code != 0:
                    raise GitHubPublishingError(f"Failed to push code to GitHub repository '{repo_name}': {p_err}")

            repo_url = f"https://github.com/{owner}/{repo_name}"

            return GitHubRepoInfo(
                repo_name=repo_name,
                repo_url=repo_url,
                owner=owner,
                is_private=is_private,
                default_branch="main",
                commit_sha=commit_sha,
                created_at=datetime.utcnow().isoformat()
            )
