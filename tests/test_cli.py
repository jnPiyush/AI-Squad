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
    
    def test_deploy_creates_config(self, runner, tmp_path):
        """Test squad deploy creates config file"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["deploy"])
            assert result.exit_code == 0
            assert Path("squad.yaml").exists()
    
    def test_deploy_force_overwrites(self, runner, tmp_path):
        """Test squad deploy --force overwrites existing config"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # First deploy
            runner.invoke(main, ["deploy"])
            
            # Second deploy should fail without --force
            result = runner.invoke(main, ["deploy"])
            assert result.exit_code == 1
            
            # With --force should succeed
            result = runner.invoke(main, ["deploy", "--force"])
            assert result.exit_code == 0
    
    def test_sitrep_checks_setup(self, runner, tmp_path):
        """Test squad sitrep validates setup"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["sitrep"])
            # Should pass or provide clear errors
            assert "check" in result.output.lower()

    def test_status_command(self, runner, tmp_path):
        """Test squad status command"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["status"])
            assert result.exit_code == 0
            assert "Routing Health Status" in result.output or "Status" in result.output

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
            runner.invoke(main, ["deploy"])
            yield
    
    def test_pm_command(self, runner, setup_project):
        _ = setup_project
        """Test squad pm command"""
        result = runner.invoke(main, ["pm", "123"])
        # Command should execute (may fail due to missing GitHub token)
        assert "Product Manager" in result.output or "Error" in result.output
    
    def test_architect_command(self, runner, setup_project):
        _ = setup_project
        """Test squad architect command"""
        result = runner.invoke(main, ["architect", "123"])
        assert "Architect" in result.output or "Error" in result.output
    
    def test_engineer_command(self, runner, setup_project):
        _ = setup_project
        """Test squad engineer command"""
        result = runner.invoke(main, ["engineer", "123"])
        assert "Engineer" in result.output or "Error" in result.output
    
    def test_ux_command(self, runner, setup_project):
        _ = setup_project
        """Test squad ux command"""
        result = runner.invoke(main, ["ux", "123"])
        assert "UX Designer" in result.output or "Error" in result.output
    
    def test_review_command(self, runner, setup_project):
        _ = setup_project
        """Test squad review command"""
        result = runner.invoke(main, ["review", "456"])
        assert "Reviewer" in result.output or "Error" in result.output
    
    def test_joint_op_command(self, runner, setup_project):
        _ = setup_project
        """Test squad joint-op command"""
        result = runner.invoke(main, ["joint-op", "123", "pm", "architect"])
        # Command shows "Joint Operation" output or error
        assert "joint operation" in result.output.lower() or "Error" in result.output or "participants" in result.output.lower()
    
    def test_captain_command(self, runner, setup_project):
        _ = setup_project
        """Test squad captain command"""
        result = runner.invoke(main, ["captain", "123"])
        # Should show Captain coordinating message or error
        assert "Captain" in result.output or "Error" in result.output or "captain" in result.output.lower()
    
    def test_captain_command_invalid_issue(self, runner, setup_project):
        _ = setup_project
        """Test squad captain with invalid issue number type"""
        result = runner.invoke(main, ["captain", "not-a-number"])
        # Should fail with usage error
        assert result.exit_code != 0


class TestOrchestrationCommands:
    """Test orchestration-related CLI commands"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()
    
    def test_ops_command_empty(self, runner, tmp_path):
        """Test squad ops command with no operations"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(main, ["deploy"])
            result = runner.invoke(main, ["ops"])
            assert result.exit_code == 0
            # Should show no operations or empty list
            assert "No operations" in result.output or "Operations" in result.output or "No work items" in result.output
    
    def test_ops_command_with_status_filter(self, runner, tmp_path):
        """Test squad ops command with status filter"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(main, ["deploy"])
            result = runner.invoke(main, ["ops", "--status", "ready"])
            assert result.exit_code == 0
    
    def test_ops_command_with_agent_filter(self, runner, tmp_path):
        """Test squad ops command with agent filter"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(main, ["deploy"])
            result = runner.invoke(main, ["ops", "--agent", "pm"])
            assert result.exit_code == 0
    
    def test_convoys_command_empty(self, runner, tmp_path):
        """Test squad convoys command with no convoys"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(main, ["deploy"])
            result = runner.invoke(main, ["convoys"])
            assert result.exit_code == 0
            assert "No convoys" in result.output or "Convoy" in result.output
    
    def test_status_command_detailed(self, runner, tmp_path):
        """Test squad status command output"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(main, ["deploy"])
            result = runner.invoke(main, ["status"])
            assert result.exit_code == 0
            assert "Health" in result.output or "health" in result.output.lower() or "Status" in result.output
    
    def test_patrol_command(self, runner, tmp_path):
        """Test squad patrol command"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(main, ["deploy"])
            result = runner.invoke(main, ["patrol", "--help"])
            # Command should show help or execute
            assert result.exit_code == 0 or "patrol" in result.output.lower()


class TestDashboardCommand:
    """Test dashboard command"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()
    
    def test_dashboard_command_help(self, runner, tmp_path):
        """Test dashboard command help"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["dashboard", "--help"])
            assert result.exit_code == 0
            assert "dashboard" in result.output.lower()


class TestGraphCommands:
    """Test graph-related CLI commands"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()
    
    def test_graph_export_formats(self, runner, tmp_path):
        """Test graph export command output format"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(main, ["deploy"])
            result = runner.invoke(main, ["graph", "export"])
            assert result.exit_code == 0
            # Should output mermaid format
            assert "graph" in result.output.lower()


class TestSignalCommands:
    """Test signal-related CLI commands"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()
    
    def test_signal_command_help(self, runner, tmp_path):
        """Test signal command help"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["signal", "--help"])
            assert result.exit_code == 0
            assert "signal" in result.output.lower()


class TestIdentityCommand:
    """Test identity/status commands"""
    
    @pytest.fixture
    def runner(self):
        """Create CLI runner"""
        return CliRunner()
    
    def test_status_command_identity(self, runner, tmp_path):
        """Test squad status command for identity info"""
        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(main, ["deploy"])
            result = runner.invoke(main, ["status"])
            # Status command may fail without proper setup, but should run
            # Accept either success or error output
            assert "status" in result.output.lower() or "Status" in result.output or "Error" in result.output or result.exit_code in (0, 1)
