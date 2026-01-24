"""Organization-plane routing with policy checks and health aggregation."""
from dataclasses import dataclass, field
import json
import logging
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ai_squad.core.events import StructuredEventEmitter, RoutingEvent

logger = logging.getLogger(__name__)


@dataclass
class Candidate:
    """A route candidate (agent/model) with attributes."""

    name: str
    capability_tags: List[str] = field(default_factory=list)
    trust_level: str = "low"
    data_sensitivity: str = "public"
    latency_ms: Optional[int] = None


@dataclass
class PolicyRule:
    """Policy constraints for routing."""

    allowed_capability_tags: List[str] = field(default_factory=list)
    denied_capability_tags: List[str] = field(default_factory=list)
    required_trust_levels: List[str] = field(default_factory=list)
    max_data_sensitivity: str = "confidential"  # public|internal|confidential|restricted

    def permits(self, candidate: Candidate, requested_tags: List[str], sensitivity: str, trust: str) -> bool:
        if self.allowed_capability_tags:
            if not set(requested_tags).intersection(self.allowed_capability_tags):
                return False
        if set(candidate.capability_tags).intersection(self.denied_capability_tags):
            return False
        if self.required_trust_levels and trust not in self.required_trust_levels:
            return False
        sensitivity_rank = self._rank_sensitivity(sensitivity)
        max_rank = self._rank_sensitivity(self.max_data_sensitivity)
        if sensitivity_rank > max_rank:
            return False
        return True

    @staticmethod
    def _rank_sensitivity(level: str) -> int:
        order = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
        return order.get(level, 3)


@dataclass
class HealthConfig:
    """Health thresholds and circuit breaker settings."""

    warn_block_rate: float = 0.25
    critical_block_rate: float = 0.5
    circuit_breaker_block_rate: float = 0.7
    throttle_block_rate: float = 0.5
    min_events: int = 5
    window: int = 200  # number of recent events to consider

    def score(self, block_rate: float, total: int) -> str:
        if total < self.min_events:
            return "insufficient_data"
        if block_rate >= self.critical_block_rate:
            return "critical"
        if block_rate >= self.warn_block_rate:
            return "warn"
        return "healthy"


class OrgRouter:
    """Organization-plane router enforcing policy rules with health checks."""

    def __init__(
        self,
        policy: PolicyRule,
        event_emitter: Optional[StructuredEventEmitter] = None,
        health_config: Optional[HealthConfig] = None,
        workspace_root: Optional[Path] = None,
    ):
        self.policy = policy
        self.event_emitter = event_emitter or StructuredEventEmitter(workspace_root=workspace_root)
        self.health_config = health_config or HealthConfig()
        self.health_view = HealthView(workspace_root=workspace_root or getattr(self.event_emitter, "workspace_root", None), window=self.health_config.window)

    def route(
        self,
        *,
        candidates: List[Candidate],
        requested_capability_tags: List[str],
        data_sensitivity: str,
        trust_level: str,
        priority: str = "normal",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Candidate]:
        metadata = metadata or {}
        viable = [c for c in candidates if self.policy.permits(c, requested_capability_tags, data_sensitivity, trust_level)]
        healthy_candidates: List[Tuple[Candidate, Dict[str, Any]]] = []
        throttled_candidates: List[Tuple[Candidate, Dict[str, Any]]] = []
        circuit_blocked: List[Tuple[Candidate, Dict[str, Any]]] = []

        for candidate in viable:
            health = self.health_view.destination_health(candidate.name, self.health_config)
            if health.get("circuit_open"):
                circuit_blocked.append((candidate, health))
                continue
            if health.get("throttled"):
                throttled_candidates.append((candidate, health))
                continue
            healthy_candidates.append((candidate, health))
        chosen = None
        if healthy_candidates:
            # Pick lowest latency if available; otherwise first viable
            with_latency = [c for c, _ in healthy_candidates if c.latency_ms is not None]
            if with_latency:
                chosen = min(with_latency, key=lambda c: c.latency_ms)
            else:
                chosen = healthy_candidates[0][0]
        elif throttled_candidates:
            with_latency = [c for c, _ in throttled_candidates if c.latency_ms is not None]
            if with_latency:
                chosen = min(with_latency, key=lambda c: c.latency_ms)
            else:
                chosen = throttled_candidates[0][0]

        block_reason = "policy_block"
        if not healthy_candidates and circuit_blocked:
            block_reason = "circuit_breaker"
        if not healthy_candidates and throttled_candidates and not chosen:
            block_reason = "throttled"

        status = "routed" if chosen else "blocked"
        reason = "policy_check"
        if not chosen:
            reason = block_reason
        elif throttled_candidates and chosen.name in [c.name for c, _ in throttled_candidates]:
            reason = "throttled_route"
        event = RoutingEvent.create(
            source="org_router",
            destination=chosen.name if chosen else "none",
            status=status,
            execution_mode="org",
            message_id=None,
            issue_number=None,
            reason=reason,
            metadata={
                "requested_capability_tags": requested_capability_tags,
                "data_sensitivity": data_sensitivity,
                "trust_level": trust_level,
                "viable": [c.name for c in viable],
                "metadata": metadata,
                "priority": priority,
                "health": {
                    c.name: h for c, h in healthy_candidates
                },
                "throttled": {c.name: h for c, h in throttled_candidates},
                "circuit_blocked": [c.name for c, _ in circuit_blocked],
            },
        )
        self.event_emitter.emit_routing(event)
        return chosen


class HealthView:
    """Aggregated health view using routing events."""

    def __init__(self, workspace_root: Optional[Path] = None, window: int = 200):
        self.workspace_root = workspace_root or Path.cwd()
        self.events_dir = self.workspace_root / ".squad" / "events"
        self.routing_file = self.events_dir / "routing.jsonl"
        self.window = window

    def _load_events(self) -> List[Dict[str, Any]]:
        if not self.routing_file.exists():
            return []
        events: deque = deque(maxlen=self.window)
        for line in self.routing_file.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return list(events)

    def summarize(self, config: Optional[HealthConfig] = None) -> Dict[str, Any]:
        events = self._load_events()
        stats: Dict[str, Any] = {
            "total": 0,
            "routed": 0,
            "blocked": 0,
            "not_implemented": 0,
            "by_source": {},
            "by_destination": {},
            "by_priority": {},
        }

        for event in events:
            status = event.get("status", "unknown")
            source = event.get("source", "unknown")
            destination = event.get("destination", "unknown")
            meta = event.get("metadata", {}) or {}
            priority = meta.get("priority", "normal")

            stats["total"] += 1
            if status in stats:
                stats[status] += 1

            stats["by_source"].setdefault(source, {"total": 0, "routed": 0, "blocked": 0})
            stats["by_destination"].setdefault(destination, {"total": 0, "routed": 0, "blocked": 0})
            stats["by_priority"].setdefault(priority, {"total": 0, "routed": 0, "blocked": 0})

            stats["by_source"][source]["total"] += 1
            stats["by_destination"][destination]["total"] += 1
            stats["by_priority"][priority]["total"] += 1

            if status == "routed":
                stats["by_source"][source]["routed"] += 1
                stats["by_destination"][destination]["routed"] += 1
                stats["by_priority"][priority]["routed"] += 1
            elif status == "blocked":
                stats["by_source"][source]["blocked"] += 1
                stats["by_destination"][destination]["blocked"] += 1
                stats["by_priority"][priority]["blocked"] += 1

        if config:
            block_rate = stats["blocked"] / stats["total"] if stats["total"] else 0.0
            stats["overall_status"] = config.score(block_rate, stats["total"])
            stats["block_rate"] = block_rate

        return stats

    def destination_health(self, destination: str, config: HealthConfig) -> Dict[str, Any]:
        events = [e for e in self._load_events() if e.get("destination") == destination]
        total = len(events)
        blocked = len([e for e in events if e.get("status") == "blocked"])
        routed = len([e for e in events if e.get("status") == "routed"])
        block_rate = blocked / total if total else 0.0
        status = config.score(block_rate, total)
        throttled = block_rate >= config.throttle_block_rate and total >= config.min_events
        circuit_open = block_rate >= config.circuit_breaker_block_rate and total >= config.min_events
        last_timestamp = events[-1].get("timestamp") if events else None
        return {
            "total": total,
            "blocked": blocked,
            "routed": routed,
            "block_rate": block_rate,
            "status": status,
            "throttled": throttled,
            "circuit_open": circuit_open,
            "last_timestamp": last_timestamp,
        }
