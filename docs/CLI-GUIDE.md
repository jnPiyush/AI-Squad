# AI-Squad CLI Commands Guide

This guide covers all CLI commands available in AI-Squad, including the new orchestration features.

## Quick Reference

| Command | Description |
|---------|-------------|
| `squad init` | Initialize AI-Squad in your project |
| `squad doctor` | Validate setup and configuration |
| `squad pm <issue>` | Run Product Manager agent |
| `squad architect <issue>` | Run Architect agent |
| `squad engineer <issue>` | Run Engineer agent |
| `squad ux <issue>` | Run UX Designer agent |
| `squad review <pr>` | Run Reviewer agent |
| `squad captain <issue>` | Coordinate issue with Captain |
| `squad dashboard` | Launch web dashboard |
| `squad health` | View routing health |
| `squad work` | List work items |
| `squad plans` | List battle plans |
| `squad convoys` | List convoys |
| `squad signal <agent>` | View agent signals |
| `squad graph` | Manage operational graph |
| `squad capabilities` | Manage capability packages |
| `squad delegation` | Manage delegation links |
| `squad scout` | Manage scout worker runs |

---

## Setup Commands

### `squad init`

Initialize AI-Squad in your project directory.

```bash
squad init
squad init --force  # Overwrite existing files
```

**Creates:**
- `squad.yaml` - Configuration file
- `docs/` directories for outputs
- `.squad/` directory for internal state

### `squad doctor`

Validate your AI-Squad setup.

```bash
squad doctor
```

**Checks:**
- Configuration file presence
- GitHub token configuration
- Directory structure
- Agent availability

---

## Agent Commands

### `squad pm <issue-number>`

Run the Product Manager agent to create a PRD.

```bash
squad pm 123
```

**Output:** `docs/prd/PRD-123.md`

### `squad architect <issue-number>`

Run the Architect agent to create an ADR/specification.

```bash
squad architect 123
```

**Output:** `docs/adr/ADR-123.md` or `docs/specs/SPEC-123.md`

### `squad engineer <issue-number>`

Run the Engineer agent to implement a feature.

```bash
squad engineer 123
```

**Output:** Implementation code with tests

### `squad ux <issue-number>`

Run the UX Designer agent to create wireframes.

```bash
squad ux 123
```

**Output:** `docs/ux/UX-123.md` and HTML prototype

### `squad review <pr-number>`

Run the Reviewer agent to review a pull request.

```bash
squad review 456
```

**Output:** `docs/reviews/REVIEW-456.md`

---

## Orchestration Commands

### `squad captain <issue-number>`

Run the Captain (Coordinator) agent to orchestrate work.

```bash
squad captain 123
```

The Captain:
- Analyzes the issue
- Breaks it into work items
- Selects appropriate battle plans
- Coordinates agent execution

### `squad collab <issue-number> <agents...>`

Run multiple agents in collaboration.

```bash
squad collab 123 pm architect
squad collab 123 pm architect engineer
```

### `squad watch`

Watch GitHub for label changes and auto-trigger agents.

```bash
squad watch
squad watch --interval 60  # Custom polling interval
squad watch --repo owner/repo  # Override repository
```

**Orchestration Labels:**
- `orch:pm-done` → Triggers Architect
- `orch:architect-done` → Triggers Engineer
- `orch:engineer-done` → Triggers Reviewer

---

## Work Management Commands

### `squad work`

List all work items.

```bash
squad work
squad work --status ready
squad work --status in-progress
squad work --agent engineer
```

**Statuses:** `ready`, `in-progress`, `blocked`, `done`

### `squad plans`

List available battle plans (workflow templates).

```bash
squad plans
squad plans --label bugfix
```

### `squad run-plan <plan-name> <issue-number>`

Execute a battle plan on an issue.

```bash
squad run-plan feature 123
squad run-plan bugfix 456
```

### `squad convoys`

List active convoys (parallel work batches).

```bash
squad convoys
squad convoys --convoy-id convoy-abc123
squad convoys --issue 123
```

### `squad handoff <work-item-id> <from-agent> <to-agent>`

Initiate a handoff between agents.

```bash
squad handoff sq-abc12 pm architect --reason workflow
squad handoff sq-abc12 architect engineer --reason workflow --summary "Spec complete"
```

**Reasons:** `workflow`, `escalation`, `specialization`, `blocker`

### `squad signal <agent>`

View agent signal messages.

```bash
squad signal engineer
squad signal pm --unread
```

### `squad status`

Show overall orchestration status.

```bash
squad status
```

---

## Health & Monitoring Commands

### `squad health`

View routing health and circuit breaker status.

```bash
squad health
```

**Shows:**
- Overall health status (healthy/warn/critical)
- Total events, routed, blocked
- Block rate percentage
- Health by destination
- Health by priority

### `squad dashboard`

Launch the web-based dashboard.

```bash
squad dashboard
squad dashboard --port 8080
squad dashboard --host 0.0.0.0 --debug
```

**Default:** http://127.0.0.1:5050

**Requires:** `pip install flask`

**Dashboard Pages:**
- **Overview** - Stats and recent activity
- **Health** - Routing health and circuit breakers
- **Work Items** - Work item management
- **Delegations** - Delegation tracking
- **Convoys** - Parallel work monitoring
- **Graph** - Operational graph visualization

---

## Graph Commands

### `squad graph export`

Export the operational graph as a Mermaid diagram.

```bash
squad graph export
squad graph export --format mermaid
```

### `squad graph impact <node-id>`

Analyze the impact of changes to a node.

```bash
squad graph impact issue-123
squad graph impact engineer
```

**Shows:**
- Direct dependents
- Total affected nodes
- Owners
- Full affected node list

---

## Capability Management Commands

### `squad capabilities list`

List installed capability packages.

```bash
squad capabilities list
```

### `squad capabilities install <path>`

Install a capability package.

```bash
squad capabilities install ./my-capability
squad capabilities install ./my-capability-1.0.0.tar.gz
```

### `squad capabilities key`

Manage capability signature key.

```bash
squad capabilities key --set "your-secret-key"
squad capabilities key --show
```

---

## Delegation Commands

### `squad delegation list`

List all delegation links.

```bash
squad delegation list
```

---

## Scout Worker Commands

### `squad scout list`

List scout worker runs.

```bash
squad scout list
```

### `squad scout show <run-id>`

Show details for a scout run.

```bash
squad scout show scout-abc12345
```

### `squad scout run`

Run a scout worker task.

```bash
squad scout run --task noop
squad scout run --task list_squad_files
squad scout run --task check_routing_events
```

---

## Configuration

### Environment Variables

```bash
# Required
export GITHUB_TOKEN=ghp_your_token

# Optional
export AI_SQUAD_MODEL=gpt-4
export AI_SQUAD_TEMPERATURE=0.5
export AI_SQUAD_TEMPLATE_FORCE_TIER=system
```

### squad.yaml Configuration

See `squad.yaml.example` for full configuration options.

Key sections:
- `project` - Project metadata
- `agents` - Agent configuration
- `output` - Output directories
- `routing` - Routing policy configuration
- `quality` - Quality thresholds

### Routing Policy Configuration

```yaml
routing:
  # Policy constraints
  allowed_capability_tags: []
  denied_capability_tags: []
  required_trust_levels: []
  max_data_sensitivity: restricted  # public|internal|confidential|restricted
  trust_level: high
  data_sensitivity: internal
  priority: normal
  
  # Health thresholds
  warn_block_rate: 0.25
  critical_block_rate: 0.5
  circuit_breaker_block_rate: 0.7
  throttle_block_rate: 0.5
  min_events: 5
  window: 200
  
  # Enable for CLI commands
  enforce_cli_routing: false
```

---

## Tips & Best Practices

### Standard Feature Workflow

```bash
# 1. Create PRD
squad pm 123

# 2. Create architecture
squad architect 123

# 3. Create UX design (if needed)
squad ux 123

# 4. Implement feature
squad engineer 123

# 5. Review code
squad review <pr-number>
```

### Using Captain for Complex Issues

```bash
# Let Captain coordinate everything
squad captain 123

# Then monitor progress
squad work
squad status
```

### Monitoring Health

```bash
# Quick health check
squad health

# Full dashboard
squad dashboard
```

### Working with the Graph

```bash
# See the full graph
squad graph export

# Analyze impact before changes
squad graph impact engineer
```

---

## Troubleshooting

### "GitHub token not set"

```bash
export GITHUB_TOKEN=ghp_your_token
```

### "Flask not installed"

```bash
pip install flask
```

### "SDK not available"

```bash
pip install github-copilot-sdk
```

### "Issue not found"

- Verify the issue exists in your repository
- Check `GITHUB_TOKEN` has access to the repository

### "Routing policy blocked"

- Check `squad.yaml` routing configuration
- View health with `squad health`
- Disable enforcement: `enforce_cli_routing: false`

---

## Further Reading

- [AGENTS.md](../AGENTS.md) - Detailed agent documentation
- [Architecture](architecture/orchestration-enhancements.md) - System architecture
- [Configuration](configuration.md) - Full configuration reference
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
