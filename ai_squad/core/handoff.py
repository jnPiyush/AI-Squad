"""
Handoff Protocol

Explicit work transfer between agents with context preservation.
Ensures smooth transitions and accountability tracking.
"""
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_squad.core.runtime_paths import resolve_runtime_dir

from .workstate import WorkItem, WorkStateManager, WorkStatus
from .signal import SignalManager, MessagePriority

logger = logging.getLogger(__name__)


class HandoffStatus(str, Enum):
    """Handoff status states"""
    INITIATED = "initiated"       # Handoff started
    PENDING = "pending"           # Waiting for acceptance
    ACCEPTED = "accepted"         # Recipient accepted
    REJECTED = "rejected"         # Recipient rejected
    IN_PROGRESS = "in_progress"   # Transfer in progress
    COMPLETED = "completed"       # Handoff complete
    CANCELLED = "cancelled"       # Handoff cancelled
    FAILED = "failed"             # Handoff failed


class HandoffReason(str, Enum):
    """Reasons for handoff"""
    WORKFLOW = "workflow"          # Normal workflow transition
    ESCALATION = "escalation"      # Escalation to higher authority
    SPECIALIZATION = "specialization"  # Need specialist expertise
    LOAD_BALANCING = "load_balancing"  # Redistribute work
    BLOCKER = "blocker"            # Current agent blocked
    COMPLETION = "completion"      # Work phase complete
    ERROR = "error"                # Error requires different handling


@dataclass
class HandoffContext:
    """
    Context passed during a handoff.
    Ensures recipient has all necessary information.
    """
    summary: str                         # Brief summary of work done
    current_state: str                   # Current state description
    next_steps: List[str] = field(default_factory=list)  # Recommended actions
    blockers: List[str] = field(default_factory=list)    # Known blockers
    artifacts: List[str] = field(default_factory=list)   # Created artifacts
    notes: str = ""                      # Additional notes
    data: Dict[str, Any] = field(default_factory=dict)   # Arbitrary data
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "summary": self.summary,
            "current_state": self.current_state,
            "next_steps": self.next_steps,
            "blockers": self.blockers,
            "artifacts": self.artifacts,
            "notes": self.notes,
            "data": self.data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HandoffContext":
        """Create from dictionary"""
        return cls(**data)


@dataclass
class Handoff:
    """
    A handoff record tracking work transfer between agents.
    """
    id: str
    work_item_id: str
    from_agent: str
    to_agent: str
    reason: HandoffReason
    status: str = HandoffStatus.INITIATED.value
    
    # Context
    context: Optional[HandoffContext] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    requires_ack: bool = True
    
    # Timestamps
    initiated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    accepted_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    # Response
    acceptance_message: Optional[str] = None
    rejection_reason: Optional[str] = None
    
    # Audit trail
    audit_log: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        reason_value = self.reason.value if hasattr(self.reason, "value") else str(self.reason)
        return {
            "id": self.id,
            "work_item_id": self.work_item_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "reason": reason_value,
            "status": self.status,
            "context": self.context.to_dict() if self.context else None,
            "metadata": self.metadata,
            "priority": self.priority.value,
            "requires_ack": self.requires_ack,
            "initiated_at": self.initiated_at,
            "accepted_at": self.accepted_at,
            "completed_at": self.completed_at,
            "acceptance_message": self.acceptance_message,
            "rejection_reason": self.rejection_reason,
            "audit_log": self.audit_log
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Handoff":
        """Create from dictionary"""
        data = data.copy()
        if "reason" in data:
            try:
                data["reason"] = HandoffReason(data["reason"])
            except ValueError:
                # Preserve raw reason strings that are not enumerated
                data["reason"] = data["reason"]
        if "priority" in data:
            data["priority"] = MessagePriority(data["priority"])
        if data.get("context"):
            data["context"] = HandoffContext.from_dict(data["context"])
        return cls(**data)
    
    def add_audit_entry(
        self,
        action: str,
        agent: str,
        details: Optional[str] = None
    ) -> None:
        """Add an entry to the audit log"""
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "agent": agent,
            "details": details
        })


class HandoffManager:
    """
    Manages handoffs between agents.
    
    Persists handoffs to .squad/handoffs/ directory.
    """
    
    HANDOFFS_DIR = "handoffs"
    HANDOFFS_FILE = "handoffs.json"
    
    def __init__(
        self,
        work_state_manager: Any,
        signal_manager: Optional[SignalManager] = None,
        delegation_manager: Optional[Any] = None,
        workspace_root: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        base_dir: Optional[str] = None,
    ):
        """
        Initialize handoff manager.
        
        Args:
            work_state_manager: Work state manager instance
            signal_manager: Optional signal manager for notifications
            workspace_root: Workspace root directory
        """
        if isinstance(work_state_manager, WorkStateManager):
            self.work_state_manager = work_state_manager
        else:
            self.work_state_manager = WorkStateManager(Path(work_state_manager))
        self.signal_manager = signal_manager
        self.delegation_manager = delegation_manager
        self.workspace_root = workspace_root or Path.cwd()
        runtime_dir = resolve_runtime_dir(self.workspace_root, config=config, base_dir=base_dir)
        self.handoffs_dir = runtime_dir / self.HANDOFFS_DIR
        
        self._handoffs: Dict[str, Handoff] = {}
        self._load_state()
    
    def _ensure_handoffs_dir(self) -> None:
        """Create handoffs directory if it doesn't exist"""
        self.handoffs_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self) -> None:
        """Load handoffs from disk"""
        handoffs_file = self.handoffs_dir / self.HANDOFFS_FILE
        if handoffs_file.exists():
            try:
                data = json.loads(handoffs_file.read_text(encoding="utf-8"))
                self._handoffs = {
                    h_id: Handoff.from_dict(h_data)
                    for h_id, h_data in data.items()
                }
                logger.info("Loaded %d handoffs", len(self._handoffs))
            except (json.JSONDecodeError, KeyError) as e:
                logger.error("Failed to load handoffs: %s", e)
                self._handoffs = {}
    
    def _save_state(self) -> None:
        """Save handoffs to disk"""
        self._ensure_handoffs_dir()
        
        handoffs_file = self.handoffs_dir / self.HANDOFFS_FILE
        data = {
            h_id: h.to_dict()
            for h_id, h in self._handoffs.items()
        }
        handoffs_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )
    
    # Handoff Operations
    
    def initiate_handoff(
        self,
        work_item_id: str,
        from_agent: str,
        to_agent: str,
        reason: HandoffReason,
        context: Optional[HandoffContext] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        requires_ack: bool = True
    ) -> Optional[Handoff]:
        """
        Initiate a handoff from one agent to another.
        
        Args:
            work_item_id: ID of work item being handed off
            from_agent: Source agent
            to_agent: Target agent
            reason: Reason for handoff
            context: Handoff context with details
            priority: Priority level
            requires_ack: Whether acknowledgment is required
            
        Returns:
            Created Handoff or None if work item not found
        """
        # Normalize work item input (tests may pass WorkItem object)
        work_item = None
        if isinstance(work_item_id, WorkItem):
            work_item = work_item_id
            work_item_id = work_item.id
        # Verify work item exists
        self.work_state_manager.reload_state()
        work_item = work_item or self.work_state_manager.get_work_item(work_item_id)
        if not work_item:
            logger.error("Work item not found: %s", work_item_id)
            return None

        # Normalize context input (tests may pass raw dict)
        if context and not isinstance(context, HandoffContext):
            context = HandoffContext(
                summary=str(context),
                current_state="",
                next_steps=[],
                blockers=[],
                artifacts=[],
                notes="",
                data=context if isinstance(context, dict) else {}
            )
        
        # Normalize reason (allow raw strings from callers/tests)
        if not isinstance(reason, HandoffReason):
            try:
                reason = HandoffReason(reason)
            except ValueError:
                # Preserve arbitrary text reasons while keeping type safety elsewhere
                pass

        # Create handoff
        handoff_id = f"handoff-{uuid.uuid4().hex[:8]}"
        
        handoff = Handoff(
            id=handoff_id,
            work_item_id=work_item_id,
            from_agent=from_agent,
            to_agent=to_agent,
            reason=reason,
            context=context,
            priority=priority,
            requires_ack=requires_ack,
            metadata={},
        )
        
        handoff.add_audit_entry(
            action="initiated",
            agent=from_agent,
            details=f"Handoff initiated: {reason.value if hasattr(reason, 'value') else reason}"
        )
        
        # Update status
        handoff.status = HandoffStatus.PENDING.value
        
        self._handoffs[handoff_id] = handoff
        self._save_state()

        try:
            from ai_squad.core.operational_graph import OperationalGraph, NodeType, EdgeType

            graph = OperationalGraph(self.workspace_root)
            graph.add_node(from_agent, NodeType.AGENT, {"agent": from_agent})
            graph.add_node(to_agent, NodeType.AGENT, {"agent": to_agent})
            graph.add_node(work_item_id, NodeType.WORK_ITEM, {"title": work_item.title})
            graph.add_edge(from_agent, to_agent, EdgeType.DELEGATES_TO, {"handoff_id": handoff_id})
            graph.add_edge(work_item_id, to_agent, EdgeType.DELEGATES_TO, {"handoff_id": handoff_id})
        except (ValueError, OSError, RuntimeError) as e:
            logger.warning("Operational graph update failed for handoff %s: %s", handoff_id, e)

        if self.delegation_manager:
            try:
                delegation = self.delegation_manager.create_delegation(
                    from_agent=from_agent,
                    to_agent=to_agent,
                    work_item_id=work_item_id,
                    scope=reason.value if hasattr(reason, "value") else str(reason),
                )
                handoff.metadata["delegation_id"] = delegation.id
                handoff.add_audit_entry(
                    action="delegation_created",
                    agent=from_agent,
                    details=f"Delegation {delegation.id} created",
                )
                self._save_state()
            except (ValueError, OSError, RuntimeError) as e:
                logger.warning("Delegation create failed for handoff %s: %s", handoff_id, e)
        
        # Send notification via signal
        if self.signal_manager:
            context_summary = ""
            if context:
                context_summary = f"\n\n**Summary**: {context.summary}\n**Current State**: {context.current_state}"
                if context.next_steps:
                    context_summary += "\n**Next Steps**:\n" + "\n".join(
                        f"- {step}" for step in context.next_steps
                    )

            self.signal_manager.send_message(
                sender=from_agent,
                recipient=to_agent,
                subject=f"Handoff Request: {work_item.title}",
                body=f"Work item handoff request from {from_agent}.\n\n"
                     f"**Reason**: {reason.value if hasattr(reason, 'value') else reason}\n"
                     f"**Work Item**: {work_item.title} ({work_item_id})"
                     f"{context_summary}",
                priority=priority,
                requires_ack=requires_ack,
                work_item_id=work_item_id,
                metadata={"handoff_id": handoff_id, **({"delegation_id": handoff.metadata.get("delegation_id")} if handoff.metadata else {})}
            )
        
        logger.info(
            "Handoff initiated: %s -> %s for %s (reason: %s)",
            from_agent, to_agent, work_item_id, reason.value if hasattr(reason, "value") else reason
        )
        
        return handoff
    
    def accept_handoff(
        self,
        handoff_id: str,
        accepting_agent: Optional[str] = None,
        message: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Accept a handoff.
        
        Args:
            handoff_id: Handoff ID
            accepting_agent: Agent accepting the handoff
            message: Optional acceptance message
            
        Returns:
            True if accepted successfully
        """
        # Support legacy/aliased parameter name "agent"
        accepting_agent = accepting_agent or kwargs.pop("agent", None)

        handoff = self.get_handoff(handoff_id)
        if not handoff:
            return False
        
        # Verify accepting agent is the intended recipient
        if handoff.to_agent != accepting_agent:
            logger.warning(
                "Agent %s cannot accept handoff intended for %s",
                accepting_agent, handoff.to_agent
            )
            return False
        
        # Verify handoff is pending
        if handoff.status != HandoffStatus.PENDING.value:
            logger.warning(
                "Cannot accept handoff in status %s",
                handoff.status
            )
            return False
        
        # Update handoff
        handoff.status = HandoffStatus.ACCEPTED.value
        handoff.accepted_at = datetime.now().isoformat()
        handoff.acceptance_message = message
        
        handoff.add_audit_entry(
            action="accepted",
            agent=accepting_agent,
            details=message
        )
        
        # Update work item assignment
        self.work_state_manager.reload_state()
        assignment_ok = self.work_state_manager.assign_to_agent(
            handoff.work_item_id,
            accepting_agent
        )
        # Move work into active state for recipient
        if assignment_ok:
            self.work_state_manager.transition_status(
                handoff.work_item_id,
                WorkStatus.IN_PROGRESS
            )
        else:
            logger.error("Failed to assign work item %s to %s", handoff.work_item_id, accepting_agent)
        
        self._save_state()
        
        # Send confirmation via signal
        if self.signal_manager:
            self.signal_manager.send_message(
                sender=accepting_agent,
                recipient=handoff.from_agent,
                subject=f"Handoff Accepted: {handoff.work_item_id}",
                body=f"Handoff accepted by {accepting_agent}."
                     + (f"\n\nMessage: {message}" if message else ""),
                work_item_id=handoff.work_item_id,
                metadata={"handoff_id": handoff_id}
            )
        
        logger.info(
            "Handoff accepted: %s by %s",
            handoff_id, accepting_agent
        )
        
        return True
    
    def reject_handoff(
        self,
        handoff_id: str,
        rejecting_agent: str,
        reason: str
    ) -> bool:
        """
        Reject a handoff.
        
        Args:
            handoff_id: Handoff ID
            rejecting_agent: Agent rejecting the handoff
            reason: Rejection reason
            
        Returns:
            True if rejected successfully
        """
        handoff = self.get_handoff(handoff_id)
        if not handoff:
            return False
        
        if handoff.to_agent != rejecting_agent:
            logger.warning(
                "Agent %s cannot reject handoff intended for %s",
                rejecting_agent, handoff.to_agent
            )
            return False
        
        if handoff.status != HandoffStatus.PENDING.value:
            logger.warning(
                "Cannot reject handoff in status %s",
                handoff.status
            )
            return False
        
        handoff.status = HandoffStatus.REJECTED.value
        handoff.rejection_reason = reason
        
        handoff.add_audit_entry(
            action="rejected",
            agent=rejecting_agent,
            details=reason
        )
        
        self._save_state()

        if self.delegation_manager and handoff.metadata.get("delegation_id"):
            try:
                from ai_squad.core.delegation import DelegationStatus

                self.delegation_manager.complete_delegation(
                    handoff.metadata["delegation_id"],
                    status=DelegationStatus.FAILED,
                    details=reason,
                )
            except (ValueError, OSError, RuntimeError) as e:
                logger.warning("Delegation rejection failed for %s: %s", handoff_id, e)
        
        # Send notification via signal
        if self.signal_manager:
            self.signal_manager.send_message(
                sender=rejecting_agent,
                recipient=handoff.from_agent,
                subject=f"Handoff Rejected: {handoff.work_item_id}",
                body=f"Handoff rejected by {rejecting_agent}.\n\n"
                     f"**Reason**: {reason}",
                priority=MessagePriority.HIGH,
                work_item_id=handoff.work_item_id,
                metadata={"handoff_id": handoff_id}
            )
        
        logger.info(
            "Handoff rejected: %s by %s (reason: %s)",
            handoff_id, rejecting_agent, reason
        )
        
        return True
    
    def complete_handoff(
        self,
        handoff_id: str,
        completing_agent: str
    ) -> bool:
        """
        Mark a handoff as complete.
        
        Args:
            handoff_id: Handoff ID
            completing_agent: Agent completing the handoff
            
        Returns:
            True if completed successfully
        """
        handoff = self.get_handoff(handoff_id)
        if not handoff:
            return False
        
        if handoff.to_agent != completing_agent:
            return False
        
        if handoff.status != HandoffStatus.ACCEPTED.value:
            return False
        
        handoff.status = HandoffStatus.COMPLETED.value
        handoff.completed_at = datetime.now().isoformat()
        
        handoff.add_audit_entry(
            action="completed",
            agent=completing_agent,
            details="Handoff completed"
        )
        
        self._save_state()

        if self.delegation_manager and handoff.metadata.get("delegation_id"):
            try:
                from ai_squad.core.delegation import DelegationStatus

                self.delegation_manager.complete_delegation(
                    handoff.metadata["delegation_id"],
                    status=DelegationStatus.COMPLETED,
                    details="Handoff completed",
                )
            except (ValueError, OSError, RuntimeError) as e:
                logger.warning("Delegation completion failed for %s: %s", handoff_id, e)
        
        logger.info("Handoff completed: %s", handoff_id)
        return True
    
    def cancel_handoff(
        self,
        handoff_id: str,
        cancelling_agent: str,
        reason: str
    ) -> bool:
        """
        Cancel a handoff.
        
        Args:
            handoff_id: Handoff ID
            cancelling_agent: Agent cancelling the handoff
            reason: Cancellation reason
            
        Returns:
            True if cancelled successfully
        """
        handoff = self.get_handoff(handoff_id)
        if not handoff:
            return False
        
        # Only initiator can cancel
        if handoff.from_agent != cancelling_agent:
            return False
        
        if handoff.status not in (HandoffStatus.INITIATED.value, HandoffStatus.PENDING.value):
            return False
        
        handoff.status = HandoffStatus.CANCELLED.value
        handoff.add_audit_entry(
            action="cancelled",
            agent=cancelling_agent,
            details=reason
        )
        
        self._save_state()

        if self.delegation_manager and handoff.metadata.get("delegation_id"):
            try:
                from ai_squad.core.delegation import DelegationStatus

                self.delegation_manager.complete_delegation(
                    handoff.metadata["delegation_id"],
                    status=DelegationStatus.CANCELLED,
                    details=reason,
                )
            except (ValueError, OSError, RuntimeError) as e:
                logger.warning("Delegation cancel failed for %s: %s", handoff_id, e)
        
        # Notify recipient
        if self.signal_manager:
            self.signal_manager.send_message(
                sender=cancelling_agent,
                recipient=handoff.to_agent,
                subject=f"Handoff Cancelled: {handoff.work_item_id}",
                body=f"Handoff cancelled by {cancelling_agent}.\n\n"
                     f"**Reason**: {reason}",
                work_item_id=handoff.work_item_id,
                metadata={"handoff_id": handoff_id}
            )
        
        logger.info(
            "Handoff cancelled: %s by %s",
            handoff_id, cancelling_agent
        )
        
        return True
    
    # Query Methods
    
    def get_handoff(self, handoff_id: str) -> Optional[Handoff]:
        """Get a handoff by ID"""
        return self._handoffs.get(handoff_id)
    
    def get_handoffs_by_work_item(self, work_item_id: str) -> List[Handoff]:
        """Get all handoffs for a work item"""
        return [
            h for h in self._handoffs.values()
            if h.work_item_id == work_item_id
        ]
    
    def get_pending_handoffs(self, to_agent: str) -> List[Handoff]:
        """Get pending handoffs for an agent"""
        return [
            h for h in self._handoffs.values()
            if h.to_agent == to_agent and h.status == HandoffStatus.PENDING
        ]
    
    def get_outgoing_handoffs(
        self,
        from_agent: str,
        status: Optional[HandoffStatus] = None
    ) -> List[Handoff]:
        """Get handoffs initiated by an agent"""
        handoffs = [
            h for h in self._handoffs.values()
            if h.from_agent == from_agent
        ]
        
        if status:
            handoffs = [h for h in handoffs if h.status == status]
        
        return sorted(handoffs, key=lambda h: h.initiated_at, reverse=True)
    
    def get_handoff_history(self, work_item_id: str) -> List[Dict[str, Any]]:
        """
        Get complete handoff history for a work item.
        
        Returns chronological list of all handoff events.
        """
        handoffs = self.get_handoffs_by_work_item(work_item_id)
        
        history = []
        for handoff in handoffs:
            for entry in handoff.audit_log:
                history.append({
                    "handoff_id": handoff.id,
                    "from_agent": handoff.from_agent,
                    "to_agent": handoff.to_agent,
                    **entry
                })
        
        return sorted(history, key=lambda e: e["timestamp"])
    
    # Statistics
    
    def get_stats(self) -> Dict[str, Any]:
        """Get handoff statistics"""
        handoffs = list(self._handoffs.values())
        
        status_counts = {}
        for status in HandoffStatus:
            status_counts[status.value] = len([
                h for h in handoffs if h.status == status.value
            ])
        
        reason_counts = {}
        for reason in HandoffReason:
            reason_counts[reason.value] = len([
                h for h in handoffs if h.reason == reason
            ])
        
        # Calculate average acceptance time
        accepted_handoffs = [
            h for h in handoffs
            if h.accepted_at and h.initiated_at
        ]
        
        avg_acceptance_time = None
        if accepted_handoffs:
            times = []
            for h in accepted_handoffs:
                initiated = datetime.fromisoformat(h.initiated_at)
                accepted = datetime.fromisoformat(h.accepted_at)
                times.append((accepted - initiated).total_seconds())
            avg_acceptance_time = sum(times) / len(times)
        
        return {
            "total": len(handoffs),
            "by_status": status_counts,
            "by_reason": reason_counts,
            "pending": status_counts.get("pending", 0),
            "completed": status_counts.get("completed", 0),
            "rejected": status_counts.get("rejected", 0),
            "avg_acceptance_time_seconds": avg_acceptance_time
        }


# Convenience functions for common handoff patterns

def workflow_handoff(
    handoff_manager: HandoffManager,
    work_item_id: str,
    from_agent: str,
    to_agent: str,
    summary: str,
    next_steps: List[str],
    artifacts: Optional[List[str]] = None
) -> Optional[Handoff]:
    """
    Standard workflow handoff between agents.
    
    Used when work naturally flows from one agent to another.
    """
    context = HandoffContext(
        summary=summary,
        current_state="Phase complete, ready for next phase",
        next_steps=next_steps,
        artifacts=artifacts or []
    )
    
    return handoff_manager.initiate_handoff(
        work_item_id=work_item_id,
        from_agent=from_agent,
        to_agent=to_agent,
        reason=HandoffReason.WORKFLOW,
        context=context
    )


def escalation_handoff(
    handoff_manager: HandoffManager,
    work_item_id: str,
    from_agent: str,
    to_agent: str,
    issue: str,
    blockers: List[str]
) -> Optional[Handoff]:
    """
    Escalation handoff for issues requiring higher authority.
    """
    context = HandoffContext(
        summary=f"Escalation required: {issue}",
        current_state="Blocked - requires escalation",
        blockers=blockers,
        notes="This work item requires attention from a higher authority or specialist."
    )
    
    return handoff_manager.initiate_handoff(
        work_item_id=work_item_id,
        from_agent=from_agent,
        to_agent=to_agent,
        reason=HandoffReason.ESCALATION,
        context=context,
        priority=MessagePriority.URGENT
    )


def specialist_handoff(
    handoff_manager: HandoffManager,
    work_item_id: str,
    from_agent: str,
    specialist_agent: str,
    specialty_needed: str,
    current_progress: str
) -> Optional[Handoff]:
    """
    Handoff to a specialist agent.
    """
    context = HandoffContext(
        summary=f"Specialist needed: {specialty_needed}",
        current_state=current_progress,
        next_steps=[
            f"Apply {specialty_needed} expertise",
            "Complete specialized work",
            "Hand back to original agent if needed"
        ]
    )
    
    return handoff_manager.initiate_handoff(
        work_item_id=work_item_id,
        from_agent=from_agent,
        to_agent=specialist_agent,
        reason=HandoffReason.SPECIALIZATION,
        context=context,
        priority=MessagePriority.HIGH
    )

