"""
Diagnostic checks for AI-Squad setup
"""
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple


def _check_gh_auth() -> bool:
    """Check if gh CLI is authenticated via OAuth"""
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def _check_copilot_cli() -> Tuple[bool, str]:
    """Check if Copilot CLI is installed and authenticated"""
    if shutil.which("copilot") is None:
        return False, "Copilot CLI not found. Install and run 'copilot --version'"

    try:
        version = subprocess.run(
            ["copilot", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if version.returncode != 0:
            return False, "Copilot CLI not responding. Reinstall or check PATH"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False, "Copilot CLI not available. Install and retry"

    try:
        auth = subprocess.run(
            ["copilot", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if auth.returncode == 0:
            return True, "Authenticated"
        return False, "Not authenticated. Run 'copilot auth login'"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False, "Unable to verify Copilot auth. Run 'copilot auth login'"


def run_doctor_checks() -> Dict[str, Any]:
    """
    Run diagnostic checks
    
    Returns:
        Dict with check results
    """
    checks = []
    
    # Check 1: GitHub Authentication (Token or OAuth)
    github_token = os.getenv("GITHUB_TOKEN")
    gh_oauth = _check_gh_auth()
    
    if github_token:
        auth_message = "Token (GITHUB_TOKEN)"
        auth_passed = True
    elif gh_oauth:
        auth_message = "OAuth (gh auth login)"
        auth_passed = True
    else:
        auth_message = "Not configured. Use 'gh auth login' (recommended) or set GITHUB_TOKEN"
        auth_passed = False
    
    checks.append({
        "name": "GitHub Auth",
        "passed": auth_passed,
        "message": auth_message
    })

    # Check 2: Copilot CLI (installed + authenticated)
    copilot_ok, copilot_message = _check_copilot_cli()
    checks.append({
        "name": "Copilot CLI",
        "passed": copilot_ok,
        "message": copilot_message
    })
    
    # Check 3: squad.yaml exists
    config_file = Path.cwd() / "squad.yaml"
    checks.append({
        "name": "Configuration",
        "passed": config_file.exists(),
        "message": "Found squad.yaml" if config_file.exists() else "Run 'squad init' first"
    })
    
    # Check 4: Output directories
    directories = ["docs/prd", "docs/adr", "docs/specs", "docs/ux", "docs/reviews"]
    all_dirs_exist = all((Path.cwd() / d).exists() for d in directories)
    checks.append({
        "name": "Output Directories",
        "passed": all_dirs_exist,
        "message": "All directories exist" if all_dirs_exist else "Some directories missing"
    })
    
    # Check 5: AI Provider (Copilot -> OpenAI -> Azure -> Template)
    try:
        from ai_squad.core.ai_provider import get_ai_provider, AIProviderType
        provider = get_ai_provider()
        available = provider.get_available_providers()
        
        if available:
            primary = available[0]
            provider_names = {
                "copilot": "GitHub Copilot",
                "openai": "OpenAI API",
                "azure_openai": "Azure OpenAI"
            }
            checks.append({
                "name": "AI Provider",
                "passed": True,
                "message": f"{provider_names.get(primary, primary)} ({', '.join(available)})"
            })
        else:
            checks.append({
                "name": "AI Provider",
                "passed": False,
                "message": "No AI provider. Ensure Copilot CLI auth or set OPENAI_API_KEY/AZURE_OPENAI_*"
            })
    except Exception as e:
        checks.append({
            "name": "AI Provider",
            "passed": False,
            "message": f"Error checking AI providers: {e}"
        })
    
    # Check 6: Git repository
    git_dir = Path.cwd() / ".git"
    checks.append({
        "name": "Git Repository",
        "passed": git_dir.exists(),
        "message": "Found .git/" if git_dir.exists() else "Not a git repository"
    })
    
    all_passed = all(check["passed"] for check in checks)
    
    return {
        "all_passed": all_passed,
        "checks": checks
    }
