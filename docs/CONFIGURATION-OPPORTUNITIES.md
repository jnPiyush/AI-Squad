# AI-Squad Configuration Opportunities

This document identifies areas where hardcoded values could be externalized for better customization.

## 🔴 High Priority (Recommended to implement)

### 1. Agent System Prompts → External Files
**Current**: Embedded in Python code (`agents/*.py`)  
**Impact**: Users can't customize agent behavior without modifying code  
**Solution**: Extract to `ai_squad/prompts/` as `.md` files

| Agent | Current Location | Proposed File |
|-------|-----------------|---------------|
| PM | `product_manager.py` | `prompts/pm.md` |
| Architect | `architect.py` | `prompts/architect.md` |
| Engineer | `engineer.py` | `prompts/engineer.md` |
| UX | `ux_designer.py` | `prompts/ux.md` |
| Reviewer | `reviewer.py` | `prompts/reviewer.md` |

### 2. Quality Thresholds → squad.yaml
**Current**: Hardcoded `≥80%` test coverage, `70/20/10` test pyramid  
**Locations**: `engineer.py`, `reviewer.py`, `templates.py`  
**Solution**: Add to `squad.yaml`:

```yaml
quality:
  test_coverage_threshold: 80
  test_pyramid:
    unit: 70
    integration: 20
    e2e: 10
```

### 3. Performance Requirements → squad.yaml  
**Current**: Hardcoded `< 200ms`, `> 1000 req/s`  
**Locations**: `templates.py` (spec template)  
**Solution**: Add to `squad.yaml`:

```yaml
performance:
  response_time_p95_ms: 200
  throughput_req_per_sec: 1000
  concurrent_users: 100
```

### 4. Accessibility Standard → squad.yaml
**Current**: Hardcoded `WCAG 2.1 AA`  
**Locations**: `ux_designer.py`, `templates.py`  
**Solution**: Add to `squad.yaml`:

```yaml
accessibility:
  wcag_level: "AA"  # A, AA, or AAA
  wcag_version: "2.1"
  contrast_ratio: 4.5
```

---

## 🟡 Medium Priority (Nice to have)

### 5. Responsive Breakpoints → squad.yaml
**Current**: Hardcoded `320px`, `768px`, `1024px`  
**Locations**: `ux_designer.py`, `templates.py`  
**Solution**: Add to `squad.yaml`:

```yaml
design:
  breakpoints:
    mobile: "320px-767px"
    tablet: "768px-1023px"
    desktop: "1024px+"
  touch_target_min: "44px"
```

### 6. Status Labels → Already Configurable ✅
**Current**: `squad.yaml` has `github.labels`  
**Status**: Already implemented - just needs documentation

### 7. Workflow State Machine → squad.yaml
**Current**: Hardcoded in `status.py` (`VALID_TRANSITIONS`, `AGENT_STATUS_TRANSITIONS`)  
**Solution**: Make configurable:

```yaml
workflow:
  statuses:
    - Backlog
    - Ready
    - In Progress
    - In Review
    - Done
    - Blocked
  transitions:
    pm: { start: Backlog, complete: Ready }
    architect: { start: Ready, complete: Ready }
    ux: { start: Ready, complete: Ready }
    engineer: { start: In Progress, complete: In Review }
    reviewer: { start: In Review, complete: Done }
```

---

## 🟢 Low Priority (Future consideration)

### 8. Document Naming Patterns
**Current**: Hardcoded `PRD-{issue}.md`, `ADR-{issue}.md`, etc.  
**Solution**: Add to `squad.yaml`:

```yaml
output:
  naming:
    prd: "PRD-{issue}.md"
    adr: "ADR-{issue}.md"
    spec: "SPEC-{issue}.md"
    ux: "UX-{issue}.md"
    review: "REVIEW-{pr}.md"
```

### 9. Code Examples Language
**Current**: C# examples in skills  
**Solution**: Support multiple languages in skills

### 10. Comment Formats
**Current**: Mentions "XML docs" (C#), "docstrings" (Python), "JSDoc" (JS)  
**Solution**: Detect from project or configure

### 11. GitHub API Rate Limits
**Current**: Hardcoded retry thresholds in `github.py`  
**Solution**: Add to `squad.yaml`:

```yaml
github:
  retry:
    max_attempts: 3
    failure_threshold: 5
    success_threshold: 2
```

### 12. Model Temperature Per-Agent
**Current**: Only model name configurable  
**Solution**: Extend agent config:

```yaml
agents:
  pm:
    enabled: true
    model: gpt-4
    temperature: 0.7
    max_tokens: 4000
```

---

## Implementation Plan

### Phase 1: High Impact (Recommended Now)
1. ✅ Templates extracted (completed)
2. 🔄 Agent prompts → external files
3. 🔄 Quality thresholds → squad.yaml
4. 🔄 Update squad.yaml.example with new options

### Phase 2: Medium Impact (Next Iteration)
5. Accessibility/Performance configs
6. Responsive breakpoints
7. Workflow customization

### Phase 3: Polish (Future)
8-12. Lower priority items

---

## Benefits

| Change | Benefit |
|--------|---------|
| External prompts | Customize agent personality without code changes |
| Quality thresholds | Different standards per project |
| Performance targets | Enterprise vs startup requirements |
| Accessibility levels | WCAG A vs AA vs AAA compliance |
| Workflow states | Match existing team processes |
