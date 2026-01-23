"""
Integration Tests for AI-Squad

Tests complete workflows across multiple agents and components.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from ai_squad.core.config import Config
from ai_squad.agents.product_manager import ProductManagerAgent
from ai_squad.agents.architect import ArchitectAgent
from ai_squad.agents.engineer import EngineerAgent
from ai_squad.agents.reviewer import ReviewerAgent
from ai_squad.core.status import StatusManager, IssueStatus
from ai_squad.core.agent_comm import AgentCommunicator
from ai_squad.tools.github import GitHubTool


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test outputs"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def config(self, temp_dir):
        """Create test configuration"""
        return Config({
            "project": {
                "name": "Test Project",
                "github_repo": "test-repo",
                "github_owner": "test-owner"
            },
            "agents": {
                "pm": {"enabled": True, "model": "gpt-4"},
                "architect": {"enabled": True, "model": "gpt-4"},
                "engineer": {"enabled": True, "model": "gpt-4"},
                "reviewer": {"enabled": True, "model": "gpt-4"}
            },
            "output": {
                "prd_dir": str(temp_dir / "prd"),
                "adr_dir": str(temp_dir / "adr"),
                "specs_dir": str(temp_dir / "specs"),
                "reviews_dir": str(temp_dir / "reviews")
            },
            "skills": ["all"]
        })
    
    @pytest.fixture
    def mock_github(self):
        """Create mock GitHub tool"""
        github = Mock(spec=GitHubTool)
        
        # Mock issue
        github.get_issue.return_value = {
            "number": 123,
            "title": "Add user authentication",
            "body": "Implement OAuth login with Google and GitHub",
            "labels": [{"name": "type:feature"}],
            "state": "open",
            "user": {"login": "testuser"}
        }
        
        # Mock PR
        github.get_pull_request.return_value = {
            "number": 456,
            "title": "Implement authentication",
            "body": "Closes #123",
            "state": "open",
            "user": {"login": "testuser"}
        }
        
        github.get_pr_diff.return_value = "diff --git a/auth.py..."
        # Files should be dicts with filename and status
        github.get_pr_files.return_value = [
            {"filename": "auth.py", "status": "added"},
            {"filename": "test_auth.py", "status": "added"}
        ]
        github.add_comment.return_value = True
        github.add_labels.return_value = True
        github.update_issue_status.return_value = True
        github.close_issue.return_value = True
        github._is_configured.return_value = True
        
        return github
    
    def test_pm_to_architect_workflow(self, config, temp_dir, mock_github):
        """Test PM creates PRD, then Architect creates ADR"""
        # Create output directories
        (temp_dir / "prd").mkdir(exist_ok=True)
        (temp_dir / "adr").mkdir(exist_ok=True)
        
        # Step 1: PM creates PRD
        pm = ProductManagerAgent(config, sdk=None)
        pm.github = mock_github
        
        # Mock prerequisite validation to pass (return dict with all passing)
        pm.workflow_validator.validate_prerequisites = Mock(return_value={
            "issue_exists": True,
            "issue_open": True
        })
        
        try:
            result = pm.execute(123)
        except Exception as e:
            print(f"\nPM execution raised exception: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        if not result["success"]:
            print(f"\nPM execution failed: {result.get('error')}")
        
        assert result["success"] is True
        assert (temp_dir / "prd" / "PRD-123.md").exists()
        
        # Step 2: Architect creates ADR (requires PRD)
        architect = ArchitectAgent(config, sdk=None)
        architect.github = mock_github
        
        # Mock prerequisite validation to pass (PRD exists now)
        architect.workflow_validator.validate_prerequisites = Mock(return_value={
            "issue_exists": True,
            "issue_open": True,
            "prd_exists": True
        })
        
        result = architect.execute(123)
        
        assert result["success"] is True
        assert (temp_dir / "adr" / "ADR-123.md").exists()
    
    def test_status_transitions_through_workflow(self, config, mock_github):
        """Test status transitions from Backlog to Done"""
        # Track current labels to simulate real behavior
        current_labels = [{"name": "type:feature"}]
        
        def get_issue_with_labels(issue_number):
            return {
                "number": issue_number,
                "title": "Add user authentication",
                "body": "Implement OAuth login",
                "labels": current_labels,
                "state": "open"
            }
        
        def add_labels(issue_number, labels):
            for label in labels:
                if label.startswith("status:"):
                    # Remove old status labels
                    current_labels[:] = [l for l in current_labels if not l.get("name", "").startswith("status:")]
                    current_labels.append({"name": label})
            return True
        
        mock_github.get_issue.side_effect = get_issue_with_labels
        mock_github.add_labels.side_effect = add_labels
        
        status_manager = StatusManager(mock_github)
        
        # Start: Backlog → Ready (PM completes)
        success = status_manager.transition(
            123,
            IssueStatus.READY,
            "pm",
            "PRD created"
        )
        assert success is True
        
        # Ready → In Progress (Engineer starts)
        success = status_manager.transition(
            123,
            IssueStatus.IN_PROGRESS,
            "engineer",
            "Starting implementation"
        )
        assert success is True
        
        # In Progress → In Review (Engineer completes)
        success = status_manager.transition(
            123,
            IssueStatus.IN_REVIEW,
            "engineer",
            "PR created"
        )
        assert success is True
        
        # In Review → Done (Reviewer approves)
        success = status_manager.transition(
            123,
            IssueStatus.DONE,
            "reviewer",
            "All criteria met"
        )
        assert success is True
        
        # Verify transition history
        history = status_manager.get_transition_history(123)
        assert len(history) == 4
        assert history[0].from_status == IssueStatus.BACKLOG
        assert history[-1].to_status == IssueStatus.DONE
    
    def test_invalid_status_transition(self, config, mock_github):
        """Test that invalid transitions are rejected"""
        from ai_squad.core.status import StatusTransitionError
        
        status_manager = StatusManager(mock_github)
        
        # Try to jump from Backlog to Done (invalid)
        with pytest.raises(StatusTransitionError):
            status_manager.transition(
                123,
                IssueStatus.DONE,
                "pm",
                "Trying to skip steps"
            )
    
    def test_agent_communication_workflow(self, config, mock_github):
        """Test agent-to-agent communication"""
        communicator = AgentCommunicator(
            execution_mode="automated",
            github_tool=mock_github
        )
        
        # Architect asks PM for clarification
        question_id = communicator.ask(
            from_agent="architect",
            to_agent="pm",
            question="Should we support 2FA?",
            context={"issue": 123},
            issue_number=123
        )
        
        assert question_id is not None
        
        # Check pending questions for PM
        pending = communicator.get_pending_questions("pm")
        assert len(pending) == 1
        assert pending[0].content == "Should we support 2FA?"
        
        # PM responds
        success = communicator.respond(
            question_id,
            "Yes, 2FA should be required for all accounts",
            "pm"
        )
        
        assert success is True
        assert question_id in communicator.responses
    
    def test_reviewer_closes_issue_when_criteria_met(self, config, temp_dir, mock_github):
        """Test Reviewer automatically closes issue"""
        (temp_dir / "reviews").mkdir(exist_ok=True)
        
        # Mock issue as already in review status
        mock_github.get_issue.return_value = {
            "number": 123,
            "title": "Add user authentication",
            "body": "Implement OAuth login with Google and GitHub",
            "labels": [{"name": "type:feature"}, {"name": "status:in-review"}],
            "state": "open",
            "user": {"login": "testuser"}
        }
        
        # Mock search_prs_by_issue to return a list (for _check_pr_exists)
        mock_github.search_prs_by_issue.return_value = [{"number": 456}]
        
        reviewer = ReviewerAgent(config, sdk=None)
        reviewer.github = mock_github
        
        # Mock prerequisite validation to pass
        reviewer.workflow_validator.validate_prerequisites = Mock(return_value={
            "issue_exists": True,
            "issue_open": True,
            "pr_exists": True
        })
        
        # Mock successful review
        with patch.object(reviewer, '_check_acceptance_criteria', return_value=True):
            result = reviewer.execute(456)
        
        assert result["success"] is True
        assert result.get("criteria_met") is True
        assert result.get("issue_closed") is True
        assert result.get("closed_issue") == 123
        
        # Verify close_issue was called
        mock_github.close_issue.assert_called_once()


class TestWorkflowValidation:
    """Test workflow prerequisite validation"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"pm": {"enabled": True}},
            "output": {
                "prd_dir": "docs/prd",
                "specs_dir": "docs/specs"
            }
        })
    
    @pytest.fixture
    def mock_github(self):
        """Create mock GitHub tool"""
        github = Mock(spec=GitHubTool)
        github.get_issue.return_value = {
            "number": 123,
            "state": "open"
        }
        return github
    
    def test_architect_requires_prd(self, config, mock_github):
        """Test that Architect validates PRD exists"""
        from ai_squad.core.status import WorkflowValidator
        
        validator = WorkflowValidator(config, mock_github)
        
        # Without PRD
        checks = validator.validate_prerequisites(123, "architect")
        assert checks["prd_exists"] is False
        
        # Create PRD
        Path("docs/prd").mkdir(parents=True, exist_ok=True)
        Path("docs/prd/PRD-123.md").write_text("# PRD")
        
        # With PRD
        checks = validator.validate_prerequisites(123, "architect")
        assert checks["prd_exists"] is True
        
        # Cleanup
        Path("docs/prd/PRD-123.md").unlink()
    
    def test_engineer_requires_prd_and_spec(self, config, mock_github):
        """Test that Engineer validates both PRD and spec exist"""
        from ai_squad.core.status import WorkflowValidator
        
        validator = WorkflowValidator(config, mock_github)
        
        # Create directories
        Path("docs/prd").mkdir(parents=True, exist_ok=True)
        Path("docs/specs").mkdir(parents=True, exist_ok=True)
        
        # Without documents
        checks = validator.validate_prerequisites(123, "engineer")
        assert checks["prd_exists"] is False
        assert checks["spec_exists"] is False
        
        # Create PRD only
        Path("docs/prd/PRD-123.md").write_text("# PRD")
        checks = validator.validate_prerequisites(123, "engineer")
        assert checks["prd_exists"] is True
        assert checks["spec_exists"] is False
        
        # Create spec
        Path("docs/specs/SPEC-123.md").write_text("# Spec")
        checks = validator.validate_prerequisites(123, "engineer")
        assert checks["prd_exists"] is True
        assert checks["spec_exists"] is True
        
        # Cleanup
        Path("docs/prd/PRD-123.md").unlink()
        Path("docs/specs/SPEC-123.md").unlink()


class TestErrorScenarios:
    """Test error handling and recovery"""
    
    @pytest.fixture
    def config(self):
        """Create test configuration"""
        return Config({
            "project": {"name": "Test"},
            "agents": {"pm": {"enabled": True}},
            "output": {"prd_dir": "docs/prd"}
        })
    
    def test_agent_handles_missing_issue(self, config):
        """Test agent handles missing issue gracefully"""
        github = Mock(spec=GitHubTool)
        github.get_issue.return_value = None
        github._is_configured.return_value = True
        
        agent = ProductManagerAgent(config, sdk=None)
        agent.github = github
        
        result = agent.execute(999)
        
        assert result["success"] is False
        # Should fail with missing prerequisites (issue_exists fails)
        assert "missing prerequisites" in result["error"].lower() or "issue" in result["error"].lower()
    
    def test_agent_handles_missing_prerequisites(self, config):
        """Test agent handles missing prerequisites"""
        github = Mock(spec=GitHubTool)
        github.get_issue.return_value = {
            "number": 123,
            "state": "open"
        }
        github._is_configured.return_value = True
        
        architect = ArchitectAgent(config, sdk=None)
        architect.github = github
        
        result = architect.execute(123)
        
        assert result["success"] is False
        assert "prerequisites" in result["error"].lower()
    
    def test_status_manager_resets_on_failure(self, config):
        """Test status can be reset on failure"""
        github = Mock(spec=GitHubTool)
        github.get_issue.return_value = {
            "number": 123,
            "state": "open",
            "labels": [{"name": "status:in-progress"}]
        }
        github.update_issue_status.return_value = True
        github.add_labels.return_value = True
        github.add_comment.return_value = True
        
        status_manager = StatusManager(github)
        
        # Reset to Ready
        success = status_manager.reset_to_ready(
            123,
            "engineer",
            "Build failed, needs fixes"
        )
        
        assert success is True


class TestMultiAgentCollaboration:
    """Test multi-agent collaboration scenarios"""
    
    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration"""
        return Config({
            "project": {"name": "Test"},
            "agents": {
                "pm": {"enabled": True},
                "architect": {"enabled": True}
            },
            "output": {
                "prd_dir": str(tmp_path / "prd"),
                "adr_dir": str(tmp_path / "adr")
            }
        })
    
    def test_agents_can_clarify_with_each_other(self, config):
        """Test agents can ask each other for clarification"""
        github = Mock(spec=GitHubTool)
        github.get_issue.return_value = {"number": 123, "state": "open"}
        github._is_configured.return_value = True
        
        communicator = AgentCommunicator(
            execution_mode="automated",
            github_tool=github
        )
        
        # Architect asks PM
        q1 = communicator.ask("architect", "pm", "Question 1", {}, 123)
        
        # Engineer asks Architect
        q2 = communicator.ask("engineer", "architect", "Question 2", {}, 123)
        
        # UX asks PM
        q3 = communicator.ask("ux", "pm", "Question 3", {}, 123)
        
        # Verify message routing
        pm_questions = communicator.get_pending_questions("pm")
        architect_questions = communicator.get_pending_questions("architect")
        
        assert len(pm_questions) == 2  # From architect and ux
        assert len(architect_questions) == 1  # From engineer
    
    def test_conversation_thread_tracking(self, config):
        """Test conversation threads are tracked properly"""
        github = Mock(spec=GitHubTool)
        communicator = AgentCommunicator(
            execution_mode="automated",
            github_tool=github
        )
        
        # Create conversation
        q1 = communicator.ask("architect", "pm", "Q1", {}, 123)
        communicator.respond(q1, "A1", "pm")
        
        q2 = communicator.ask("architect", "pm", "Q2", {}, 123)
        communicator.respond(q2, "A2", "pm")
        
        # Get full conversation
        conversation = communicator.get_conversation(123)
        
        assert len(conversation) == 4  # 2 questions + 2 responses
        assert conversation[0].content == "Q1"
        assert conversation[1].content == "A1"
        assert conversation[2].content == "Q2"
        assert conversation[3].content == "A2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
