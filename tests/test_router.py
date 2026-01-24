import json

from ai_squad.core.router import Candidate, PolicyRule, OrgRouter, HealthView, HealthConfig
from ai_squad.core.events import StructuredEventEmitter, RoutingEvent


def test_policy_blocks_and_routes(tmp_path):
    policy = PolicyRule(
        allowed_capability_tags=["analysis"],
        denied_capability_tags=["experimental"],
        required_trust_levels=["high"],
        max_data_sensitivity="confidential",
    )
    emitter = StructuredEventEmitter(workspace_root=tmp_path)
    router = OrgRouter(policy, event_emitter=emitter)

    candidates = [
        Candidate(name="pm", capability_tags=["analysis"], trust_level="high", data_sensitivity="internal", latency_ms=50),
        Candidate(name="lab", capability_tags=["experimental"], trust_level="medium", data_sensitivity="public", latency_ms=10),
    ]

    chosen = router.route(
        candidates=candidates,
        requested_capability_tags=["analysis"],
        data_sensitivity="internal",
        trust_level="high",
    )

    assert chosen.name == "pm"

    # Health view should see routing event
    hv = HealthView(tmp_path)
    summary = hv.summarize()
    assert summary["routed"] == 1


def test_circuit_breaker_blocks_candidate(tmp_path):
    policy = PolicyRule(
        allowed_capability_tags=["analysis"],
        required_trust_levels=["high"],
        max_data_sensitivity="confidential",
    )
    emitter = StructuredEventEmitter(workspace_root=tmp_path)
    health_cfg = HealthConfig(min_events=3, circuit_breaker_block_rate=0.6, throttle_block_rate=0.5, warn_block_rate=0.2, critical_block_rate=0.5)

    # Seed blocked events to trip circuit breaker
    for _ in range(3):
        emitter.emit_routing(
            RoutingEvent.create(
                source="test",
                destination="pm",
                status="blocked",
                execution_mode="org",
                reason="seed_block",
            )
        )

    hv = HealthView(tmp_path, window=50)
    health = hv.destination_health("pm", health_cfg)
    assert health["circuit_open"]

    router = OrgRouter(policy, event_emitter=emitter, health_config=health_cfg, workspace_root=tmp_path)
    candidates = [Candidate(name="pm", capability_tags=["analysis"], trust_level="high", data_sensitivity="internal")]
    chosen = router.route(
        candidates=candidates,
        requested_capability_tags=["analysis"],
        data_sensitivity="internal",
        trust_level="high",
    )

    assert chosen is None

    last_event = json.loads((tmp_path / ".squad" / "events" / "routing.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert last_event["reason"] == "circuit_breaker"


def test_throttle_prefers_healthier_candidate(tmp_path):
    policy = PolicyRule(
        allowed_capability_tags=["analysis"],
        required_trust_levels=["high"],
        max_data_sensitivity="confidential",
    )
    emitter = StructuredEventEmitter(workspace_root=tmp_path)
    health_cfg = HealthConfig(min_events=3, circuit_breaker_block_rate=0.9, throttle_block_rate=0.5)

    # Seed throttled history for pm (50% block rate over 4 events)
    for status in ("blocked", "blocked", "routed", "routed"):
        emitter.emit_routing(
            RoutingEvent.create(
                source="test",
                destination="pm",
                status=status,
                execution_mode="org",
                reason="seed",
            )
        )

    candidates = [
        Candidate(name="pm", capability_tags=["analysis"], trust_level="high", data_sensitivity="internal", latency_ms=5),
        Candidate(name="architect", capability_tags=["analysis"], trust_level="high", data_sensitivity="internal", latency_ms=10),
    ]

    router = OrgRouter(policy, event_emitter=emitter, health_config=health_cfg, workspace_root=tmp_path)
    chosen = router.route(
        candidates=candidates,
        requested_capability_tags=["analysis"],
        data_sensitivity="internal",
        trust_level="high",
        priority="urgent",
    )

    assert chosen.name == "architect"  # prefers non-throttled


def test_throttled_candidate_used_as_fallback(tmp_path):
    policy = PolicyRule(
        allowed_capability_tags=["analysis"],
        required_trust_levels=["high"],
        max_data_sensitivity="confidential",
    )
    emitter = StructuredEventEmitter(workspace_root=tmp_path)
    health_cfg = HealthConfig(min_events=2, circuit_breaker_block_rate=0.9, throttle_block_rate=0.5)

    # pm is throttled but not circuit open (50% block rate over 2 events)
    for status in ("blocked", "routed"):
        emitter.emit_routing(
            RoutingEvent.create(
                source="test",
                destination="pm",
                status=status,
                execution_mode="org",
                reason="seed",
            )
        )

    candidates = [Candidate(name="pm", capability_tags=["analysis"], trust_level="high", data_sensitivity="internal")]

    router = OrgRouter(policy, event_emitter=emitter, health_config=health_cfg, workspace_root=tmp_path)
    chosen = router.route(
        candidates=candidates,
        requested_capability_tags=["analysis"],
        data_sensitivity="internal",
        trust_level="high",
        priority="normal",
    )

    assert chosen.name == "pm"
    last_event = json.loads((tmp_path / ".squad" / "events" / "routing.jsonl").read_text(encoding="utf-8").splitlines()[-1])
    assert last_event["reason"] == "throttled_route"


def test_health_view_priority_aggregation(tmp_path):
    emitter = StructuredEventEmitter(workspace_root=tmp_path)
    emitter.emit_routing(
        RoutingEvent.create(
            source="org_router",
            destination="pm",
            status="routed",
            execution_mode="org",
            reason="policy_check",
            metadata={"priority": "urgent"},
        )
    )

    hv = HealthView(tmp_path, window=10)
    summary = hv.summarize(config=HealthConfig(min_events=1))
    assert summary["by_priority"]["urgent"]["routed"] == 1
    assert summary["overall_status"] == "healthy"
