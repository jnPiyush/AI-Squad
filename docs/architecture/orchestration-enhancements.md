# AI-Squad Orchestration Enhancements

## Goals
- Strengthen multi-agent coordination with clear planes and provenance.
- Improve portability of workflows and skills across orgs and projects.
- Make routing, delegation, and health signals explicit and auditable.

## Proposed Architecture (Combat-Inspired AI-Squad Terms)
- Control planes: Command HQ (organization plane) for policy, routing, telemetry; Mission Squad (project plane) for execution and caching.
- Operational graph: Map work items, agents, skills, repos, and environments as nodes with typed edges (depends_on, delegates_to, mirrors, owns, emits, consumes).
- Capability armory: Versioned skill packs and workflow packs with capability tags, checksums, signatures, and upgrade/downgrade paths; scopes for public, org, and project.
- Playbook resolution: Three-tier lookup for templates and prompts (system → org → project) with resolution traces and force-tier overrides.
- Delegation channel: First-class API to create and close delegation links with scope, SLA, and audit; completion bubbles up automatically.
- Identity dossiers: Workspace and agent identity documents bundled with outputs (commits, summaries, plans) for routing and trust.
- Scout workers: Non-LLM task workers as state-machine executors with checkpoints; reserve LLM calls for planning and reasoning.
- Health and escalation: Config-driven severity routes, throttles, circuit breakers, and a ready/health view aggregated by source and priority.
- Discovery: Optional remotes with opt-in metadata; allow filtered remote queries (project, actor, status) while preserving privacy boundaries.
- Observability: Structured events for routing decisions, resolution paths, delegation links, and execution outcomes; expose traces and audits to users.
- Policy-aware routing: Combine capability tags, trust level, and data sensitivity to select agents/models; enforce guardrails per plane.

## Incremental Rollout
- Phase 1: Add resolution tracing and force-tier overrides for templates/prompts; emit structured routing events.
- Phase 2: Introduce capability registry schema and signed packages; support install/upgrade/list across scopes.
- Phase 3: Implement delegation API with audit trail and automatic completion propagation.
- Phase 4: Add organization-plane router with policy checks and aggregated health view; keep project-plane executors as-is.
- Phase 5: Enable remote discovery endpoints with privacy defaults and query filters.

## Implementation Notes
- Keep taxonomy aligned to AI-Squad agents: Product Manager, Architect, Engineer, UX Designer, Reviewer.
- Treat workflows and skills as first-class packages, not embedded constants; maintain semantic versioning and provenance.
- Prefer explicit graphs over implicit hierarchies to improve impact analysis and routing quality.
- Use lightweight workers for monitoring/retry/cleanup to avoid LLM burn and improve concurrency.
- Surface “why” everywhere: chosen workflow, tier, policy match, capability match, and delegation lineage.
