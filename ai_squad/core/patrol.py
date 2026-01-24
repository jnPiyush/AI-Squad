"""
Patrol cycles for stale work detection.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from ai_squad.core.workstate import WorkStateManager, WorkStatus

logger = logging.getLogger(__name__)


@dataclass
class PatrolEvent:
    event_id: str
    timestamp: str
    work_item_id: str
    status: str
    minutes_stale: int
    last_updated: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "work_item_id": self.work_item_id,
            "status": self.status,
            "minutes_stale": self.minutes_stale,
            "last_updated": self.last_updated,
            "metadata": self.metadata,
        }


class PatrolManager:
    """Detects stale work items and logs escalation events."""

    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        workstate_manager: Optional[WorkStateManager] = None,
        stale_minutes: int = 120,
        statuses: Optional[List[str]] = None,
    ) -> None:
        self.workspace_root = workspace_root or Path.cwd()
        self.workstate_manager = workstate_manager or WorkStateManager(self.workspace_root)
        self.stale_minutes = stale_minutes
        self.statuses = statuses or [WorkStatus.IN_PROGRESS.value, WorkStatus.HOOKED.value, WorkStatus.BLOCKED.value]
        self.events_dir = self.workspace_root / ".squad" / "events"
        self.patrol_file = self.events_dir / "patrol.jsonl"

    def run(self) -> List[PatrolEvent]:
        now = datetime.now()
        stale_cutoff = now - timedelta(minutes=self.stale_minutes)
        stale_events: List[PatrolEvent] = []

        for item in self.workstate_manager.list_work_items():
            if item.status.value not in self.statuses:
                continue
            last_updated = self._parse_timestamp(item.updated_at)
            if last_updated and last_updated <= stale_cutoff:
                minutes_stale = int((now - last_updated).total_seconds() // 60)
                event = PatrolEvent(
                    event_id=uuid.uuid4().hex,
                    timestamp=now.isoformat(),
                    work_item_id=item.id,
                    status=item.status.value,
                    minutes_stale=minutes_stale,
                    last_updated=item.updated_at,
                    metadata={"agent": item.agent_assignee, "priority": item.priority},
                )
                stale_events.append(event)
                self._emit_event(event)

        logger.info("Patrol complete: %d stale items", len(stale_events))
        return stale_events

    def _emit_event(self, event: PatrolEvent) -> None:
        self.events_dir.mkdir(parents=True, exist_ok=True)
        with self.patrol_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=True) + "\n")
        logger.info("patrol_event", extra={"patrol_event": event.to_dict()})

    @staticmethod
    def _parse_timestamp(value: str) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None
