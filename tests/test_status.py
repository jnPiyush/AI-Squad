"""
Status Management Tests

Comprehensive tests for status transitions and workflow validation.
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from ai_squad.core.status import (
    IssueStatus,
    StatusManager,
    WorkflowValidator,
    StatusTransitionError,
    StatusTransition
)
from ai_squad.tools.github import GitHubTool
from ai_squad.core.config import Config


class TestIssueStatus:
    """Test IssueStatus enum"""
    
    def test_all_statuses_defined(self):
        """Test all expected statuses exist"""
        assert IssueStatus.BACKLOG
        assert IssueStatus.READY
        assert IssueStatus.IN_PROGRESS
        assert IssueStatus.IN_REVIEW
        assert IssueStatus.DONE
        assert IssueStatus.BLOCKED
    
    def test_from_string_conversion(self):
        """Test string to status conversion"""
        assert IssueStatus.from_string("Backlog") == IssueStatus.BACKLOG
        assert IssueStatus.from_string("ready") == IssueStatus.READY
        assert IssueStatus.from_string("in progress") == IssueStatus.IN_PROGRESS
        assert IssueStatus.from_string("In Review") == IssueStatus.IN_REVIEW
        assert IssueStatus.from_string("done") == IssueStatus.DONE
        assert IssueStatus.from_string("BLOCKED") == IssueStatus.BLOCKED
    
    def test_from_string_invalid(self):
        """Test invalid string returns None"""
        assert IssueStatus.from_string("invalid") is None
        assert IssueStatus.from_string("") is None


class TestStatusManager:
    """Test StatusManager class"""
    
    @pytest.fixture
    def mock_github(self):
        """Create mock GitHub tool"""
        github = Mock(spec=GitHubTool)
        github.get_issue.return_value = {
            "number": 123,
            "state": "open",
            "labels": []
        }
        github.update_issue_status.return_value = True
        github.add_labels.return_value = True
        github.add_comment.return_value = True
        return github
    
    @pytest.fixture
    def status_manager(self, mock_github):
        """Create StatusManager instance"""
        return StatusManager(mock_github)
    
    def test_valid_transitions_defined(self, status_manager):
        """Test valid transitions are defined"""
        transitions = status_manager.VALID_TRANSITIONS
        
        assert IssueStatus.BACKLOG in transitions
        assert IssueStatus.READY in transitions[IssueStatus.BACKLOG]
        assert IssueStatus.IN_PROGRESS in transitions[IssueStatus.READY]
        assert IssueStatus.IN_REVIEW in transitions[IssueStatus.IN_PROGRESS]
        assert IssueStatus.DONE in transitions[IssueStatus.IN_REVIEW]
    
    def test_can_transition_valid(self, status_manager):
        """Test valid transition check"""
        # Backlog → Ready
        assert status_manager.can_transition(
            IssueStatus.BACKLOG,
            IssueStatus.READY
        ) is True
        
        # Ready → In Progress
        assert status_manager.can_transition(
            IssueStatus.READY,
            IssueStatus.IN_PROGRESS
        ) is True
        
        # In Progress → In Review
        assert status_manager.can_transition(
            IssueStatus.IN_PROGRESS,
            IssueStatus.IN_REVIEW
        ) is True
    
    def test_can_transition_invalid(self, status_manager):
        """Test invalid transition check"""
        # Cannot skip from Backlog to Done
        assert status_manager.can_transition(
            IssueStatus.BACKLOG,
            IssueStatus.DONE
        ) is False
        
        # Cannot go from Done to In Progress (except via reset)
        assert status_manager.can_transition(
            IssueStatus.DONE,
            IssueStatus.BLOCKED
        ) is False
    
    def test_can_transition_from_done(self, status_manager):
        """Test transitions from Done status"""
        # Can reopen from Done
        assert status_manager.can_transition(
            IssueStatus.DONE,
            IssueStatus.IN_PROGRESS
        ) is True
        
        assert status_manager.can_transition(
            IssueStatus.DONE,
            IssueStatus.READY
        ) is True
    
    def test_transition_success(self, status_manager, mock_github):
        """Test successful status transition"""
        success = status_manager.transition(
            issue_number=123,
            to_status=IssueStatus.READY,
            agent="pm",
            reason="PRD completed"
        )
        
        assert success is True
        
        # Verify GitHub calls
        mock_github.update_issue_status.assert_called_once_with(123, "Ready")
        mock_github.add_labels.assert_called_once()
        mock_github.add_comment.assert_called_once()
    
    def test_transition_invalid_rejected(self, status_manager):
        """Test invalid transition is rejected"""
        with pytest.raises(StatusTransitionError) as exc_info:
            status_manager.transition(
                issue_number=123,
                to_status=IssueStatus.DONE,
                agent="pm",
                reason="Cannot skip"
            )
        
        assert "Invalid transition" in str(exc_info.value)
    
    def test_transition_force_override(self, status_manager, mock_github):
        """Test force parameter overrides validation"""
        # This would normally be invalid
        success = status_manager.transition(
            issue_number=123,
            to_status=IssueStatus.DONE,
            agent="admin",
            reason="Manual override",
            force=True
        )
        
        assert success is True
    
    def test_transition_history_tracking(self, status_manager):
        """Test transitions are tracked in history"""
        status_manager.transition(123, IssueStatus.READY, "pm")
        status_manager.transition(123, IssueStatus.IN_PROGRESS, "engineer")
        
        history = status_manager.get_transition_history(123)
        
        assert len(history) == 2
        assert history[0].issue_number == 123
        assert history[0].from_status == IssueStatus.BACKLOG
        assert history[0].to_status == IssueStatus.READY
        assert history[0].agent == "pm"
        
        assert history[1].from_status == IssueStatus.BACKLOG  # Current status from mock
        assert history[1].to_status == IssueStatus.IN_PROGRESS
    
    def test_get_agent_start_status(self, status_manager):
        """Test getting agent's start status"""
        assert status_manager.get_agent_start_status("pm") == IssueStatus.BACKLOG
        assert status_manager.get_agent_start_status("engineer") == IssueStatus.IN_PROGRESS
        assert status_manager.get_agent_start_status("reviewer") == IssueStatus.IN_REVIEW
    
    def test_get_agent_complete_status(self, status_manager):
        """Test getting agent's complete status"""
        assert status_manager.get_agent_complete_status("pm") == IssueStatus.READY
        assert status_manager.get_agent_complete_status("architect") == IssueStatus.READY
        assert status_manager.get_agent_complete_status("engineer") == IssueStatus.IN_REVIEW
        assert status_manager.get_agent_complete_status("reviewer") == IssueStatus.DONE
    
    def test_get_current_status_from_label(self, status_manager, mock_github):
        """Test reading current status from labels"""
        mock_github.get_issue.return_value = {
            "number": 123,
            "state": "open",
            "labels": [{"name": "status:in-progress"}]
        }
        
        status = status_manager._get_current_status(123)
        assert status == IssueStatus.IN_PROGRESS
    
    def test_get_current_status_from_closed_issue(self, status_manager, mock_github):
        """Test closed issue returns Done status"""
        mock_github.get_issue.return_value = {
            "number": 123,
            "state": "closed",
            "labels": []
        }
        
        status = status_manager._get_current_status(123)
        assert status == IssueStatus.DONE
    
    def test_get_current_status_default(self, status_manager, mock_github):
        """Test default status is Backlog"""
        mock_github.get_issue.return_value = {
            "number": 123,
            "state": "open",
            "labels": []
        }
        
        status = status_manager._get_current_status(123)
        assert status == IssueStatus.BACKLOG
    
    def test_reset_to_ready(self, status_manager, mock_github):
        """Test reset_to_ready convenience method"""
        mock_github.get_issue.return_value = {
            "number": 123,
            "state": "open",
            "labels": [{"name": "status:in-progress"}]
        }
        
        success = status_manager.reset_to_ready(
            123,
            "engineer",
            "Build failed"
        )
        
        assert success is True
        mock_github.update_issue_status.assert_called_with(123, "Ready")
    
    def test_create_transition_comment(self, status_manager):
        """Test transition comment generation"""
        comment = status_manager._create_transition_comment(
            IssueStatus.READY,
            IssueStatus.IN_PROGRESS,
            "engineer",
            "Starting implementation"
        )
        
        assert "Status Update" in comment
        assert "Ready" in comment
        assert "In Progress" in comment
        assert "Engineer Agent" in comment
        assert "Starting implementation" in comment


class TestWorkflowValidator:
    """Test WorkflowValidator class"""
    
    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration"""
        return Config({
            "project": {"name": "Test"},
            "output": {
                "prd_dir": str(tmp_path / "prd"),
                "specs_dir": str(tmp_path / "specs"),
                "adr_dir": str(tmp_path / "adr")
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
        github.search_prs_by_issue.return_value = []
        return github
    
    @pytest.fixture
    def validator(self, config, mock_github):
        """Create WorkflowValidator instance"""
        return WorkflowValidator(config, mock_github)
    
    def test_validate_prerequisites_pm(self, validator):
        """Test PM prerequisites (minimal)"""
        checks = validator.validate_prerequisites(123, "pm")
        
        assert "issue_exists" in checks
        assert "issue_open" in checks
        assert checks["issue_exists"] is True
        assert checks["issue_open"] is True
    
    def test_validate_prerequisites_architect(self, validator, config, tmp_path):
        """Test Architect prerequisites (needs PRD)"""
        # Without PRD
        checks = validator.validate_prerequisites(123, "architect")
        assert checks["prd_exists"] is False
        
        # Create PRD
        prd_dir = tmp_path / "prd"
        prd_dir.mkdir(exist_ok=True)
        (prd_dir / "PRD-123.md").write_text("# PRD")
        
        # With PRD
        checks = validator.validate_prerequisites(123, "architect")
        assert checks["prd_exists"] is True
    
    def test_validate_prerequisites_engineer(self, validator, tmp_path):
        """Test Engineer prerequisites (needs PRD and spec)"""
        # Without documents
        checks = validator.validate_prerequisites(123, "engineer")
        assert checks["prd_exists"] is False
        assert checks["spec_exists"] is False
        
        # Create PRD
        prd_dir = tmp_path / "prd"
        prd_dir.mkdir(exist_ok=True)
        (prd_dir / "PRD-123.md").write_text("# PRD")
        
        checks = validator.validate_prerequisites(123, "engineer")
        assert checks["prd_exists"] is True
        assert checks["spec_exists"] is False
        
        # Create spec
        spec_dir = tmp_path / "specs"
        spec_dir.mkdir(exist_ok=True)
        (spec_dir / "SPEC-123.md").write_text("# Spec")
        
        checks = validator.validate_prerequisites(123, "engineer")
        assert checks["prd_exists"] is True
        assert checks["spec_exists"] is True
    
    def test_validate_prerequisites_reviewer(self, validator, mock_github):
        """Test Reviewer prerequisites (needs PR)"""
        # Without PR
        checks = validator.validate_prerequisites(123, "reviewer")
        assert checks["pr_exists"] is False
        
        # With PR
        mock_github.search_prs_by_issue.return_value = [{"number": 456}]
        checks = validator.validate_prerequisites(123, "reviewer")
        assert checks["pr_exists"] is True
    
    def test_get_missing_prerequisites(self, validator):
        """Test getting list of missing prerequisites"""
        missing = validator.get_missing_prerequisites(123, "architect")
        
        assert "prd_exists" in missing
        assert "issue_exists" not in missing  # This one passes
    
    def test_check_issue_exists(self, validator, mock_github):
        """Test issue existence check"""
        assert validator._check_issue_exists(123) is True
        
        mock_github.get_issue.return_value = None
        assert validator._check_issue_exists(999) is False
    
    def test_check_issue_open(self, validator, mock_github):
        """Test issue open state check"""
        mock_github.get_issue.return_value = {"state": "open"}
        assert validator._check_issue_open(123) is True
        
        mock_github.get_issue.return_value = {"state": "closed"}
        assert validator._check_issue_open(123) is False


class TestStatusTransition:
    """Test StatusTransition dataclass"""
    
    def test_status_transition_creation(self):
        """Test creating status transition"""
        transition = StatusTransition(
            issue_number=123,
            from_status=IssueStatus.READY,
            to_status=IssueStatus.IN_PROGRESS,
            agent="engineer",
            timestamp=datetime.now(),
            reason="Starting work"
        )
        
        assert transition.issue_number == 123
        assert transition.from_status == IssueStatus.READY
        assert transition.to_status == IssueStatus.IN_PROGRESS
        assert transition.agent == "engineer"
        assert transition.reason == "Starting work"
        assert isinstance(transition.timestamp, datetime)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
