"""
GitHub Integration Tool

Interacts with GitHub API for issues, PRs, and repository operations.
"""
# ruff: noqa: BLE001
# pylint: disable=broad-except
import os
import subprocess
from typing import Dict, Any, Optional, List
import json
import logging

from ai_squad.core.config import Config
from ai_squad.core.retry import (
    retry_with_backoff,
    GITHUB_API_RETRY,
    RateLimiter,
    CircuitBreaker,
    GitHubRateLimitError
)

logger = logging.getLogger(__name__)


class GitHubCommandError(Exception):
    """Raised when a GitHub CLI command fails"""


class GitHubTool:
    """GitHub API and CLI integration with retry logic and rate limiting"""
    
    def __init__(self, config: Config):
        """
        Initialize GitHub tool
        
        Args:
            config: AI-Squad configuration
        """
        self.config = config
        self.token = os.getenv("GITHUB_TOKEN")
        self.owner = config.github_owner
        self.repo = config.github_repo
        self._gh_auth_checked = False
        self._gh_authenticated = False
        
        # Initialize retry components
        self.rate_limiter = RateLimiter(calls_per_hour=5000, burst_size=100)
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            success_threshold=2,
            timeout=60
        )

    def is_configured(self) -> bool:
        """Public helper to check GitHub configuration state"""
        return self._is_configured()
    
    @retry_with_backoff(GITHUB_API_RETRY)
    def get_issue(self, issue_number: int) -> Optional[Dict[str, Any]]:
        """
        Get issue details
        
        Args:
            issue_number: GitHub issue number
            
        Returns:
            Issue details or None if not found
        """
        if not self._is_configured():
            return self._create_mock_issue(issue_number)
        
        # Check rate limits before making call
        self.rate_limiter.wait_if_needed()
        
        try:
            result = self._run_gh_command_with_circuit_breaker([
                "issue", "view", str(issue_number),
                "--json", "number,title,body,labels,author,createdAt,state"
            ])
            
            self.rate_limiter.record_call()
            
            if result:
                return json.loads(result)
            
        except (json.JSONDecodeError, GitHubCommandError, TimeoutError) as e:
            logger.error("Error fetching issue: %s", e)
        
        return None
    
    def create_issue(self, title: str, body: str, labels: List[str] = None) -> Optional[int]:
        """
        Create a new issue
        
        Args:
            title: Issue title
            body: Issue body
            labels: List of labels
            
        Returns:
            Issue number or None if failed
        """
        if not self._is_configured():
            print("GitHub not configured - issue creation skipped")
            return None
        
        try:
            cmd = ["issue", "create", "--title", title, "--body", body]
            
            if labels:
                for label in labels:
                    cmd.extend(["--label", label])
            
            result = self._run_gh_command(cmd)
            
            # Extract issue number from URL
            if result:
                # URL format: https://github.com/owner/repo/issues/123
                parts = result.strip().split("/")
                if parts:
                    return int(parts[-1])
            
        except Exception as e:
            print(f"Error creating issue: {e}")
        
        return None
    
    def update_issue(self, issue_number: int, labels: List[str] = None, 
                    state: str = None) -> bool:
        """
        Update issue
        
        Args:
            issue_number: Issue number
            labels: Labels to set
            state: State to set (open/closed)
            
        Returns:
            True if successful
        """
        if not self._is_configured():
            return False
        
        try:
            cmd = ["issue", "edit", str(issue_number)]
            
            if labels:
                cmd.extend(["--add-label", ",".join(labels)])
            
            if state:
                if state == "closed":
                    cmd = ["issue", "close", str(issue_number)]
                elif state == "open":
                    cmd = ["issue", "reopen", str(issue_number)]
            
            self._run_gh_command(cmd)
            return True
            
        except Exception as e:
            print(f"Error updating issue: {e}")
            return False
    
    def add_comment(self, issue_number: int, body: str) -> bool:
        """
        Add comment to issue
        
        Args:
            issue_number: Issue number
            body: Comment body
            
        Returns:
            True if successful
        """
        if not self._is_configured():
            return False
        
        try:
            self._run_gh_command([
                "issue", "comment", str(issue_number),
                "--body", body
            ])
            return True
            
        except Exception as e:
            print(f"Error adding comment: {e}")
            return False
    
    def close_issue(self, issue_number: int, comment: str = None) -> bool:
        """
        Close an issue
        
        Args:
            issue_number: Issue number
            comment: Optional comment to add before closing
            
        Returns:
            True if successful
        """
        if not self._is_configured():
            return False
        
        try:
            # Add comment if provided
            if comment:
                self.add_comment(issue_number, comment)
            
            # Close issue
            self._run_gh_command(["issue", "close", str(issue_number)])
            return True
            
        except Exception as e:
            print(f"Error closing issue: {e}")
            return False
    
    def reopen_issue(self, issue_number: int, comment: str = None) -> bool:
        """
        Reopen a closed issue
        
        Args:
            issue_number: Issue number
            comment: Optional comment to add
            
        Returns:
            True if successful
        """
        if not self._is_configured():
            return False
        
        try:
            # Reopen issue
            self._run_gh_command(["issue", "reopen", str(issue_number)])
            
            # Add comment if provided
            if comment:
                self.add_comment(issue_number, comment)
            
            return True
            
        except Exception as e:
            print(f"Error reopening issue: {e}")
            return False
    
    def update_issue_status(self, issue_number: int, status: str) -> bool:
        """
        Update issue status using labels and custom fields
        
        Args:
            issue_number: Issue number
            status: Status value (e.g., "Ready", "In Progress")
            
        Returns:
            True if successful
        """
        if not self._is_configured():
            return False
        
        try:
            # Remove old status labels
            issue = self.get_issue(issue_number)
            if issue:
                old_labels = [l.get("name", "") for l in issue.get("labels", [])]
                status_labels = [l for l in old_labels if l.startswith("status:")]
                
                for label in status_labels:
                    self.remove_label(issue_number, label)
            
            # Add new status label
            status_label = f"status:{status.lower().replace(' ', '-')}"
            self.add_labels(issue_number, [status_label])
            
            return True
            
        except Exception as e:
            print(f"Error updating status: {e}")
            return False
    
    def remove_label(self, issue_number: int, label: str) -> bool:
        """
        Remove a label from an issue
        
        Args:
            issue_number: Issue number
            label: Label to remove
            
        Returns:
            True if successful
        """
        if not self._is_configured():
            return False
        
        try:
            self._run_gh_command([
                "issue", "edit", str(issue_number),
                "--remove-label", label
            ])
            return True
            
        except Exception as e:
            print(f"Error removing label: {e}")
            return False
    
    def get_pull_request(self, pr_number: int) -> Optional[Dict[str, Any]]:
        """
        Get PR details
        
        Args:
            pr_number: PR number
            
        Returns:
            PR details or None
        """
        if not self._is_configured():
            return self._create_mock_pr(pr_number)
        
        try:
            result = self._run_gh_command([
                "pr", "view", str(pr_number),
                "--json", "number,title,body,labels,author,createdAt,state,mergeable"
            ])
            
            if result:
                return json.loads(result)
            
        except (GitHubCommandError, json.JSONDecodeError, subprocess.CalledProcessError, TimeoutError) as e:
            print(f"Error fetching PR: {e}")
        
        return None
    
    def get_pr_diff(self, pr_number: int) -> str:
        """
        Get PR diff
        
        Args:
            pr_number: PR number
            
        Returns:
            Diff content
        """
        if not self._is_configured():
            return "# Mock diff"
        
        try:
            return self._run_gh_command([
                "pr", "diff", str(pr_number)
            ])
        except (GitHubCommandError, subprocess.CalledProcessError, TimeoutError) as e:
            print(f"Error fetching diff: {e}")
            return ""

    def get_pr_files(self, pr_number: int) -> List[Dict[str, Any]]:
        """
        Get PR changed files

        Args:
            pr_number: PR number

        Returns:
            List of file metadata dictionaries
        """
        if not self._is_configured():
            return []

        try:
            result = self._run_gh_command([
                "pr", "view", str(pr_number),
                "--json", "files"
            ])

            if result:
                data = json.loads(result)
                return data.get("files", [])

        except (GitHubCommandError, json.JSONDecodeError, subprocess.CalledProcessError, TimeoutError) as e:
            print(f"Error fetching PR files: {e}")
            return []

        return []
    
    def _run_gh_command(self, args: List[str]) -> Optional[str]:
        """
        Run GitHub CLI command
        
        Args:
            args: Command arguments
            
        Returns:
            Command output or None
        """
        cmd = ["gh"] + args
        
        if self.owner and self.repo:
            cmd.extend(["--repo", f"{self.owner}/{self.repo}"])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            check=False
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            raise GitHubCommandError(f"Command failed: {result.stderr}")
    
    def _is_configured(self) -> bool:
        """
        Check if GitHub is properly configured.
        
        Supports two authentication methods:
        1. GitHub CLI OAuth (gh auth login) - Preferred
        2. GITHUB_TOKEN environment variable - Fallback
        
        Returns:
            True if either auth method is available and repo is configured
        """
        # Must have repo configured
        if not (self.owner and self.repo):
            return False
        
        # Check 1: GITHUB_TOKEN env var
        if self.token:
            return True
        
        # Check 2: gh CLI OAuth (cached check)
        if not self._gh_auth_checked:
            self._gh_auth_checked = True
            self._gh_authenticated = self._check_gh_auth()
        
        return self._gh_authenticated
    
    def _check_gh_auth(self) -> bool:
        """Check if gh CLI is authenticated via OAuth"""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            # gh auth status returns 0 if authenticated
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def set_auth_cache(self, checked: bool, authenticated: bool) -> None:
        """Set cached GitHub CLI auth state (for tests)."""
        self._gh_auth_checked = checked
        self._gh_authenticated = authenticated
    
    def get_auth_method(self) -> str:
        """
        Get the current authentication method being used.
        
        Returns:
            'oauth' if using gh CLI, 'token' if using GITHUB_TOKEN, 'none' if not configured
        """
        if not (self.owner and self.repo):
            return "none"
        
        if self.token:
            return "token"
        
        if not self._gh_auth_checked:
            self._gh_auth_checked = True
            self._gh_authenticated = self._check_gh_auth()
        
        if self._gh_authenticated:
            return "oauth"
        
        return "none"
    
    def search_issues_by_labels(self, include_labels: List[str], 
                                exclude_labels: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search for issues with specific labels
        
        Args:
            include_labels: Labels that must be present
            exclude_labels: Labels that must NOT be present
            
        Returns:
            List of matching issues
        """
        if not self._is_configured():
            return []
        
        try:
            # Build search query
            query_parts = ["is:open", "is:issue"]
            
            for label in include_labels:
                query_parts.append(f'label:"{label}"')
            
            if exclude_labels:
                for label in exclude_labels:
                    query_parts.append(f'-label:"{label}"')
            
            if self.owner and self.repo:
                query_parts.append(f"repo:{self.owner}/{self.repo}")
            
            query = " ".join(query_parts)
            
            # Run search
            result = self._run_gh_command([
                "search", "issues",
                query,
                "--json", "number,title,body,labels,author,createdAt,state",
                "--limit", "50"
            ])
            
            if result:
                data = json.loads(result)
                return data if isinstance(data, list) else []
            
        except Exception as e:
            print(f"Error searching issues: {e}")
        
        return []
    
    def add_labels(self, issue_number: int, labels: List[str]) -> bool:
        """
        Add labels to an issue
        
        Args:
            issue_number: Issue number
            labels: Labels to add
            
        Returns:
            True if successful
        """
        if not self._is_configured():
            return False
        
        try:
            for label in labels:
                self._run_gh_command([
                    "issue", "edit", str(issue_number),
                    "--add-label", label
                ])
            return True
            
        except (GitHubCommandError, subprocess.CalledProcessError, TimeoutError) as e:
            print(f"Error adding labels: {e}")
            return False
    
    def search_prs_by_issue(self, issue_number: int) -> List[Dict[str, Any]]:
        """
        Search for PRs that reference an issue
        
        Args:
            issue_number: Issue number
            
        Returns:
            List of matching PRs
        """
        if not self._is_configured():
            return []
        
        try:
            # Search for PRs mentioning the issue
            query_parts = [
                "is:pr",
                f"#{issue_number} in:body",
                f"repo:{self.owner}/{self.repo}"
            ]
            
            query = " ".join(query_parts)
            
            result = self._run_gh_command([
                "search", "prs",
                query,
                "--json", "number,title,state,url",
                "--limit", "10"
            ])
            
            if result:
                data = json.loads(result)
                return data if isinstance(data, list) else []
            
        except Exception as e:
            print(f"Error searching PRs: {e}")
        
        return []
    
    def get_issues_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Get open issues with specific status
        
        Args:
            status: Status to filter by (e.g., "Ready", "In Progress")
            
        Returns:
            List of matching issues
        """
        status_label = f"status:{status.lower().replace(' ', '-')}"
        return self.search_issues_by_labels([status_label])
    
    def _run_gh_command_with_circuit_breaker(self, cmd: List[str]) -> Optional[str]:
        """
        Run GitHub CLI command with circuit breaker protection
        
        Args:
            cmd: Command arguments
            
        Returns:
            Command output or None
        """
        return self.circuit_breaker.call(self._run_gh_command, cmd)
    
    def _check_rate_limit_response(self, error_msg: str) -> None:
        """
        Check if error indicates rate limit and raise appropriate exception
        
        Args:
            error_msg: Error message from GitHub
            
        Raises:
            GitHubRateLimitError: If rate limit exceeded
        """
        if "rate limit" in error_msg.lower() or "403" in error_msg:
            raise GitHubRateLimitError(f"GitHub rate limit exceeded: {error_msg}")
    
    def get_rate_limit_status(self) -> Dict[str, int]:
        """
        Get current rate limit status
        
        Returns:
            Dict with rate limit information
        """
        github_limits = {}
        
        if self._is_configured():
            try:
                result = self._run_gh_command(["api", "rate_limit"])
                if result:
                    data = json.loads(result)
                    github_limits = {
                        "remaining": data.get("rate", {}).get("remaining", 0),
                        "limit": data.get("rate", {}).get("limit", 5000),
                        "reset": data.get("rate", {}).get("reset", 0)
                    }
            except (json.JSONDecodeError, GitHubCommandError, TimeoutError) as e:
                logger.warning("Could not fetch GitHub rate limits: %s", e)
        
        # Combine with our rate limiter
        local_limits = self.rate_limiter.get_remaining()
        
        return {
            **github_limits,
            **local_limits
        }

    
    def _create_mock_issue(self, issue_number: int) -> Dict[str, Any]:
        """Create mock issue for testing"""
        return {
            "number": issue_number,
            "title": f"Mock Issue #{issue_number}",
            "body": "This is a mock issue for testing purposes.",
            "labels": ["type:story"],
            "author": {"login": "mock-user"},
            "createdAt": "2026-01-22T00:00:00Z",
            "state": "open"
        }
    
    def _create_mock_pr(self, pr_number: int) -> Dict[str, Any]:
        """Create mock PR for testing"""
        return {
            "number": pr_number,
            "title": f"Mock PR #{pr_number}",
            "body": "This is a mock PR for testing purposes.",
            "labels": [],
            "author": {"login": "mock-user"},
            "createdAt": "2026-01-22T00:00:00Z",
            "state": "open",
            "mergeable": "MERGEABLE"
        }
