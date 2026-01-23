"""Core package initialization"""

from ai_squad.core.agent_executor import AgentExecutor
from ai_squad.core.config import Config
from ai_squad.core.init_project import initialize_project

# Gastown-inspired orchestration modules
from ai_squad.core.workstate import WorkItem, WorkStateManager, WorkStatus
from ai_squad.core.formula import (
    Formula,
    FormulaStep,
    FormulaManager,
    FormulaExecutor,
    FormulaExecution,
)
from ai_squad.core.captain import Captain, TaskBreakdown, ConvoyPlan
from ai_squad.core.convoy import (
    Convoy,
    ConvoyMember,
    ConvoyManager,
    ConvoyBuilder,
    ConvoyStatus,
)
from ai_squad.core.mailbox import (
    Message,
    Mailbox,
    MailboxManager,
    MessagePriority,
    MessageStatus,
)
from ai_squad.core.handoff import (
    Handoff,
    HandoffContext,
    HandoffManager,
    HandoffStatus,
    HandoffReason,
)

__all__ = [
    # Original exports
    "AgentExecutor",
    "Config",
    "initialize_project",
    # WorkState
    "WorkItem",
    "WorkStateManager",
    "WorkStatus",
    # Formula
    "Formula",
    "FormulaStep",
    "FormulaManager",
    "FormulaExecutor",
    "FormulaExecution",
    # Captain
    "Captain",
    "TaskBreakdown",
    "ConvoyPlan",
    # Convoy
    "Convoy",
    "ConvoyMember",
    "ConvoyManager",
    "ConvoyBuilder",
    "ConvoyStatus",
    # Mailbox
    "Message",
    "Mailbox",
    "MailboxManager",
    "MessagePriority",
    "MessageStatus",
    # Handoff
    "Handoff",
    "HandoffContext",
    "HandoffManager",
    "HandoffStatus",
    "HandoffReason",
]
