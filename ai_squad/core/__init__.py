"""Core package initialization"""

from ai_squad.core.agent_executor import AgentExecutor
from ai_squad.core.config import Config
from ai_squad.core.init_project import initialize_project

# AI Provider chain (Copilot -> OpenAI -> Azure -> Template)
from ai_squad.core.ai_provider import (
    AIProviderChain,
    AIProviderType,
    AIResponse,
    get_ai_provider,
    generate_content,
)

# AI-Squad orchestration modules
from ai_squad.core.workstate import WorkItem, WorkStateManager, WorkStatus
from ai_squad.core.hooks import HookManager
from ai_squad.core.worker_lifecycle import WorkerLifecycleManager
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
from ai_squad.core.capability_registry import CapabilityRegistry
from ai_squad.core.delegation import DelegationManager, DelegationStatus
from ai_squad.core.router import OrgRouter, PolicyRule, HealthView
from ai_squad.core.discovery import DiscoveryIndex
from ai_squad.core.identity import IdentityDossier, IdentityManager
from ai_squad.core.scout_worker import ScoutWorker
from ai_squad.core.operational_graph import OperationalGraph, NodeType, EdgeType

__all__ = [
    # Original exports
    "AgentExecutor",
    "Config",
    "initialize_project",
    # WorkState
    "WorkItem",
    "WorkStateManager",
    "WorkStatus",
    "HookManager",
    "WorkerLifecycleManager",
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
    # Enhancements
    "CapabilityRegistry",
    "DelegationManager",
    "DelegationStatus",
    "OrgRouter",
    "PolicyRule",
    "HealthView",
    "DiscoveryIndex",
    "IdentityDossier",
    "IdentityManager",
    "ScoutWorker",
    "OperationalGraph",
    "NodeType",
    "EdgeType",
]
