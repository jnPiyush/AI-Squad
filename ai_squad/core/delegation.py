"""Delegation API with audit trail and completion propagation."""
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import uuid
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_squad.core.signal import SignalManager, MessagePriority

logger = logging.getLogger(__name__)


class DelegationStatus(str, Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class DelegationLink:
    """Represents a delegation link with audit trail."""

    id: str
    from_agent: str
    to_agent: str
    work_item_id: str
    scope: str
    sla: Optional[str] = None
    status: DelegationStatus = DelegationStatus.INITIATED
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    audit_log: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "work_item_id": self.work_item_id,
            "scope": self.scope,
            "sla": self.sla,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "audit_log": self.audit_log,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DelegationLink":
        data = data.copy()
        data["status"] = DelegationStatus(data["status"])
        return cls(**data)

    def add_audit(self, action: str, details: str) -> None:
        self.audit_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
        })


class DelegationManager:
    """Manages delegation links and propagates completion to originator."""

    def __init__(self, workspace_root: Optional[Path] = None, signal_manager: Optional[SignalManager] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.signal_manager = signal_manager
        self.delegations_dir = self.workspace_root / ".squad" / "delegations"
        self.delegations_file = self.delegations_dir / "delegations.json"
        self.delegations_dir.mkdir(parents=True, exist_ok=True)
        self._delegations: Dict[str, DelegationLink] = {}
        self._load()

    def create_delegation(
        self,
        *,
        from_agent: str,
        to_agent: str,
        work_item_id: str,
        scope: str,
        sla: Optional[str] = None,
    ) -> DelegationLink:
        link_id = f"delegation-{uuid.uuid4().hex[:8]}"
        link = DelegationLink(
            id=link_id,
            from_agent=from_agent,
            to_agent=to_agent,
            work_item_id=work_item_id,
            scope=scope,
            sla=sla,
        )
        link.add_audit("created", f"Delegation created from {from_agent} to {to_agent}")
        self._delegations[link_id] = link
        self._save()

        try:
            from ai_squad.core.operational_graph import OperationalGraph, NodeType, EdgeType

            graph = OperationalGraph(self.workspace_root)
            graph.add_node(from_agent, NodeType.AGENT, {"agent": from_agent})
            graph.add_node(to_agent, NodeType.AGENT, {"agent": to_agent})
            graph.add_node(work_item_id, NodeType.WORK_ITEM, {"work_item_id": work_item_id})
            graph.add_edge(from_agent, to_agent, EdgeType.DELEGATES_TO, {"delegation_id": link_id})
            graph.add_edge(work_item_id, to_agent, EdgeType.DELEGATES_TO, {"delegation_id": link_id})
        except (ValueError, OSError, RuntimeError) as e:
            logger.warning("Operational graph update failed for delegation %s: %s", link_id, e)

        if self.signal_manager:
            self.signal_manager.send_message(
                sender="system",
                recipient=to_agent,
                subject=f"Delegation Request: {work_item_id}",
                body=f"{from_agent} delegated work item {work_item_id}",
                priority=MessagePriority.NORMAL,
                work_item_id=work_item_id,
                metadata={"delegation_id": link_id},
            )

        logger.info("delegation_created", extra={"delegation": link.to_dict()})
        return link

    def complete_delegation(self, link_id: str, *, status: DelegationStatus = DelegationStatus.COMPLETED, details: str = "") -> Optional[DelegationLink]:
        link = self._delegations.get(link_id)
        if not link:
            return None
        link.status = status
        link.completed_at = datetime.now().isoformat()
        link.add_audit("completed", details or f"Delegation marked {status.value}")
        self._save()

        if self.signal_manager:
            self.signal_manager.send_message(
                sender="system",
                recipient=link.from_agent,
                subject=f"Delegation {status.value}: {link.work_item_id}",
                body=f"{link.to_agent} reported {status.value} for {link.work_item_id}",
                priority=MessagePriority.HIGH,
                work_item_id=link.work_item_id,
                metadata={"delegation_id": link_id, "status": status.value},
            )

        logger.info("delegation_completed", extra={"delegation": link.to_dict()})
        return link

    def get(self, link_id: str) -> Optional[DelegationLink]:
        return self._delegations.get(link_id)

    def list(self) -> List[DelegationLink]:
        return list(self._delegations.values())

    def _save(self) -> None:
        self.delegations_dir.mkdir(parents=True, exist_ok=True)
        payload = {link_id: link.to_dict() for link_id, link in self._delegations.items()}
        self.delegations_file.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")

    def _load(self) -> None:
        if not self.delegations_file.exists():
            return
        try:
            data = json.loads(self.delegations_file.read_text(encoding="utf-8"))
            self._delegations = {
                link_id: DelegationLink.from_dict(meta)
                for link_id, meta in data.items()
            }
        except json.JSONDecodeError:
            logger.warning("Delegations file corrupted; resetting")
            self._delegations = {}
