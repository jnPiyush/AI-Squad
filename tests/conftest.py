"""
Test fixtures and configuration for pytest
"""
import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_project_dir():
    """Create temporary project directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_github_token(monkeypatch):
    """Mock GitHub token"""
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_mock_token_12345")


@pytest.fixture
def mock_config():
    """Mock AI-Squad configuration"""
    from ai_squad.core.config import Config
    
    return Config({
        "project": {
            "name": "Test Project",
            "github_repo": "test-repo",
            "github_owner": "test-user"
        },
        "agents": {
            "pm": {"enabled": True, "model": "claude-sonnet-4.5"},
            "architect": {"enabled": True, "model": "claude-sonnet-4.5"},
            "engineer": {"enabled": True, "model": "claude-sonnet-4.5"},
            "ux": {"enabled": True, "model": "claude-sonnet-4.5"},
            "reviewer": {"enabled": True, "model": "claude-sonnet-4.5"}
        },
        "output": {
            "prd_dir": "docs/prd",
            "adr_dir": "docs/adr",
            "specs_dir": "docs/specs",
            "ux_dir": "docs/ux",
            "reviews_dir": "docs/reviews"
        },
        "github": {
            "auto_create_issues": True,
            "auto_create_prs": False
        },
        "skills": ["all"]
    })


@pytest.fixture
def mock_issue():
    """Mock GitHub issue"""
    return {
        "number": 123,
        "title": "Test Feature",
        "body": "Test feature description",
        "labels": ["type:feature"],
        "user": {"login": "testuser"},
        "created_at": "2026-01-22T00:00:00Z",
        "state": "open"
    }


@pytest.fixture
def mock_pr():
    """Mock GitHub pull request"""
    return {
        "number": 456,
        "title": "Test PR",
        "body": "Test PR description",
        "labels": [],
        "user": {"login": "testuser"},
        "created_at": "2026-01-22T00:00:00Z",
        "state": "open",
        "mergeable": "MERGEABLE"
    }
