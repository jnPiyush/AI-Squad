# 🚨 CRITICAL: Missing Prerequisite Validation in Workflow

## Issue Discovered
**Date:** January 24, 2026  
**Discovered By:** E2E Test Validation  
**Severity:** HIGH - Architectural Bug

## Problem Statement

The E2E autonomous test revealed that **Engineer phase can execute without PRD/ADR/SPEC prerequisites**, which violates the fundamental workflow dependency chain. Investigation shows this is **not just a test issue - it's a workflow architecture bug**.

### Root Cause

The workflow system (`ai_squad/core/handoff.py`, `ai_squad/core/agent_executor.py`) has **NO prerequisite validation** when:
1. Initiating handoffs between agents
2. Executing agent phases
3. Transitioning workflow states

### Current Code Analysis

**File:** `ai_squad/core/handoff.py` - `HandoffManager.initiate_handoff()`

```python
def initiate_handoff(
    self,
    work_item_id: str,
    from_agent: str,
    to_agent: str,
    reason: HandoffReason,
    context: Optional[HandoffContext] = None,
    ...
) -> Optional[Handoff]:
    # Verify work item exists
    work_item = self.work_state_manager.get_work_item(work_item_id)
    if not work_item:
        return None
    
    # ❌ NO PREREQUISITE VALIDATION HERE
    # Creates handoff without checking if prerequisites exist
    handoff = Handoff(...)
    return handoff
```

**What's Missing:**
- No validation that PM has completed PRD before Architect runs
- No validation that Architect has completed ADR/SPEC before Engineer runs
- No validation that Engineer has completed implementation before Reviewer runs
- No validation of artifact existence before handoff

## Impact

### High Risk Scenarios

1. **Engineer runs without requirements** → Implements wrong solution
2. **Architect designs without PRD** → Designs without context
3. **Reviewer reviews without code** → Reviews nothing
4. **UX designs without specs** → Designs don't match architecture

### Current Workarounds

The E2E test now includes prerequisite validation **in the test** (commit 65a3dc1), but this is a **band-aid**. The actual workflow should enforce this.

## Dependency Chain Requirements

```
Issue Created
    ↓
PM Agent (generates PRD)
    ↓ ← Prerequisite: PRD must exist
Architect Agent (generates ADR + SPEC)
    ↓ ← Prerequisites: PRD + ADR + SPEC must exist
Engineer Agent (implements code)
    ↓ ← Prerequisite: Implementation must exist
Reviewer Agent (reviews code)
```

## Proposed Solution

### Phase 1: Add Prerequisite Validation to HandoffManager

**File:** `ai_squad/core/handoff.py`

```python
class AgentPrerequisites:
    """Define prerequisites for each agent type"""
    
    PREREQUISITES = {
        "architect": {
            "required_artifacts": ["PRD"],
            "required_agents": ["pm"]
        },
        "engineer": {
            "required_artifacts": ["PRD", "ADR", "SPEC"],
            "required_agents": ["pm", "architect"]
        },
        "ux": {
            "required_artifacts": ["PRD"],
            "required_agents": ["pm"]
        },
        "reviewer": {
            "required_artifacts": ["PRD", "ADR", "SPEC", "implementation"],
            "required_agents": ["pm", "architect", "engineer"]
        }
    }
    
    @staticmethod
    def validate_prerequisites(
        to_agent: str,
        work_item_id: str,
        work_state_manager: WorkStateManager
    ) -> tuple[bool, List[str]]:
        """
        Validate prerequisites before handoff.
        
        Returns:
            (is_valid, missing_items)
        """
        prereqs = AgentPrerequisites.PREREQUISITES.get(to_agent, {})
        missing = []
        
        # Check required artifacts
        for artifact in prereqs.get("required_artifacts", []):
            artifact_path = f"docs/{artifact.lower()}/{artifact}-{work_item_id}.md"
            if not Path(artifact_path).exists():
                missing.append(f"{artifact} artifact")
        
        # Check required agents completed
        work_item = work_state_manager.get_work_item(work_item_id)
        if work_item:
            for required_agent in prereqs.get("required_agents", []):
                if required_agent not in work_item.completed_agents:
                    missing.append(f"{required_agent} agent completion")
        
        return (len(missing) == 0, missing)


class HandoffManager:
    def initiate_handoff(
        self,
        work_item_id: str,
        from_agent: str,
        to_agent: str,
        reason: HandoffReason,
        context: Optional[HandoffContext] = None,
        validate_prerequisites: bool = True,  # NEW parameter
        ...
    ) -> Optional[Handoff]:
        """Initiate a handoff with prerequisite validation."""
        
        # Verify work item exists
        work_item = self.work_state_manager.get_work_item(work_item_id)
        if not work_item:
            logger.error("Work item not found: %s", work_item_id)
            return None
        
        # NEW: Validate prerequisites
        if validate_prerequisites:
            is_valid, missing = AgentPrerequisites.validate_prerequisites(
                to_agent, work_item_id, self.work_state_manager
            )
            
            if not is_valid:
                logger.error(
                    "Cannot handoff to %s: Missing prerequisites: %s",
                    to_agent, ", ".join(missing)
                )
                # Create REJECTED handoff with reason
                handoff = Handoff(
                    id=f"handoff-{uuid.uuid4().hex[:8]}",
                    work_item_id=work_item_id,
                    from_agent=from_agent,
                    to_agent=to_agent,
                    reason=reason,
                    status=HandoffStatus.REJECTED,
                    context=context,
                    rejection_reason=f"Missing prerequisites: {', '.join(missing)}",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self._save_handoff(handoff)
                return handoff
        
        # Continue with normal handoff creation...
        handoff = Handoff(...)
        return handoff
```

### Phase 2: Add to WorkItem Tracking

**File:** `ai_squad/core/workstate.py`

```python
@dataclass
class WorkItem:
    """Work item with agent tracking"""
    
    id: str
    title: str
    description: str
    status: WorkStatus
    assigned_to: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    priority: int = 5
    labels: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # NEW: Track completed agents
    completed_agents: List[str] = field(default_factory=list)
    generated_artifacts: List[str] = field(default_factory=list)
```

### Phase 3: Update AgentExecutor

**File:** `ai_squad/core/agent_executor.py`

Add prerequisite check before agent execution:

```python
def execute_agent(self, agent_name: str, issue_number: int) -> dict:
    """Execute agent with prerequisite validation."""
    
    # NEW: Validate prerequisites
    is_valid, missing = AgentPrerequisites.validate_prerequisites(
        agent_name, 
        f"issue-{issue_number}",
        self.work_state_manager
    )
    
    if not is_valid:
        return {
            "success": False,
            "error": f"Cannot execute {agent_name}: Missing prerequisites: {', '.join(missing)}",
            "prerequisites_missing": missing
        }
    
    # Continue with execution...
```

## Implementation Plan

### Priority 1 (Immediate)
- [ ] Add `AgentPrerequisites` class to `handoff.py`
- [ ] Add prerequisite validation to `HandoffManager.initiate_handoff()`
- [ ] Add `completed_agents` and `generated_artifacts` to `WorkItem`
- [ ] Update agent execution to track completion

### Priority 2 (Short Term)
- [ ] Add prerequisite validation to `AgentExecutor`
- [ ] Add validation to Captain orchestration
- [ ] Update Battle Plans to respect prerequisites
- [ ] Add validation to CLI commands

### Priority 3 (Medium Term)
- [ ] Add configuration for custom prerequisite chains
- [ ] Add override mechanism for manual intervention
- [ ] Add detailed prerequisite reporting in dashboard
- [ ] Add prerequisite visualization in operational graph

## Testing Requirements

1. **Unit Tests**
   - Test prerequisite validation logic
   - Test handoff rejection with missing prerequisites
   - Test agent execution blocking

2. **Integration Tests**
   - Test full workflow with prerequisites enforced
   - Test error handling when prerequisites missing
   - Test prerequisite override mechanism

3. **E2E Tests**
   - Update autonomous test to expect prerequisite validation
   - Test should PASS when prerequisites enforced
   - Validate rejection messages

## Success Criteria

✅ Engineer cannot run without PRD + ADR + SPEC  
✅ Architect cannot run without PRD  
✅ Reviewer cannot run without implementation  
✅ Clear error messages when prerequisites missing  
✅ Handoff history shows rejected handoffs with reasons  
✅ Dashboard shows prerequisite status  
✅ E2E test validates prerequisite enforcement  

## Related Files

- `ai_squad/core/handoff.py` - Handoff management
- `ai_squad/core/workstate.py` - Work item tracking
- `ai_squad/core/agent_executor.py` - Agent execution
- `ai_squad/core/captain.py` - Orchestration
- `ai_squad/core/battle_plan.py` - Workflow templates
- `tests/e2e-live-test.ps1` - E2E validation

## References

- E2E Test Fix: Commit `65a3dc1` (test-level prerequisite validation)
- Discovery: Autonomous test execution on 2026-01-24
- User Insight: "Shouldn't that also require investigation in solution workflow"

## Next Steps

1. Create GitHub issue with this document
2. Implement Priority 1 changes
3. Add comprehensive tests
4. Update E2E test to validate workflow enforcement
5. Document prerequisite configuration options

---

**Status:** OPEN - Requires Implementation  
**Assignee:** TBD  
**Target:** v0.5.0  
**Estimated Effort:** 3-5 days
