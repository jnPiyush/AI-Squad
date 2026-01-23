# AI-Squad Orchestration Guide

Complete guide to orchestrating multi-agent workflows in AI-Squad using formulas, Captain coordination, convoys, and handoffs.

---

## Table of Contents

- [Overview](#overview)
- [Core Concepts](#core-concepts)
- [Formula Workflows](#formula-workflows)
- [Captain Coordination](#captain-coordination)
- [Convoy Parallel Execution](#convoy-parallel-execution)
- [Work Handoffs](#work-handoffs)
- [Mailbox Messaging](#mailbox-messaging)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

AI-Squad provides powerful orchestration capabilities to coordinate multiple agents working together on complex tasks:

- **Formulas**: YAML-based workflow definitions for sequential and conditional execution
- **Captain**: Meta-agent that analyzes tasks and coordinates agent teams
- **Convoys**: Parallel execution of multiple tasks by the same or different agents
- **Handoffs**: Structured work transfer protocol between agents
- **Mailbox**: Asynchronous message passing for agent communication
- **WorkState**: Persistent tracking of work items, dependencies, and status

---

## Core Concepts

### Work Items

Work items represent units of work tracked through the system:

```python
from ai_squad.core.workstate import WorkStateManager, WorkStatus

# Create work item
work_mgr = WorkStateManager(config)
item = work_mgr.create_work_item(
    title="Implement user authentication",
    description="Add JWT-based auth",
    agent="engineer",
    labels=["feature", "security"],
    priority="high",
    metadata={"issue_number": 123}
)

# Update status
work_mgr.update_work_item(item, status=WorkStatus.IN_PROGRESS)

# Query work items
pending = work_mgr.list_work_items(status=WorkStatus.PENDING, agent="engineer")
```

### Execution Tracking

All orchestration operations track execution state persistently in `.squad/`:

- **Executions**: Formula and convoy execution history
- **Work Items**: Current and historical work state
- **Messages**: Mailbox message queue
- **Handoffs**: Work transfer records

---

## Formula Workflows

### What are Formulas?

Formulas are YAML-based workflow definitions that specify:
- Sequential execution order
- Agent responsibilities
- Dependencies between steps
- Conditional execution
- Error handling behavior

### Built-in Formulas

AI-Squad includes 5 built-in formulas:

#### 1. Feature Formula

Complete feature development workflow:

```yaml
name: feature
description: Complete feature development workflow
steps:
  - name: requirements
    agent: pm
    description: Create PRD and user stories
    
  - name: design
    agent: architect
    depends_on: [requirements]
    description: Design architecture and technical spec
    
  - name: implement
    agent: engineer
    depends_on: [design]
    description: Implement feature with tests
    
  - name: review
    agent: reviewer
    depends_on: [implement]
    description: Review code and approve PR
```

**Usage:**
```bash
squad formula run feature 123
```

#### 2. Bug Fix Formula

Streamlined bug fixing workflow:

```yaml
name: bugfix
description: Bug fix workflow
steps:
  - name: investigate
    agent: engineer
    description: Reproduce and diagnose bug
    
  - name: fix
    agent: engineer
    depends_on: [investigate]
    description: Implement fix with regression tests
    
  - name: review
    agent: reviewer
    depends_on: [fix]
    description: Review fix and tests
```

**Usage:**
```bash
squad formula run bugfix 456
```

#### 3. Tech Debt Formula

Technical debt reduction:

```yaml
name: tech-debt
description: Technical debt and refactoring workflow
steps:
  - name: analyze
    agent: architect
    description: Analyze codebase and identify improvements
    
  - name: refactor
    agent: engineer
    depends_on: [analyze]
    description: Refactor code following recommendations
    
  - name: validate
    agent: reviewer
    depends_on: [refactor]
    description: Validate improvements and test coverage
```

**Usage:**
```bash
squad formula run tech-debt 789
```

#### 4. Design Review Formula

UX-focused workflow:

```yaml
name: design-review
description: UX design and implementation workflow
steps:
  - name: requirements
    agent: pm
    description: Define UX requirements
    
  - name: design
    agent: ux
    depends_on: [requirements]
    description: Create wireframes and prototypes
    
  - name: implement
    agent: engineer
    depends_on: [design]
    description: Implement UI following designs
    
  - name: review
    agent: ux
    depends_on: [implement]
    description: Review implementation against designs
```

**Usage:**
```bash
squad formula run design-review 101
```

#### 5. Quick Fix Formula

Fast turnaround for simple changes:

```yaml
name: quick-fix
description: Quick fix without full review
steps:
  - name: fix
    agent: engineer
    description: Implement quick fix
    continue_on_error: false
```

**Usage:**
```bash
squad formula run quick-fix 202
```

### Creating Custom Formulas

Create custom formulas using CLI:

```bash
# Interactive formula creation
squad formula create

# From YAML file
squad formula create --file my-workflow.yaml
```

**Custom Formula Example:**

```yaml
name: api-feature
description: API feature development with security review
variables:
  api_version: v2
  security_level: high
  
steps:
  - name: requirements
    agent: pm
    description: Define API requirements and contracts
    output: ["docs/prd/api-spec.md"]
    
  - name: api_design
    agent: architect
    depends_on: [requirements]
    description: Design API endpoints and data models
    output: ["docs/specs/api-design.md"]
    condition: always
    
  - name: security_review
    agent: reviewer
    depends_on: [api_design]
    description: Security audit of API design
    condition: on_success
    
  - name: implement_api
    agent: engineer
    depends_on: [security_review]
    description: Implement API with security controls
    continue_on_error: false
    timeout_minutes: 60
    
  - name: integration_tests
    agent: engineer
    depends_on: [implement_api]
    description: Write comprehensive API integration tests
    condition: on_success
    
  - name: final_review
    agent: reviewer
    depends_on: [integration_tests]
    description: Final code and security review
    condition: always
```

### Executing Formulas

Execute formulas programmatically:

```python
from ai_squad.core.formula import FormulaManager, FormulaExecutor
from ai_squad.core.agent_executor import AgentExecutor

# Load formula
formula_mgr = FormulaManager(config)
formula = formula_mgr.get_formula("api-feature")

# Create executor
agent_exec = AgentExecutor(config, workstate, formula_mgr, convoy, mailbox, handoff)
formula_exec = FormulaExecutor(formula_mgr, agent_executor=agent_exec.execute)

# Execute workflow
execution_id = await formula_exec.execute_formula(
    formula_name="api-feature",
    issue_number=123,
    variables={"api_version": "v2", "security_level": "high"}
)

# Track progress
execution = formula_mgr.get_execution(execution_id)
print(f"Status: {execution.status}")
print(f"Completed: {len(execution.completed_steps)}/{len(formula.steps)}")
```

### Step Conditions

Control step execution with conditions:

- **`always`**: Always execute (default)
- **`on_success`**: Execute only if previous step succeeded
- **`on_failure`**: Execute only if previous step failed

```yaml
steps:
  - name: try_fix
    agent: engineer
    
  - name: escalate
    agent: architect
    condition: on_failure  # Only if try_fix failed
    
  - name: cleanup
    agent: engineer
    condition: always  # Always runs
```

### Error Handling

Configure error behavior per step:

```yaml
steps:
  - name: risky_operation
    agent: engineer
    continue_on_error: true  # Don't stop formula on failure
    
  - name: critical_operation
    agent: engineer
    continue_on_error: false  # Stop formula if this fails
```

---

## Captain Coordination

### What is Captain?

Captain is a meta-agent that:
- Analyzes tasks and breaks them into work items
- Identifies parallel execution opportunities
- Coordinates agent teams
- Creates and executes coordination plans

### Using Captain

#### Analyze and Plan

```bash
# Analyze issue and create coordination plan
squad captain analyze 123

# Coordinate multiple work items
squad captain coordinate item-1 item-2 item-3
```

#### Programmatic Usage

```python
from ai_squad.core.captain import Captain

captain = Captain(config, workstate, formula_mgr, convoy, mailbox, handoff)

# Analyze task
breakdown = await captain.analyze_task(
    task_description="Add payment processing with Stripe",
    issue_number=123,
    context={"labels": ["feature", "payment"], "priority": "high"}
)

print(f"Complexity: {breakdown.complexity}")
print(f"Suggested formula: {breakdown.suggested_formula}")
print(f"Work items: {len(breakdown.work_items)}")

# Create coordination plan
plan = captain.coordinate(
    work_items=[item.id for item in breakdown.work_items]
)

print(f"Parallel batches: {len(plan['parallel_batches'])}")
print(f"Sequential steps: {len(plan['sequential_steps'])}")

# Execute plan
results = await captain.execute_plan(
    plan=plan,
    agent_executor=agent_exec,
    execute=True
)

print(f"Completed: {results['completed']}")
print(f"Failed: {results['failed']}")
```

### Captain Strategies

Captain uses intelligent strategies to optimize execution:

1. **Parallel Grouping**: Identifies independent work items that can run concurrently
2. **Dependency Resolution**: Ensures dependent tasks execute in order
3. **Agent Specialization**: Routes work to appropriate expert agents
4. **Load Balancing**: Distributes work evenly across available agents

---

## Convoy Parallel Execution

### What are Convoys?

Convoys enable parallel execution of multiple tasks:
- Same agent, multiple work items
- Multiple agents, concurrent execution
- Efficient resource utilization
- Aggregated result tracking

### Creating Convoys

```bash
# Execute convoy from CLI
squad convoy run "bug-fixes" engineer 101 102 103

# List active convoys
squad convoy list

# Get convoy status
squad convoy status convoy-123
```

### Programmatic Convoy Usage

```python
from ai_squad.core.convoy import ConvoyManager

convoy_mgr = ConvoyManager(config)
convoy_mgr.agent_executor = agent_exec.execute

# Execute parallel tasks
result = await convoy_mgr.execute_convoy(
    convoy_id="parallel-bug-fixes",
    tasks=[
        ("engineer", 101),
        ("engineer", 102),
        ("engineer", 103)
    ]
)

print(f"Completed: {result['completed']}")
print(f"Failed: {result['failed']}")
print(f"Duration: {result['duration_seconds']}s")
```

### Convoy Results

Convoys return aggregated results:

```python
{
    "convoy_id": "parallel-bug-fixes",
    "completed": 2,
    "failed": 1,
    "results": [
        {"agent": "engineer", "issue": 101, "success": True},
        {"agent": "engineer", "issue": 102, "success": True},
        {"agent": "engineer", "issue": 103, "success": False, "error": "..."}
    ],
    "errors": [
        {"issue": 103, "error": "Test failure"}
    ],
    "duration_seconds": 45.2
}
```

---

## Work Handoffs

### What are Handoffs?

Handoffs enable structured work transfer between agents:
- Formal protocol for handing off work
- Context preservation
- Acceptance/rejection workflow
- Audit trail

### Handoff Workflow

```bash
# Initiate handoff
squad handoff initiate work-123 pm architect --reason "PRD complete"

# List pending handoffs
squad handoff list --status pending --agent architect

# Accept handoff
squad handoff accept handoff-456

# Reject handoff
squad handoff reject handoff-789 --reason "Missing requirements"
```

### Programmatic Handoffs

```python
from ai_squad.core.handoff import HandoffManager

handoff_mgr = HandoffManager(config)

# PM initiates handoff to Architect
handoff = handoff_mgr.initiate_handoff(
    work_item_id="work-123",
    from_agent="pm",
    to_agent="architect",
    reason="PRD complete, need architecture",
    context={
        "prd_path": "docs/prd/PRD-123.md",
        "user_stories": 15,
        "priority": "high"
    }
)

# Architect accepts handoff
accepted = handoff_mgr.accept_handoff(
    handoff_id=handoff.id,
    agent="architect"
)

# Work item is now assigned to architect
item = workstate.get_work_item("work-123")
assert item.assigned_to == "architect"
```

### Handoff States

- **`pending`**: Awaiting acceptance
- **`accepted`**: Accepted and work transferred
- **`rejected`**: Rejected with reason
- **`cancelled`**: Cancelled by initiator

---

## Mailbox Messaging

### What is Mailbox?

Mailbox provides asynchronous message passing between agents:
- Non-blocking communication
- Message persistence
- Broadcast capabilities
- Type-safe message structure

### Sending Messages

```python
from ai_squad.core.mailbox import MailboxManager, Message, MessageType

mailbox_mgr = MailboxManager(config)

# Send direct message
message = mailbox_mgr.send_message(
    from_agent="pm",
    to_agent="engineer",
    message_type=MessageType.CLARIFICATION,
    subject="Question about API design",
    body="Should we use REST or GraphQL?",
    metadata={"issue": 123, "priority": "high"}
)

# Broadcast to all agents
mailbox_mgr.broadcast(
    from_agent="architect",
    message_type=MessageType.NOTIFICATION,
    subject="New architecture guidelines published",
    body="Please review docs/adr/ADR-001.md"
)
```

### Receiving Messages

```python
# Check inbox
messages = mailbox_mgr.get_messages("engineer", unread_only=True)

for msg in messages:
    print(f"From: {msg.from_agent}")
    print(f"Subject: {msg.subject}")
    print(f"Body: {msg.body}")
    
    # Mark as read
    mailbox_mgr.mark_as_read(msg.id)
    
    # Reply
    mailbox_mgr.send_message(
        from_agent="engineer",
        to_agent=msg.from_agent,
        message_type=MessageType.RESPONSE,
        subject=f"Re: {msg.subject}",
        body="Let's use REST for simplicity",
        metadata={"reply_to": msg.id}
    )
```

### Message Types

- **`CLARIFICATION`**: Question or clarification request
- **`NOTIFICATION`**: Information broadcast
- **`REQUEST`**: Work or action request
- **`RESPONSE`**: Reply to previous message
- **`STATUS_UPDATE`**: Progress update

---

## Best Practices

### Formula Design

1. **Keep steps focused**: Each step should have single responsibility
2. **Use dependencies**: Declare dependencies explicitly for clarity
3. **Handle errors gracefully**: Set `continue_on_error` appropriately
4. **Add timeouts**: Prevent infinite execution with `timeout_minutes`
5. **Document outputs**: Specify expected artifacts in step descriptions

### Captain Usage

1. **Start with analysis**: Use `captain analyze` before manual planning
2. **Trust the coordination**: Captain's parallel grouping is optimized
3. **Review before execution**: Check plan before executing
4. **Monitor progress**: Track execution status and adjust if needed

### Convoy Execution

1. **Group similar work**: Same agent + same type of work = good convoy
2. **Limit convoy size**: Keep convoys to 3-10 tasks for manageability
3. **Handle partial failures**: Design for scenarios where some tasks fail
4. **Monitor resource usage**: Parallel execution uses more resources

### Handoff Protocol

1. **Include context**: Provide all necessary information for next agent
2. **Set clear expectations**: Explain what's needed in `reason`
3. **Check before accepting**: Review work before accepting handoff
4. **Reject with feedback**: If rejecting, provide actionable feedback

### Mailbox Communication

1. **Use appropriate types**: Choose correct `MessageType` for clarity
2. **Be concise**: Keep messages focused and actionable
3. **Check regularly**: Poll mailbox in agent loops
4. **Mark as read**: Keep inbox clean by marking processed messages

---

## Troubleshooting

### Formula Execution Issues

**Problem**: Formula execution hangs or times out

**Solutions**:
- Check agent_executor is configured correctly
- Verify all agents in formula are enabled
- Add timeout_minutes to steps
- Check logs: `.squad/logs/formula-execution.log`

**Problem**: Step fails but formula doesn't stop

**Solutions**:
- Set `continue_on_error: false` for critical steps
- Check step conditions are correct
- Verify dependencies are properly resolved

### Captain Coordination Issues

**Problem**: Captain creates suboptimal plans

**Solutions**:
- Provide better context (labels, descriptions)
- Use explicit agent assignments in work items
- Consider creating custom formula instead

**Problem**: execute_plan() doesn't run agents

**Solutions**:
- Ensure `execute=True` parameter is set
- Verify agent_executor is passed correctly
- Check agent availability and configuration

### Convoy Execution Issues

**Problem**: Convoy tasks run sequentially instead of parallel

**Solutions**:
- Verify `asyncio` is used correctly
- Check convoy_manager.agent_executor is set
- Ensure async agent executor is provided

**Problem**: High failure rate in convoys

**Solutions**:
- Reduce convoy size for better reliability
- Add retry logic in agent executors
- Check system resource availability

### Handoff Issues

**Problem**: Handoffs never accepted

**Solutions**:
- Check target agent is polling handoffs
- Verify agent names match exactly
- Ensure handoff notifications are working

**Problem**: Work item doesn't transfer

**Solutions**:
- Check workstate_manager is shared
- Verify handoff acceptance completed
- Check work item exists and is accessible

### General Debugging

**Enable debug logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check storage**:
```bash
# View persisted state
ls -la .squad/
cat .squad/workstate/work-items.json
cat .squad/executions/latest.json
```

**Verify configuration**:
```bash
squad doctor
squad config show
```

---

## Advanced Topics

### Custom Formula Templates

Create reusable formula templates:

```python
from ai_squad.core.formula import FormulaManager, FormulaStep

def create_microservice_formula(service_name: str):
    """Generate formula for new microservice development"""
    return {
        "name": f"microservice-{service_name}",
        "description": f"Development workflow for {service_name} microservice",
        "variables": {
            "service_name": service_name,
            "tech_stack": "python-fastapi"
        },
        "steps": [
            FormulaStep(name="requirements", agent="pm"),
            FormulaStep(name="api_design", agent="architect", depends_on=["requirements"]),
            FormulaStep(name="implement", agent="engineer", depends_on=["api_design"]),
            FormulaStep(name="containerize", agent="engineer", depends_on=["implement"]),
            FormulaStep(name="review", agent="reviewer", depends_on=["containerize"])
        ]
    }
```

### Dynamic Workflow Adjustment

Modify workflows at runtime:

```python
# Start formula execution
execution_id = await formula_exec.execute_formula("feature", 123)

# Monitor progress
while execution.status == "running":
    execution = formula_mgr.get_execution(execution_id)
    
    # Check for issues
    if len(execution.failed_steps) > 0:
        # Decide: retry, skip, or abort
        if should_retry:
            formula_exec.retry_step(execution_id, failed_step_name)
        elif should_continue:
            formula_exec.skip_step(execution_id, failed_step_name)
        else:
            formula_exec.abort_execution(execution_id)
            break
    
    await asyncio.sleep(5)
```

### Metrics and Observability

Track orchestration metrics:

```python
from ai_squad.core.metrics import OrchestrationMetrics

metrics = OrchestrationMetrics(config)

# Track execution
with metrics.track_formula_execution("feature"):
    await formula_exec.execute_formula("feature", 123)

# View metrics
print(f"Total executions: {metrics.total_executions}")
print(f"Success rate: {metrics.success_rate}")
print(f"Avg duration: {metrics.avg_duration_seconds}s")
```

---

## Next Steps

- **[Commands Reference](commands.md)** - Complete CLI command documentation
- **[Configuration Guide](configuration.md)** - Configure orchestration settings
- **[Agent Development](AGENTS.md)** - Create custom agents
- **[API Reference](api-reference.md)** - Programmatic API documentation

---

**Need Help?**

- 📖 [Documentation](README.md)
- 🐛 [Report Issues](https://github.com/your-org/ai-squad/issues)
- 💬 [Discussions](https://github.com/your-org/ai-squad/discussions)
