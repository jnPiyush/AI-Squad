"""
Status Management System

Manages issue status transitions and workflow states.
"""
from enum import Enum
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime


class IssueStatus(Enum):
    """Standard issue statuses"""
    BACKLOG = "Backlog"
    READY = "Ready"
    IN_PROGRESS = "In Progress"
    IN_REVIEW = "In Review"
    DONE = "Done"
    BLOCKED = "Blocked"
    
    @classmethod
    def from_string(cls, status: str) -> Optional["IssueStatus"]:
        """Get status enum from string"""
        for s in cls:
            if s.value.lower() == status.lower():
                return s
        return None


class StatusTransitionError(Exception):
    """Raised when an invalid status transition is attempted"""


@dataclass
class StatusTransition:
    """Represents a status transition event"""
    issue_number: int
    from_status: IssueStatus
    to_status: IssueStatus
    agent: str
    timestamp: datetime
    reason: Optional[str] = None


class StatusManager:
    """Manages issue status transitions with validation"""
    
    # Define valid status transitions
    VALID_TRANSITIONS: Dict[IssueStatus, Set[IssueStatus]] = {
        IssueStatus.BACKLOG: {IssueStatus.READY, IssueStatus.BLOCKED},
        IssueStatus.READY: {IssueStatus.IN_PROGRESS, IssueStatus.BLOCKED},
        IssueStatus.IN_PROGRESS: {IssueStatus.IN_REVIEW, IssueStatus.BLOCKED, IssueStatus.READY},
        IssueStatus.IN_REVIEW: {IssueStatus.IN_PROGRESS, IssueStatus.DONE, IssueStatus.BLOCKED},
        IssueStatus.BLOCKED: {IssueStatus.READY, IssueStatus.IN_PROGRESS, IssueStatus.BACKLOG},
        IssueStatus.DONE: set(),  # Terminal state
    }
    
    # Agent to status mapping (supports both short and full names)
    AGENT_STATUS_TRANSITIONS: Dict[str, Dict[str, IssueStatus]] = {
        "pm": {
            "start": IssueStatus.BACKLOG,
            "complete": IssueStatus.READY,
        },
        "productmanager": {
            "start": IssueStatus.BACKLOG,
            "complete": IssueStatus.READY,
        },
        "architect": {
            "start": IssueStatus.READY,
            "complete": IssueStatus.READY,
        },
        "ux": {
            "start": IssueStatus.READY,
            "complete": IssueStatus.READY,
        },
        "uxdesigner": {
            "start": IssueStatus.READY,
            "complete": IssueStatus.READY,
        },
        "engineer": {
            "start": IssueStatus.IN_PROGRESS,
            "complete": IssueStatus.IN_REVIEW,
        },
        "reviewer": {
            "start": IssueStatus.IN_REVIEW,
            "complete": IssueStatus.DONE,
        },
    }
    
    def __init__(self, github_tool):
        """
        Initialize status manager
        
        Args:
            github_tool: GitHub tool instance for API calls
        """
        self.github = github_tool
        self.transition_history: List[StatusTransition] = []
    
    def can_transition(self, from_status: IssueStatus, to_status: IssueStatus) -> bool:
        """
        Check if a status transition is valid
        
        Args:
            from_status: Current status
            to_status: Target status
            
        Returns:
            True if transition is valid
        """
        if from_status == IssueStatus.DONE:
            # Can reopen from Done
            return to_status in {IssueStatus.IN_PROGRESS, IssueStatus.READY}
        
        return to_status in self.VALID_TRANSITIONS.get(from_status, set())
    
    def transition(
        self,
        issue_number: int,
        to_status: IssueStatus,
        agent: str,
        reason: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """
        Transition issue to new status
        
        Args:
            issue_number: GitHub issue number
            to_status: Target status
            agent: Agent making the transition
            reason: Optional reason for transition
            force: Skip validation if True
            
        Returns:
            True if successful
            
        Raises:
            StatusTransitionError: If transition is invalid
        """
        # Get current status
        current_status = self._get_current_status(issue_number)
        
        # Skip if already in target status
        if current_status == to_status:
            return True
        
        # Validate transition
        if not force and not self.can_transition(current_status, to_status):
            raise StatusTransitionError(
                f"Invalid transition: {current_status.value} → {to_status.value}"
            )
        
        # Perform transition
        try:
            # Update GitHub issue status
            self.github.update_issue_status(issue_number, to_status.value)
            
            # Add label for tracking
            status_label = f"status:{to_status.value.lower().replace(' ', '-')}"
            self.github.add_labels(issue_number, [status_label])
            
            # Add comment
            comment = self._create_transition_comment(
                current_status, to_status, agent, reason
            )
            self.github.add_comment(issue_number, comment)
            
            # Record transition
            transition = StatusTransition(
                issue_number=issue_number,
                from_status=current_status,
                to_status=to_status,
                agent=agent,
                timestamp=datetime.now(),
                reason=reason
            )
            self.transition_history.append(transition)
            
            return True
            
        except (ConnectionError, TimeoutError, OSError) as e:
            raise StatusTransitionError(f"Failed to transition status: {e}") from e
    
    def get_agent_start_status(self, agent: str) -> IssueStatus:
        """Get the status an agent should set when starting"""
        return self.AGENT_STATUS_TRANSITIONS.get(agent, {}).get(
            "start", IssueStatus.IN_PROGRESS
        )
    
    def get_agent_complete_status(self, agent: str) -> IssueStatus:
        """Get the status an agent should set when completing"""
        return self.AGENT_STATUS_TRANSITIONS.get(agent, {}).get(
            "complete", IssueStatus.READY
        )
    
    def _get_current_status(self, issue_number: int) -> IssueStatus:
        """Get current issue status"""
        try:
            issue = self.github.get_issue(issue_number)
            
            # Check labels first
            labels = [label.get("name", "") for label in issue.get("labels", [])]
            for label in labels:
                if label.startswith("status:"):
                    status_str = label.replace("status:", "").replace("-", " ")
                    status = IssueStatus.from_string(status_str)
                    if status:
                        return status
            
            # Check if issue is closed
            if issue.get("state") == "closed":
                return IssueStatus.DONE
            
            # Default to backlog
            return IssueStatus.BACKLOG
            
        except (ConnectionError, TimeoutError, KeyError):
            return IssueStatus.BACKLOG

    def get_current_status(self, issue_number: int) -> IssueStatus:
        """Public wrapper for retrieving current status"""
        return self._get_current_status(issue_number)
    
    def _create_transition_comment(
        self,
        from_status: IssueStatus,
        to_status: IssueStatus,
        agent: str,
        reason: Optional[str]
    ) -> str:
        """Create GitHub comment for status transition"""
        comment = "🔄 **Status Update**\n\n"
        comment += f"**{from_status.value}** → **{to_status.value}**\n\n"
        comment += f"*Updated by {agent.title()} Agent*\n"
        
        if reason:
            comment += f"\n**Reason**: {reason}\n"
        
        comment += f"\n*{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
        
        return comment

    def create_transition_comment(
        self,
        from_status: IssueStatus,
        to_status: IssueStatus,
        agent: str,
        reason: Optional[str]
    ) -> str:
        """Public wrapper for transition comment generation"""
        return self._create_transition_comment(from_status, to_status, agent, reason)
    
    def get_transition_history(self, issue_number: int) -> List[StatusTransition]:
        """Get transition history for an issue"""
        return [
            t for t in self.transition_history
            if t.issue_number == issue_number
        ]
    
    def reset_to_ready(self, issue_number: int, agent: str, reason: str) -> bool:
        """Reset issue to Ready status (common for failures/changes)"""
        return self.transition(
            issue_number,
            IssueStatus.READY,
            agent,
            reason,
            force=True
        )


class WorkflowValidator:
    """Validates workflow prerequisites and requirements"""
    
    def __init__(self, config, github_tool):
        """
        Initialize workflow validator
        
        Args:
            config: AI-Squad configuration
            github_tool: GitHub tool instance
        """
        self.config = config
        self.github = github_tool
    
    def validate_prerequisites(
        self,
        issue_number: int,
        agent: str
    ) -> Dict[str, bool]:
        """
        Validate prerequisites for agent execution
        
        Args:
            issue_number: GitHub issue number
            agent: Agent to validate for
            
        Returns:
            Dict of prerequisite checks
        """
        checks = {
            "issue_exists": self._check_issue_exists(issue_number),
            "issue_open": self._check_issue_open(issue_number),
        }
        
        if agent == "architect":
            checks["prd_exists"] = self._check_prd_exists(issue_number)
        
        elif agent == "engineer":
            checks["spec_exists"] = self._check_spec_exists(issue_number)
            checks["prd_exists"] = self._check_prd_exists(issue_number)
        
        elif agent == "reviewer":
            checks["pr_exists"] = self._check_pr_exists(issue_number)
        
        return checks
    
    def _check_issue_exists(self, issue_number: int) -> bool:
        """Check if issue exists"""
        try:
            issue = self.github.get_issue(issue_number)
            return issue is not None
        except (ConnectionError, TimeoutError, KeyError):
            return False
    
    def _check_issue_open(self, issue_number: int) -> bool:
        """Check if issue is open"""
        try:
            issue = self.github.get_issue(issue_number)
            if issue is None:
                return False
            # Handle both 'open' and 'OPEN' (GitHub API inconsistency)
            state = issue.get("state", "").lower()
            return state == "open"
        except (ConnectionError, TimeoutError, KeyError):
            return False

    def check_issue_exists(self, issue_number: int) -> bool:
        """Public wrapper for issue existence check"""
        return self._check_issue_exists(issue_number)

    def check_issue_open(self, issue_number: int) -> bool:
        """Public wrapper for open issue check"""
        return self._check_issue_open(issue_number)

    def check_prd_exists(self, issue_number: int) -> bool:
        """Public wrapper for PRD existence"""
        return self._check_prd_exists(issue_number)

    def check_spec_exists(self, issue_number: int) -> bool:
        """Public wrapper for spec existence"""
        return self._check_spec_exists(issue_number)

    def check_pr_exists(self, issue_number: int) -> bool:
        """Public wrapper for PR existence"""
        return self._check_pr_exists(issue_number)
    
    def _check_prd_exists(self, issue_number: int) -> bool:
        """Check if PRD exists for issue"""
        prd_path = self.config.prd_dir / f"PRD-{issue_number}.md"
        return prd_path.exists()
    
    def _check_spec_exists(self, issue_number: int) -> bool:
        """Check if technical spec exists"""
        spec_path = self.config.specs_dir / f"SPEC-{issue_number}.md"
        return spec_path.exists()
    
    def _check_pr_exists(self, issue_number: int) -> bool:
        """Check if PR exists for issue"""
        try:
            # Search for PRs referencing this issue
            prs = self.github.search_prs_by_issue(issue_number)
            return len(prs) > 0
        except (ConnectionError, TimeoutError, KeyError):
            return False
    
    def get_missing_prerequisites(
        self,
        issue_number: int,
        agent: str
    ) -> List[str]:
        """Get list of missing prerequisites"""
        checks = self.validate_prerequisites(issue_number, agent)
        return [name for name, passed in checks.items() if not passed]
