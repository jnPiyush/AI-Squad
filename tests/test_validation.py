"""
Unit tests for PrerequisiteValidator

Tests validation logic, dependency tracking, and error handling.
"""
import pytest
from pathlib import Path
import tempfile
import shutil
from ai_squad.core.validation import (
    PrerequisiteValidator,
    validate_agent_execution,
    AgentType,
    PrerequisiteType,
    PrerequisiteError,
    ValidationResult,
)


class TestPrerequisiteValidator:
    """Test suite for PrerequisiteValidator"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        workspace = Path(tempfile.mkdtemp())
        yield workspace
        shutil.rmtree(workspace)

    @pytest.fixture
    def workspace_with_prd(self, temp_workspace):
        """Workspace with PRD document"""
        prd_dir = temp_workspace / "docs" / "prd"
        prd_dir.mkdir(parents=True)
        (prd_dir / "PRD-123.md").write_text("# PRD Content")
        return temp_workspace

    @pytest.fixture
    def workspace_with_adr(self, workspace_with_prd):
        """Workspace with PRD and ADR"""
        adr_dir = workspace_with_prd / "docs" / "adr"
        adr_dir.mkdir(parents=True)
        (adr_dir / "ADR-123.md").write_text("# ADR Content")
        return workspace_with_prd

    @pytest.fixture
    def workspace_complete(self, workspace_with_adr):
        """Workspace with all documents"""
        spec_dir = workspace_with_adr / "docs" / "specs"
        spec_dir.mkdir(parents=True)
        (spec_dir / "SPEC-123.md").write_text("# SPEC Content")

        ux_dir = workspace_with_adr / "docs" / "ux"
        ux_dir.mkdir(parents=True)
        (ux_dir / "UX-123.md").write_text("# UX Content")

        return workspace_with_adr

    def test_pm_no_prerequisites(self, temp_workspace):
        """PM should have no prerequisites"""
        validator = PrerequisiteValidator(temp_workspace)
        result = validator.validate(AgentType.PM, issue_number=123, strict=False)
        assert result.valid
        assert len(result.missing_prerequisites) == 0

    def test_architect_requires_prd(self, temp_workspace):
        """Architect should require PRD"""
        validator = PrerequisiteValidator(temp_workspace)
        result = validator.validate(AgentType.ARCHITECT, issue_number=123, strict=False)
        assert not result.valid
        assert len(result.missing_prerequisites) == 1
        assert result.missing_prerequisites[0].type == PrerequisiteType.PRD

    def test_architect_with_prd_succeeds(self, workspace_with_prd):
        """Architect should succeed with PRD"""
        validator = PrerequisiteValidator(workspace_with_prd)
        result = validator.validate(AgentType.ARCHITECT, issue_number=123, strict=False)
        assert result.valid

    def test_engineer_requires_prd_and_adr(self, temp_workspace):
        """Engineer should require PRD and ADR"""
        validator = PrerequisiteValidator(temp_workspace)
        result = validator.validate(AgentType.ENGINEER, issue_number=123, strict=False)
        assert not result.valid
        assert len(result.missing_prerequisites) == 2
        missing_types = {p.type for p in result.missing_prerequisites}
        assert PrerequisiteType.PRD in missing_types
        assert PrerequisiteType.ADR in missing_types

    def test_engineer_with_prd_only_fails(self, workspace_with_prd):
        """Engineer should fail with only PRD (needs ADR too)"""
        validator = PrerequisiteValidator(workspace_with_prd)
        result = validator.validate(AgentType.ENGINEER, issue_number=123, strict=False)
        assert not result.valid
        assert len(result.missing_prerequisites) == 1
        assert result.missing_prerequisites[0].type == PrerequisiteType.ADR

    def test_engineer_with_prd_and_adr_succeeds(self, workspace_with_adr):
        """Engineer should succeed with PRD and ADR"""
        validator = PrerequisiteValidator(workspace_with_adr)
        result = validator.validate(AgentType.ENGINEER, issue_number=123, strict=False)
        assert result.valid

    def test_strict_mode_raises_exception(self, temp_workspace):
        """Strict mode should raise PrerequisiteError"""
        validator = PrerequisiteValidator(temp_workspace)
        with pytest.raises(PrerequisiteError) as exc_info:
            validator.validate(AgentType.ENGINEER, issue_number=123, strict=True)
        
        error = exc_info.value
        assert error.agent_type == AgentType.ENGINEER
        assert len(error.missing_prerequisites) == 2

    def test_topological_sort_correct_order(self, temp_workspace):
        """Topological sort should return correct agent order"""
        validator = PrerequisiteValidator(temp_workspace)
        order = validator.topological_sort_agents()
        
        # PM must come first (no dependencies)
        assert order[0] == AgentType.PM
        
        # Architect and UX can be parallel (both depend on PM)
        pm_idx = order.index(AgentType.PM)
        arch_idx = order.index(AgentType.ARCHITECT)
        ux_idx = order.index(AgentType.UX)
        assert arch_idx > pm_idx
        assert ux_idx > pm_idx
        
        # Engineer must come after Architect
        eng_idx = order.index(AgentType.ENGINEER)
        assert eng_idx > arch_idx
        
        # Reviewer must come last (depends on implementation)
        rev_idx = order.index(AgentType.REVIEWER)
        assert rev_idx > eng_idx

    def test_get_ready_agents_pm_first(self, temp_workspace):
        """Only PM should be ready initially"""
        validator = PrerequisiteValidator(temp_workspace)
        ready = validator.get_ready_agents(issue_number=123, completed_agents=set())
        assert ready == {AgentType.PM}

    def test_get_ready_agents_after_pm(self, workspace_with_prd):
        """Architect and UX should be ready after PM"""
        validator = PrerequisiteValidator(workspace_with_prd)
        ready = validator.get_ready_agents(
            issue_number=123, 
            completed_agents={AgentType.PM}
        )
        # Both Architect and UX can proceed after PM
        assert AgentType.ARCHITECT in ready
        assert AgentType.UX in ready

    def test_get_ready_agents_after_architect(self, workspace_with_adr):
        """Engineer should be ready after Architect"""
        validator = PrerequisiteValidator(workspace_with_adr)
        ready = validator.get_ready_agents(
            issue_number=123,
            completed_agents={AgentType.PM, AgentType.ARCHITECT}
        )
        assert AgentType.ENGINEER in ready

    def test_convenience_function_valid_agent(self, workspace_with_prd):
        """Convenience function should work with valid agent"""
        result = validate_agent_execution(
            agent_type="architect",
            issue_number=123,
            workspace_root=workspace_with_prd,
            strict=False
        )
        assert result.valid

    def test_convenience_function_invalid_agent(self):
        """Convenience function should raise error for invalid agent"""
        with pytest.raises(ValueError, match="Invalid agent type"):
            validate_agent_execution(
                agent_type="invalid_agent",
                issue_number=123
            )

    def test_error_message_contains_resolution_hint(self, temp_workspace):
        """PrerequisiteError should include resolution hint"""
        validator = PrerequisiteValidator(temp_workspace)
        with pytest.raises(PrerequisiteError) as exc_info:
            validator.validate(AgentType.ARCHITECT, issue_number=123, strict=True)
        
        error_message = str(exc_info.value)
        assert "squad pm" in error_message.lower()

    def test_reviewer_requires_implementation(self, temp_workspace):
        """Reviewer should require implementation (PR)"""
        validator = PrerequisiteValidator(temp_workspace)
        result = validator.validate(
            AgentType.REVIEWER,
            issue_number=123,
            pr_number=None,
            strict=False
        )
        assert not result.valid
        assert len(result.missing_prerequisites) == 1
        assert result.missing_prerequisites[0].type == PrerequisiteType.IMPLEMENTATION

    def test_reviewer_with_pr_succeeds(self, temp_workspace):
        """Reviewer should succeed with PR number"""
        validator = PrerequisiteValidator(temp_workspace)
        result = validator.validate(
            AgentType.REVIEWER,
            issue_number=123,
            pr_number=456,
            strict=False
        )
        assert result.valid

    def test_validation_result_structure(self, temp_workspace):
        """ValidationResult should have correct structure"""
        validator = PrerequisiteValidator(temp_workspace)
        result = validator.validate(AgentType.ENGINEER, issue_number=123, strict=False)
        
        assert isinstance(result, ValidationResult)
        assert isinstance(result.valid, bool)
        assert isinstance(result.missing_prerequisites, list)
        assert result.error_message is not None
        assert result.resolution_hint is not None

    def test_multiple_issues_independent(self, workspace_with_prd):
        """Different issues should be validated independently"""
        validator = PrerequisiteValidator(workspace_with_prd)
        
        # Issue 123 has PRD
        result_123 = validator.validate(AgentType.ARCHITECT, issue_number=123, strict=False)
        assert result_123.valid
        
        # Issue 456 doesn't have PRD
        result_456 = validator.validate(AgentType.ARCHITECT, issue_number=456, strict=False)
        assert not result_456.valid


class TestPrerequisiteErrorFormatting:
    """Test error message formatting"""

    def test_error_contains_agent_type(self):
        """Error should identify which agent failed"""
        from ai_squad.core.validation import Prerequisite
        
        prereq = Prerequisite(
            type=PrerequisiteType.PRD,
            path_pattern="docs/prd/PRD-{issue}.md",
            description="Product Requirements Document",
            required_by={AgentType.ARCHITECT}
        )
        
        error = PrerequisiteError(
            agent_type=AgentType.ARCHITECT,
            missing_prerequisites=[prereq],
            issue_number=123
        )
        
        error_msg = str(error)
        assert "architect" in error_msg.lower()
        assert "PRD" in error_msg
        assert "123" in error_msg

    def test_error_contains_resolution_for_prd(self):
        """Error should suggest running PM for missing PRD"""
        from ai_squad.core.validation import Prerequisite
        
        prereq = Prerequisite(
            type=PrerequisiteType.PRD,
            path_pattern="docs/prd/PRD-{issue}.md",
            description="Product Requirements Document",
            required_by={AgentType.ARCHITECT}
        )
        
        error = PrerequisiteError(
            agent_type=AgentType.ARCHITECT,
            missing_prerequisites=[prereq],
            issue_number=123
        )
        
        error_msg = str(error)
        assert "squad pm" in error_msg.lower()

    def test_error_contains_resolution_for_adr(self):
        """Error should suggest running Architect for missing ADR"""
        from ai_squad.core.validation import Prerequisite
        
        prereq = Prerequisite(
            type=PrerequisiteType.ADR,
            path_pattern="docs/adr/ADR-{issue}.md",
            description="Architecture Decision Record",
            required_by={AgentType.ENGINEER}
        )
        
        error = PrerequisiteError(
            agent_type=AgentType.ENGINEER,
            missing_prerequisites=[prereq],
            issue_number=123
        )
        
        error_msg = str(error)
        assert "squad architect" in error_msg.lower()
