"""
Tests for AI-Squad CLI
"""
import pytest
from click.testing import CliRunner
from pathlib import Path

from ai_squad.cli import main


class TestCLI:
    """Test CLI commands"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()
    
    def test_version(self, runner):
        """Test --version flag"""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "AI-Squad version" in result.output
    
    def test_help(self, runner):
        """Test --help flag"""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "AI-Squad" in result.output
        assert "Commands:" in result.output
    
    def test_init_creates_config(self, runner, tmp_path):
        """Test squad init creates config file"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0
            assert Path("squad.yaml").exists()
    
    def test_init_force_overwrites(self, runner, tmp_path):
        """Test squad init --force overwrites existing config"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # First init
            runner.invoke(main, ["init"])
            
            # Second init should fail without --force
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 1
            
            # With --force should succeed
            result = runner.invoke(main, ["init", "--force"])
            assert result.exit_code == 0
    
    def test_doctor_checks_setup(self, runner, tmp_path):
        """Test squad doctor validates setup"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["doctor"])
            # Should pass or provide clear errors
            assert "check" in result.output.lower()

    def test_health_command(self, runner, tmp_path):
        """Test squad health command"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["health"])
            assert result.exit_code == 0
            assert "Routing Health Status" in result.output

    def test_capabilities_list_empty(self, runner, tmp_path):
        """Test empty capabilities list"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["capabilities", "list"])
            assert result.exit_code == 0
            assert "No capability packages installed" in result.output

    def test_capabilities_key_set_and_show(self, runner, tmp_path):
        """Test capability signature key management"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["capabilities", "key", "--set", "test-key"])
            assert result.exit_code == 0
            assert "Signature key saved" in result.output

            result = runner.invoke(main, ["capabilities", "key", "--show"])
            assert result.exit_code == 0
            assert "Signature key is configured" in result.output

    def test_delegation_list_empty(self, runner, tmp_path):
        """Test empty delegation list"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["delegation", "list"])
            assert result.exit_code == 0
            assert "No delegation links found" in result.output

    def test_graph_export_empty(self, runner, tmp_path):
        """Test graph export output"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["graph", "export"])
            assert result.exit_code == 0
            assert "graph TD" in result.output

    def test_graph_impact_missing_node(self, runner, tmp_path):
        """Test graph impact missing node"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["graph", "impact", "missing-node"])
            assert result.exit_code == 0
            assert "Node not found" in result.output

    def test_scout_list_empty(self, runner, tmp_path):
        """Test scout list with no runs"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["scout", "list"])
            assert result.exit_code == 0
            assert "No scout runs found" in result.output

    def test_scout_show_missing(self, runner, tmp_path):
        """Test scout show missing run"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["scout", "show", "scout-missing"])
            assert result.exit_code == 0
            assert "Scout run not found" in result.output

    def test_scout_run_noop(self, runner, tmp_path):
        """Test scout run noop task"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["scout", "run"])
            assert result.exit_code == 0
            assert "Scout run completed" in result.output


class TestAgentCommands:
    """Test agent execution commands"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()
    
    @pytest.fixture
    def setup_project(self, runner, tmp_path):
        """Setup test project"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(main, ["init"])
            yield
    
    def test_pm_command(self, runner, setup_project):
        """Test squad pm command"""
        result = runner.invoke(main, ["pm", "123"])
        # Command should execute (may fail due to missing GitHub token)
        assert "Product Manager" in result.output or "Error" in result.output
    
    def test_architect_command(self, runner, setup_project):
        """Test squad architect command"""
        result = runner.invoke(main, ["architect", "123"])
        assert "Architect" in result.output or "Error" in result.output
    
    def test_engineer_command(self, runner, setup_project):
        """Test squad engineer command"""
        result = runner.invoke(main, ["engineer", "123"])
        assert "Engineer" in result.output or "Error" in result.output
    
    def test_ux_command(self, runner, setup_project):
        """Test squad ux command"""
        result = runner.invoke(main, ["ux", "123"])
        assert "UX Designer" in result.output or "Error" in result.output
    
    def test_review_command(self, runner, setup_project):
        """Test squad review command"""
        result = runner.invoke(main, ["review", "456"])
        assert "Reviewer" in result.output or "Error" in result.output
    
    def test_collab_command(self, runner, setup_project):
        """Test squad collab command"""
        result = runner.invoke(main, ["collab", "123", "pm", "architect"])
        assert "collaboration" in result.output.lower() or "Error" in result.output
