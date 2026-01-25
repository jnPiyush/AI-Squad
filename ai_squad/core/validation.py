"""
Prerequisite Validation Framework for AI-Squad

Inspired by Gastown's formula package validation system, this module provides
centralized prerequisite validation for agent execution, ensuring agents cannot
run without required dependencies (PRD, ADR, SPEC, UX designs).

Design Principles (from Gastown):
1. **Validation at Entry Points** - Check before execution, not during
2. **Clear Dependency Chain** - Explicit prerequisites for each agent
3. **Topological Validation** - Respect dependency order
4. **Actionable Errors** - Specific messages about what's missing
5. **Zero Friction Control** - Validate automatically, don't require manual checks

Architecture:
- PrerequisiteValidator: Core validation logic
- PrerequisiteError: Structured error messages
- Dependency Registry: Maps agent types to their prerequisites
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Agent types with specific prerequisites"""
    PM = "pm"
    ARCHITECT = "architect"
    ENGINEER = "engineer"
    UX = "ux"
    REVIEWER = "reviewer"


class PrerequisiteType(Enum):
    """Types of prerequisites that can be required"""
    PRD = "prd"
    ADR = "adr"
    SPEC = "spec"
    UX_DESIGN = "ux_design"
    IMPLEMENTATION = "implementation"


@dataclass
class Prerequisite:
    """Represents a single prerequisite requirement"""
    type: PrerequisiteType
    path_pattern: str  # e.g., "docs/prd/PRD-{issue}.md"
    description: str
    required_by: Set[AgentType]


@dataclass
class ValidationResult:
    """Result of prerequisite validation"""
    valid: bool
    missing_prerequisites: List[Prerequisite]
    error_message: Optional[str] = None
    resolution_hint: Optional[str] = None


class PrerequisiteError(Exception):
    """
    Exception raised when prerequisite validation fails.
    Includes actionable information about missing dependencies.
    """
    def __init__(
        self,
        agent_type: AgentType,
        missing_prerequisites: List[Prerequisite],
        issue_number: Optional[int] = None
    ):
        self.agent_type = agent_type
        self.missing_prerequisites = missing_prerequisites
        self.issue_number = issue_number

        # Build error message
        prereq_names = [p.type.value.upper() for p in missing_prerequisites]
        msg = f"Cannot execute {agent_type.value}: Missing prerequisites: {', '.join(prereq_names)}"

        if issue_number:
            msg += f" for issue #{issue_number}"

        # Add resolution hint
        if PrerequisiteType.PRD in [p.type for p in missing_prerequisites]:
            msg += "\n\nResolution: Run 'squad pm <issue-number>' to create PRD first"
        elif PrerequisiteType.ADR in [p.type for p in missing_prerequisites]:
            msg += "\n\nResolution: Run 'squad architect <issue-number>' to create ADR/SPEC first"
        elif PrerequisiteType.UX_DESIGN in [p.type for p in missing_prerequisites]:
            msg += "\n\nResolution: Run 'squad ux <issue-number>' to create UX design first"

        super().__init__(msg)


class PrerequisiteValidator:
    """
    Centralized prerequisite validation for agent execution.

    Validates that required documents (PRD, ADR, SPEC, UX designs) exist
    before allowing agents to execute. Prevents workflow violations like
    Engineer executing without architecture design.

    Inspired by Gastown's formula validation approach:
    - Validates dependencies before execution
    - Topological ordering of prerequisites
    - Clear, actionable error messages
    """

    # Dependency Registry: Agent Type → Required Prerequisites
    # Follows the standard AI-Squad workflow order
    DEPENDENCIES: Dict[AgentType, List[PrerequisiteType]] = {
        AgentType.PM: [],  # PM has no prerequisites
        AgentType.ARCHITECT: [PrerequisiteType.PRD],  # Architect needs PRD
        AgentType.UX: [PrerequisiteType.PRD],  # UX needs PRD (parallel with Architect)
        AgentType.ENGINEER: [  # Engineer needs PRD, ADR, and optionally UX
            PrerequisiteType.PRD,
            PrerequisiteType.ADR,
            # UX is optional for non-UI features
        ],
        AgentType.REVIEWER: [  # Reviewer needs implementation
            PrerequisiteType.IMPLEMENTATION
        ]
    }

    # Prerequisite definitions with file path patterns
    PREREQUISITE_REGISTRY: Dict[PrerequisiteType, Prerequisite] = {
        PrerequisiteType.PRD: Prerequisite(
            type=PrerequisiteType.PRD,
            path_pattern="docs/prd/PRD-{issue}.md",
            description="Product Requirements Document",
            required_by={AgentType.ARCHITECT, AgentType.UX, AgentType.ENGINEER}
        ),
        PrerequisiteType.ADR: Prerequisite(
            type=PrerequisiteType.ADR,
            path_pattern="docs/adr/ADR-{issue}.md",
            description="Architecture Decision Record",
            required_by={AgentType.ENGINEER}
        ),
        PrerequisiteType.SPEC: Prerequisite(
            type=PrerequisiteType.SPEC,
            path_pattern="docs/specs/SPEC-{issue}.md",
            description="Technical Specification",
            required_by={AgentType.ENGINEER}
        ),
        PrerequisiteType.UX_DESIGN: Prerequisite(
            type=PrerequisiteType.UX_DESIGN,
            path_pattern="docs/ux/UX-{issue}.md",
            description="UX Design Document",
            required_by={AgentType.ENGINEER}  # Optional but recommended
        ),
        PrerequisiteType.IMPLEMENTATION: Prerequisite(
            type=PrerequisiteType.IMPLEMENTATION,
            path_pattern="",  # Validated by PR existence, not file
            description="Implementation Pull Request",
            required_by={AgentType.REVIEWER}
        )
    }

    def __init__(self, workspace_root: Path):
        """
        Initialize validator with workspace root.

        Args:
            workspace_root: Root directory of the AI-Squad workspace
        """
        self.workspace_root = workspace_root
        self.logger = logging.getLogger(__name__)

    def validate(
        self,
        agent_type: AgentType,
        issue_number: Optional[int] = None,
        pr_number: Optional[int] = None,
        strict: bool = True
    ) -> ValidationResult:
        """
        Validate prerequisites for an agent execution.

        Args:
            agent_type: Type of agent to validate
            issue_number: GitHub issue number (for document lookups)
            pr_number: Pull request number (for Reviewer validation)
            strict: If True, raise exception on validation failure

        Returns:
            ValidationResult with validation status and missing prerequisites

        Raises:
            PrerequisiteError: If validation fails and strict=True
        """
        self.logger.info(f"Validating prerequisites for {agent_type.value} (issue={issue_number}, pr={pr_number})")

        # Get required prerequisites for this agent
        required_types = self.DEPENDENCIES.get(agent_type, [])

        missing_prerequisites = []

        for prereq_type in required_types:
            prerequisite = self.PREREQUISITE_REGISTRY[prereq_type]

            # Check if prerequisite exists
            if not self._check_prerequisite_exists(prerequisite, issue_number, pr_number):
                missing_prerequisites.append(prerequisite)
                self.logger.warning(
                    f"Missing prerequisite: {prerequisite.description} "
                    f"({prerequisite.path_pattern.format(issue=issue_number)})"
                )

        # Build result
        if missing_prerequisites:
            result = ValidationResult(
                valid=False,
                missing_prerequisites=missing_prerequisites,
                error_message=self._build_error_message(agent_type, missing_prerequisites),
                resolution_hint=self._build_resolution_hint(agent_type, missing_prerequisites)
            )

            if strict:
                raise PrerequisiteError(agent_type, missing_prerequisites, issue_number)

            return result

        # All prerequisites satisfied
        self.logger.info(f"All prerequisites satisfied for {agent_type.value}")
        return ValidationResult(
            valid=True,
            missing_prerequisites=[]
        )

    def _check_prerequisite_exists(
        self,
        prerequisite: Prerequisite,
        issue_number: Optional[int],
        pr_number: Optional[int]
    ) -> bool:
        """
        Check if a specific prerequisite exists.

        Args:
            prerequisite: Prerequisite to check
            issue_number: Issue number for document lookup
            pr_number: PR number for implementation validation

        Returns:
            True if prerequisite exists, False otherwise
        """
        # Special case: IMPLEMENTATION validated by PR existence, not file
        if prerequisite.type == PrerequisiteType.IMPLEMENTATION:
            # For now, assume PR number provided means implementation exists
            # Future: Could integrate with GitHub API to verify PR state
            return pr_number is not None

        # Standard case: Check file existence
        if not issue_number:
            return False

        file_path = self.workspace_root / prerequisite.path_pattern.format(issue=issue_number)

        exists = file_path.exists()
        if exists:
            self.logger.debug(f"Found prerequisite: {file_path}")
        else:
            self.logger.debug(f"Missing prerequisite: {file_path}")

        return exists

    def _build_error_message(
        self,
        agent_type: AgentType,
        missing_prerequisites: List[Prerequisite]
    ) -> str:
        """Build detailed error message about missing prerequisites"""
        prereq_list = "\n  ".join([
            f"- {p.description} ({p.type.value.upper()})"
            for p in missing_prerequisites
        ])

        return f"""
❌ Prerequisite Validation Failed

Agent: {agent_type.value.upper()}
Missing Prerequisites:
  {prereq_list}

The {agent_type.value} agent cannot execute without these required documents.
This enforces the AI-Squad workflow: PM → Architect → Engineer → Reviewer
"""

    def _build_resolution_hint(
        self,
        agent_type: AgentType,
        missing_prerequisites: List[Prerequisite]
    ) -> str:
        """Build actionable resolution hint"""
        # Determine which agent should run first
        missing_types = {p.type for p in missing_prerequisites}

        if PrerequisiteType.PRD in missing_types:
            return "Run: squad pm <issue-number>"
        elif PrerequisiteType.ADR in missing_types or PrerequisiteType.SPEC in missing_types:
            return "Run: squad architect <issue-number>"
        elif PrerequisiteType.UX_DESIGN in missing_types:
            return "Run: squad ux <issue-number>"
        elif PrerequisiteType.IMPLEMENTATION in missing_types:
            return "Run: squad engineer <issue-number>"

        return "Follow the AI-Squad workflow order: PM → Architect → Engineer → Reviewer"

    def get_ready_agents(
        self,
        issue_number: int,
        completed_agents: Set[AgentType]
    ) -> Set[AgentType]:
        """
        Get agents that are ready to execute based on completed work.

        Inspired by Gastown's ReadySteps pattern - returns agents whose
        all prerequisites have been satisfied.

        Args:
            issue_number: Issue number to check
            completed_agents: Set of agents that have already completed work

        Returns:
            Set of agent types that can execute now
        """
        ready_agents = set()

        for agent_type in AgentType:
            # Skip if already completed
            if agent_type in completed_agents:
                continue

            # Check if all prerequisites are satisfied
            try:
                result = self.validate(agent_type, issue_number, strict=False)
                if result.valid:
                    ready_agents.add(agent_type)
            except PrerequisiteError:
                # Not ready
                pass

        return ready_agents

    def topological_sort_agents(self) -> List[AgentType]:
        """
        Return agents in dependency order (dependencies before dependents).

        Inspired by Gastown's TopologicalSort - ensures agents execute
        in correct order respecting dependencies.

        Returns:
            List of agent types in execution order
        """
        # Build dependency graph
        in_degree = {agent: 0 for agent in AgentType}
        dependents: Dict[AgentType, List[AgentType]] = {agent: [] for agent in AgentType}

        # Calculate in-degrees and build dependents map
        for agent_type, required_prereqs in self.DEPENDENCIES.items():
            in_degree[agent_type] = len(required_prereqs)

            # Find which agents provide these prerequisites
            for prereq_type in required_prereqs:
                prereq = self.PREREQUISITE_REGISTRY[prereq_type]
                # Find agents that produce this prerequisite
                if prereq_type == PrerequisiteType.PRD:
                    dependents[AgentType.PM].append(agent_type)
                elif prereq_type in [PrerequisiteType.ADR, PrerequisiteType.SPEC]:
                    dependents[AgentType.ARCHITECT].append(agent_type)
                elif prereq_type == PrerequisiteType.UX_DESIGN:
                    dependents[AgentType.UX].append(agent_type)
                elif prereq_type == PrerequisiteType.IMPLEMENTATION:
                    dependents[AgentType.ENGINEER].append(agent_type)

        # Kahn's algorithm for topological sort
        queue = [agent for agent, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Pop agent with no dependencies
            agent = queue.pop(0)
            result.append(agent)

            # Reduce in-degree of dependents
            for dependent in dependents[agent]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(AgentType):
            raise ValueError("Cycle detected in agent dependencies")

        return result


def validate_agent_execution(
    agent_type: str,
    issue_number: Optional[int] = None,
    pr_number: Optional[int] = None,
    workspace_root: Optional[Path] = None,
    strict: bool = True
) -> ValidationResult:
    """
    Convenience function for validating agent execution.

    Args:
        agent_type: Agent type as string (pm, architect, engineer, ux, reviewer)
        issue_number: GitHub issue number
        pr_number: Pull request number (for reviewer)
        workspace_root: Workspace root directory (defaults to current directory)
        strict: If True, raise exception on validation failure

    Returns:
        ValidationResult

    Raises:
        PrerequisiteError: If validation fails and strict=True

    Example:
        >>> validate_agent_execution("engineer", issue_number=123)
        >>> # Raises PrerequisiteError if PRD/ADR missing
    """
    # Determine workspace root
    if workspace_root is None:
        workspace_root = Path.cwd()

    # Convert string to enum
    try:
        agent_enum = AgentType(agent_type.lower())
    except ValueError:
        raise ValueError(f"Invalid agent type: {agent_type}. Valid types: {[a.value for a in AgentType]}")

    # Create validator and validate
    validator = PrerequisiteValidator(workspace_root)
    return validator.validate(agent_enum, issue_number, pr_number, strict)
