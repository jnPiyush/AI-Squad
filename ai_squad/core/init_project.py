"""
Project initialization

Creates squad.yaml and necessary directories.
"""
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List
import yaml


def initialize_project(force: bool = False) -> Dict[str, Any]:
    """
    Initialize AI-Squad in current project
    
    Args:
        force: Overwrite existing files
        
    Returns:
        Dict with initialization result
    """
    cwd = Path.cwd()
    config_file = cwd / "squad.yaml"
    
    # Check if already initialized
    if config_file.exists() and not force:
        return {
            "success": False,
            "error": "AI-Squad already initialized. Use --force to overwrite."
        }
    
    created = []
    
    try:
        # Create squad.yaml
        _create_config(config_file)
        created.append("squad.yaml")
        
        # Create output directories
        directories = [
            "docs/prd",
            "docs/adr",
            "docs/specs",
            "docs/ux",
            "docs/reviews",
            ".github/agents",
            ".github/skills",
            ".github/templates",
            ".squad/hooks",
        ]
        
        for dir_path in directories:
            full_path = cwd / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            created.append(f"{dir_path}/")
        
        # Copy templates to .github/templates
        _copy_templates(cwd)
        created.append(".github/templates/ (templates)")
        
        # Copy skills to .github/skills
        _copy_skills(cwd)
        created.append(".github/skills/ (18 skills)")
        
        # Create README if not exists
        readme = cwd / "README.md"
        if not readme.exists():
            _create_readme(readme)
            created.append("README.md")
        
        return {
            "success": True,
            "created": created
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def _create_config(path: Path) -> None:
    """Create default squad.yaml"""
    
    # Try to detect GitHub repo from git config
    github_repo = None
    github_owner = None
    
    try:
        import subprocess
        result = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            # Parse GitHub URL (https://github.com/owner/repo.git or git@github.com:owner/repo.git)
            if "github.com" in url:
                parts = url.replace(".git", "").split("/")
                if len(parts) >= 2:
                    github_repo = parts[-1]
                    github_owner = parts[-2].split(":")[-1]
    except:
        pass
    
    config = {
        "project": {
            "name": Path.cwd().name,
            "github_repo": github_repo,
            "github_owner": github_owner,
        },
        "agents": {
            "pm": {
                "enabled": True,
                "model": "gpt-4",
            },
            "architect": {
                "enabled": True,
                "model": "gpt-4",
            },
            "engineer": {
                "enabled": True,
                "model": "gpt-4",
            },
            "ux": {
                "enabled": True,
                "model": "gpt-4",
            },
            "reviewer": {
                "enabled": True,
                "model": "gpt-4",
            },
        },
        "output": {
            "prd_dir": "docs/prd",
            "adr_dir": "docs/adr",
            "specs_dir": "docs/specs",
            "ux_dir": "docs/ux",
            "reviews_dir": "docs/reviews",
        },
        "github": {
            "auto_create_issues": True,
            "auto_create_prs": False,
            "labels": {
                "epic": "type:epic",
                "feature": "type:feature",
                "story": "type:story",
                "bug": "type:bug",
            },
        },
        "skills": ["all"],  # or list specific skills: ["testing", "security", ...]
        "runtime": {
            "provider": "copilot",
            "provider_order": ["copilot", "openai", "azure_openai"],
            "command": None,
            "args": [],
            "prompt_mode": "none",
        },
        "hooks": {
            "enabled": True,
            "use_git_worktree": False,
            "hooks_dir": ".squad/hooks",
        },
    }
    
    with open(path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def _copy_templates(project_dir: Path) -> None:
    """Copy document templates to project"""
    templates_dir = Path(__file__).parent.parent / "templates"
    target_dir = project_dir / ".github" / "templates"
    
    if templates_dir.exists():
        shutil.copytree(templates_dir, target_dir, dirs_exist_ok=True)


def _copy_skills(project_dir: Path) -> None:
    """Copy skills to project"""
    skills_dir = Path(__file__).parent.parent / "skills"
    target_dir = project_dir / ".github" / "skills"
    
    if skills_dir.exists():
        shutil.copytree(skills_dir, target_dir, dirs_exist_ok=True)


def _create_readme(path: Path) -> None:
    """Create basic README with AI-Squad badge"""
    content = f"""# {Path.cwd().name}

[![AI-Squad](https://img.shields.io/badge/AI--Squad-enabled-00ADD8?logo=robot)](https://github.com/jnPiyush/AI-Squad)

> Powered by AI-Squad - Your AI Development Squad

## Getting Started

This project uses AI-Squad for accelerated development.

### Available Agents

- **Product Manager**: `squad pm <issue#>` - Creates PRDs
- **Architect**: `squad architect <issue#>` - Designs solutions
- **Engineer**: `squad engineer <issue#>` - Implements features
- **UX Designer**: `squad ux <issue#>` - Creates designs
- **Reviewer**: `squad review <pr#>` - Reviews code

### Multi-Agent Collaboration

```bash
# Epic planning (PM + Architect)
squad collab 123 pm architect

# Feature development (Architect + Engineer + UX)
squad collab 456 architect engineer ux
```

## Documentation

- PRDs: `docs/prd/`
- ADRs: `docs/adr/`
- Specs: `docs/specs/`
- UX: `docs/ux/`
- Reviews: `docs/reviews/`

## Learn More

- [AI-Squad Documentation](https://github.com/jnPiyush/AI-Squad)
- [Quick Start Guide](https://github.com/jnPiyush/AI-Squad#quick-start)
- [Examples](https://github.com/jnPiyush/AI-Squad/tree/main/examples)
"""
    
    with open(path, "w") as f:
        f.write(content)
