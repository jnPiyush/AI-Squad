"""Core package initialization"""

from ai_squad.core.agent_executor import AgentExecutor
from ai_squad.core.config import Config
from ai_squad.core.init_project import initialize_project

# Gastown-inspired orchestration modules
from ai_squad.core.workstate import WorkItem, WorkStateManager, WorkStatus
from ai_squad.core.battle_plan import (
    BattlePlan,
    BattlePlanPhase,
    BattlePlanManager,
    BattlePlanExecutor,
    BattlePlanExecution,
)
from ai_squad.core.captain import Captain, TaskBreakdown, ConvoyPlan
from ai_squad.core.convoy import (
    Convoy,
    ConvoyMember,
    ConvoyManager,
    ConvoyBuilder,
    ConvoyStatus,
)
from ai_squad.core.signal import (
    Signal,
    SignalManager,
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
    # Battle Plan
    "BattlePlan",
    "BattlePlanPhase",
    "BattlePlanManager",
    "BattlePlanExecutor",
    "BattlePlanExecution",
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
    # Signal
    "Signal",
    "SignalManager",
    "MessagePriority",
    "MessageStatus",
    # Handoff
    "Handoff",
    "HandoffContext",
    "HandoffManager",
    "HandoffStatus",
    "HandoffReason",
]
