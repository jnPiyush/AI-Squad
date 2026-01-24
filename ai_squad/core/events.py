"""
Structured event helpers for orchestration telemetry.
"""
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RoutingEvent:
    """Structured routing event emitted during message dispatch."""

    event_id: str
    timestamp: str
    source: str
    destination: str
    status: str
    execution_mode: str
    message_id: Optional[str] = None
    issue_number: Optional[int] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        *,
        source: str,
        destination: str,
        status: str,
        execution_mode: str,
        message_id: Optional[str] = None,
        issue_number: Optional[int] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "RoutingEvent":
        """Factory helper to build a routing event with defaults."""

        return cls(
            event_id=uuid.uuid4().hex,
            timestamp=datetime.now().isoformat(),
            source=source,
            destination=destination,
            status=status,
            execution_mode=execution_mode,
            message_id=message_id,
            issue_number=issue_number,
            reason=reason,
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to a JSON-serializable dict."""

        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "source": self.source,
            "destination": self.destination,
            "status": self.status,
            "execution_mode": self.execution_mode,
            "message_id": self.message_id,
            "issue_number": self.issue_number,
            "reason": self.reason,
            "metadata": self.metadata,
        }


class StructuredEventEmitter:
    """Persists structured events to .squad/events/*.jsonl."""

    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = workspace_root or Path.cwd()
        self.events_dir = self.workspace_root / ".squad" / "events"
        self.routing_file = self.events_dir / "routing.jsonl"
        self.events_dir.mkdir(parents=True, exist_ok=True)

    def emit_routing(self, event: RoutingEvent) -> None:
        """Append a routing event to the routing log and log it."""

        payload = event.to_dict()
        self.routing_file.parent.mkdir(parents=True, exist_ok=True)
        with self.routing_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
        logger.info("routing_event", extra={"routing_event": payload})
