# AI-Squad Orchestration Enhancements

## Goals
- Strengthen multi-agent coordination with clear planes and provenance.
- Improve portability of workflows and skills across orgs and projects.
- Make routing, delegation, and health signals explicit and auditable.

## Proposed Architecture (Battle Plan + Signal terminology)
- Control planes: Command HQ (organization plane) for policy, routing, telemetry; Mission Squad (project plane) for Battle Plan execution, caching, and Signals.
- Operational graph: Map work items, agents, skills, repos, and environments as nodes with typed edges (depends_on, delegates_to, mirrors, owns, emits, consumes).
- Capability registry: Versioned skill packs and workflow packs with capability tags, checksums, signatures, and upgrade/downgrade paths; scopes for public, org, and project.
- Strategy/Template resolution: Three-tier lookup for strategies/templates/prompts (system → org → project) with resolution traces and force-tier overrides.
- Delegation channel: First-class API to create and close delegation links with scope, SLA, and audit; completion bubbles up automatically via Signals.
- Identity dossiers: Workspace and agent identity documents bundled with outputs (commits, summaries, plans) for routing and trust (IdentityManager + identity.json).
- Scout workers: Non-LLM task workers as state-machine executors with checkpoints; reserve LLM calls for planning and reasoning (ScoutWorker + checkpoints in .squad/scout_workers).
- Health and escalation: Config-driven severity routes, throttles, circuit breakers, and a ready/health view aggregated by source and priority from routing Signals.
- Discovery: Optional remotes with opt-in metadata; allow filtered remote queries (project, actor, status) while preserving privacy boundaries.
- Observability: Structured events for routing decisions, resolution paths, delegation links, and execution outcomes; expose traces and audits to users.
- Policy-aware routing: Combine capability tags, trust level, and data sensitivity to select agents/models; enforce guardrails per plane.

## Incremental Rollout (implemented)
- Phase 1 (done): Resolution tracing and force-tier overrides for templates/prompts; structured routing events persisted to `.squad/events/routing.jsonl`.
- Phase 2 (done): Capability registry with manifest validation, checksum verification, and install/upgrade/list across scopes via `.squad/capabilities`.
- Phase 3 (done): Delegation API with audit log and automatic completion propagation back to originator via SignalManager.
- Phase 4 (done): Organization-plane router enforcing policy checks with aggregated health summary from routing events.
- Phase 5 (done): Remote discovery index with privacy defaults and scoped query filters.

## Implementation Notes
- Keep taxonomy aligned to AI-Squad agents: Product Manager, Architect, Engineer, UX Designer, Reviewer.
- Treat workflows and skills as first-class packages, not embedded constants; maintain semantic versioning and provenance.
- Prefer explicit graphs over implicit hierarchies to improve impact analysis and routing quality.
- Use lightweight workers for monitoring/retry/cleanup to avoid LLM burn and improve concurrency.
- Surface “why” everywhere: chosen workflow, tier, policy match, capability match, and delegation lineage.
