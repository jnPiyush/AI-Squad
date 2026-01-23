"""
Constants Module

Centralized constants for AI-Squad to avoid magic strings throughout the codebase.
"""
from enum import Enum


class AgentType(str, Enum):
    """Agent type identifiers"""
    PM = "pm"
    ARCHITECT = "architect"
    ENGINEER = "engineer"
    UX = "ux"
    REVIEWER = "reviewer"
    
    @classmethod
    def all(cls) -> list:
        """Get all agent types"""
        return [agent.value for agent in cls]


class OrchestrationLabel(str, Enum):
    """Labels used for orchestration flow"""
    PM_DONE = "orch:pm-done"
    ARCHITECT_DONE = "orch:architect-done"
    ENGINEER_DONE = "orch:engineer-done"
    UX_DONE = "orch:ux-done"
    REVIEWER_DONE = "orch:reviewer-done"


class StatusLabel(str, Enum):
    """Labels used for status tracking"""
    BACKLOG = "status:backlog"
    READY = "status:ready"
    IN_PROGRESS = "status:in-progress"
    IN_REVIEW = "status:in-review"
    DONE = "status:done"
    BLOCKED = "status:blocked"


class IssueLabel(str, Enum):
    """Standard issue type labels"""
    EPIC = "type:epic"
    FEATURE = "type:feature"
    STORY = "type:story"
    BUG = "type:bug"
    TASK = "type:task"


class ReviewOutcome(str, Enum):
    """Code review outcomes"""
    APPROVE = "APPROVE"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    COMMENT = "COMMENT"


# Agent flow mapping: when one agent completes, which agent should run next
AGENT_FLOW = {
    OrchestrationLabel.PM_DONE.value: AgentType.ARCHITECT.value,
    OrchestrationLabel.ARCHITECT_DONE.value: AgentType.ENGINEER.value,
    OrchestrationLabel.ENGINEER_DONE.value: AgentType.REVIEWER.value,
}

# Status-based triggers: which agents can start based on status
STATUS_TRIGGERS = {
    StatusLabel.READY.value: [AgentType.ARCHITECT.value, AgentType.UX.value],
    StatusLabel.IN_REVIEW.value: [AgentType.REVIEWER.value],
}

# Output directories (relative paths)
OUTPUT_DIRS = {
    AgentType.PM.value: "docs/prd",
    AgentType.ARCHITECT.value: "docs/adr",
    AgentType.ENGINEER.value: "src",
    AgentType.UX.value: "docs/ux",
    AgentType.REVIEWER.value: "docs/reviews",
}

# Default file patterns for each agent output
OUTPUT_PATTERNS = {
    AgentType.PM.value: "PRD-{issue}.md",
    AgentType.ARCHITECT.value: "ADR-{issue}.md",
    AgentType.UX.value: "UX-{issue}.md",
    AgentType.REVIEWER.value: "REVIEW-{issue}.md",
}

# Quality thresholds (can be overridden by config)
DEFAULT_TEST_COVERAGE = 80
DEFAULT_TEST_PYRAMID = {
    "unit": 70,
    "integration": 20,
    "e2e": 10,
}

# Accessibility standards
DEFAULT_WCAG_VERSION = "2.1"
DEFAULT_WCAG_LEVEL = "AA"
DEFAULT_CONTRAST_RATIO = 4.5

# Performance targets
DEFAULT_RESPONSE_TIME_P95_MS = 200
DEFAULT_THROUGHPUT_REQ_PER_SEC = 1000

# Design breakpoints
DEFAULT_BREAKPOINTS = {
    "mobile": "320px-767px",
    "tablet": "768px-1023px",
    "desktop": "1024px+",
}
DEFAULT_TOUCH_TARGET_MIN = "44px"
