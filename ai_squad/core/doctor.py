"""
Diagnostic checks for AI-Squad setup
"""
import os
from pathlib import Path
from typing import Dict, Any, List


def run_doctor_checks() -> Dict[str, Any]:
    """
    Run diagnostic checks
    
    Returns:
        Dict with check results
    """
    checks = []
    
    # Check 1: GITHUB_TOKEN
    github_token = os.getenv("GITHUB_TOKEN")
    checks.append({
        "name": "GitHub Token",
        "passed": bool(github_token),
        "message": "Found" if github_token else "Not set (export GITHUB_TOKEN=...)"
    })
    
    # Check 2: squad.yaml exists
    config_file = Path.cwd() / "squad.yaml"
    checks.append({
        "name": "Configuration",
        "passed": config_file.exists(),
        "message": "Found squad.yaml" if config_file.exists() else "Run 'squad init' first"
    })
    
    # Check 3: Output directories
    directories = ["docs/prd", "docs/adr", "docs/specs", "docs/ux", "docs/reviews"]
    all_dirs_exist = all((Path.cwd() / d).exists() for d in directories)
    checks.append({
        "name": "Output Directories",
        "passed": all_dirs_exist,
        "message": "All directories exist" if all_dirs_exist else "Some directories missing"
    })
    
    # Check 4: GitHub Copilot SDK
    try:
        import copilot
        checks.append({
            "name": "Copilot SDK",
            "passed": True,
            "message": f"Installed (github-copilot-sdk)"
        })
    except ImportError:
        checks.append({
            "name": "Copilot SDK",
            "passed": False,
            "message": "Not installed (pip install github-copilot-sdk)"
        })
    
    # Check 5: Git repository
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
