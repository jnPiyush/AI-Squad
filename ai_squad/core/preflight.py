"""
Preflight validation checks for AI-Squad workflows.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Dict, Any, List, Optional

from ai_squad.core.config import Config


def _parse_repo_from_url(url: str) -> Optional[str]:
    if not url:
        return None

    # https://github.com/owner/repo.git
    https_match = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/.]+)", url)
    if https_match:
        return f"{https_match.group('owner')}/{https_match.group('repo')}"

    return None


def _resolve_repo(config: Config) -> Optional[str]:
    if config.github_owner and config.github_repo:
        return f"{config.github_owner}/{config.github_repo}"

    # Try git remote origin
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return _parse_repo_from_url(result.stdout.strip())
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None

    return None


def _run_gh(args: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )


def run_preflight_checks(
    *,
    issue_number: Optional[int] = None,
    config: Optional[Config] = None,
) -> Dict[str, Any]:
    """Run preflight checks for Captain mode.

    Returns:
        Dict with all_passed boolean and per-check results.
    """
    cfg = config or Config.load()
    checks: List[Dict[str, Any]] = []

    gh_path = shutil.which("gh")
    checks.append({
        "name": "GitHub CLI",
        "passed": bool(gh_path),
        "message": "gh found" if gh_path else "GitHub CLI not found (install gh)",
    })

    github_token = os.getenv("GITHUB_TOKEN")
    gh_auth_ok = False
    if gh_path:
        try:
            auth = _run_gh(["auth", "status"])
            gh_auth_ok = auth.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            gh_auth_ok = False

    checks.append({
        "name": "GitHub Auth",
        "passed": bool(github_token) or gh_auth_ok,
        "message": "Token (GITHUB_TOKEN)" if github_token else (
            "OAuth (gh auth login)" if gh_auth_ok else "Not authenticated"
        ),
    })

    repo = _resolve_repo(cfg)
    checks.append({
        "name": "Repository",
        "passed": repo is not None,
        "message": repo if repo else "Repo not configured (set project.github_owner/repo or git remote)",
    })

    repo_ok = False
    if gh_path and repo:
        try:
            repo_view = _run_gh(["repo", "view", repo])
            repo_ok = repo_view.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            repo_ok = False

    checks.append({
        "name": "Repo Access",
        "passed": repo_ok,
        "message": "Accessible" if repo_ok else "Cannot access repo via gh",
    })

    if issue_number is not None:
        issue_ok = False
        if gh_path and repo:
            try:
                issue_view = _run_gh(["issue", "view", str(issue_number), "--repo", repo])
                issue_ok = issue_view.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                issue_ok = False

        checks.append({
            "name": "Issue Access",
            "passed": issue_ok,
            "message": f"Issue #{issue_number} accessible" if issue_ok else "Cannot access issue",
        })

    all_passed = all(check["passed"] for check in checks)

    return {
        "all_passed": all_passed,
        "checks": checks,
    }