"""
Tests for preflight validation.
"""
import subprocess


from ai_squad.core.config import Config
from ai_squad.core.preflight import run_preflight_checks


class TestPreflight:
    """Preflight validation tests"""

    def test_preflight_fails_without_gh(self, monkeypatch):
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        monkeypatch.setattr("shutil.which", lambda _cmd: None)

        checks = run_preflight_checks(issue_number=123, config=Config(Config.DEFAULT_CONFIG))
        assert checks["all_passed"] is False
        assert any(c["name"] == "GitHub CLI" and not c["passed"] for c in checks["checks"])

    def test_preflight_passes_with_repo_and_issue(self, monkeypatch, tmp_path):
        _ = tmp_path
        cfg = Config({
            "project": {"name": "Test", "github_owner": "owner", "github_repo": "repo"},
        })

        monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
        monkeypatch.setattr("shutil.which", lambda _cmd: "/usr/bin/gh")

        def fake_run(cmd, **_kwargs):
            return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

        monkeypatch.setattr("subprocess.run", fake_run)

        checks = run_preflight_checks(issue_number=123, config=cfg)
        assert checks["all_passed"] is True
        assert all(c["passed"] for c in checks["checks"])