"""
Template Engine

Loads and renders document templates.
"""
from dataclasses import dataclass, field
from enum import Enum
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import re


logger = logging.getLogger(__name__)


class TemplateTier(str, Enum):
    """Lookup tiers for templates/prompts."""

    SYSTEM = "system"
    ORG = "org"
    PROJECT = "project"


@dataclass
class TemplateResolutionTrace:
    """Trace data for template resolution attempts."""

    template: str
    force_tier: Optional[str]
    order: List[str] = field(default_factory=list)
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    resolved: Optional[Dict[str, Any]] = None
    fallback: Optional[str] = None


class TemplateEngine:
    """Template loading and rendering with tiered resolution."""

    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        org_templates_dir: Optional[Path] = None,
        force_tier: Optional[str] = None,
    ):
        """Initialize template engine with tiered lookup.

        Args:
            workspace_root: Project root; defaults to cwd.
            org_templates_dir: Optional organization-level templates root.
            force_tier: Force resolution to a specific tier (system/org/project).
        """

        self.workspace_root = workspace_root or Path.cwd()
        self.templates_dir = Path(__file__).parent.parent / "templates"
        self.org_templates_dir = org_templates_dir or Path.home() / ".ai-squad" / "templates"
        self.project_templates_dir = self.workspace_root / ".squad" / "templates"
        self.force_tier_override = (force_tier or os.getenv("AI_SQUAD_TEMPLATE_FORCE_TIER"))
        
    def get_template(
        self,
        template_name: str,
        *,
        force_tier: Optional[str] = None,
        include_trace: bool = False,
    ) -> Union[str, Tuple[str, TemplateResolutionTrace]]:
        """Get a template by name with tiered resolution.

        Args:
            template_name: Template name (prd, adr, spec, ux, review, strategy, etc.)
            force_tier: Optional tier override (system/org/project) for this lookup.
            include_trace: When True, also return the resolution trace object.

        Returns:
            Template content, or (content, trace) when include_trace=True.
        """

        content, trace = self._resolve_template(template_name, force_tier=force_tier)
        if include_trace:
            return content, trace
        return content

    def _resolve_template(
        self,
        template_name: str,
        *,
        force_tier: Optional[str] = None,
    ) -> Tuple[str, TemplateResolutionTrace]:
        """Resolve a template across project/org/system tiers."""

        normalized_force = self._normalize_force_tier(force_tier or self.force_tier_override)
        resolution_order = self._compute_resolution_order(normalized_force)
        trace = TemplateResolutionTrace(
            template=template_name,
            force_tier=normalized_force,
            order=[tier.value for tier in resolution_order],
        )

        extensions = self._candidate_extensions(template_name)
        template_stem = Path(template_name).stem

        for tier in resolution_order:
            tier_root = self._tier_roots()[tier]
            for ext in extensions:
                candidate = tier_root / f"{template_stem}{ext}"
                trace.attempts.append({
                    "tier": tier.value,
                    "path": str(candidate),
                    "exists": candidate.exists(),
                })
                if candidate.exists():
                    content = candidate.read_text(encoding="utf-8")
                    trace.resolved = {
                        "tier": tier.value,
                        "path": str(candidate),
                        "extension": ext,
                    }
                    logger.info(
                        "template_resolution_success",
                        extra={"template_resolution": trace.__dict__},
                    )
                    return content, trace

        fallback = self._get_default_template(template_stem)
        trace.fallback = "default"
        logger.info(
            "template_resolution_fallback",
            extra={"template_resolution": trace.__dict__},
        )
        return fallback, trace

    def _tier_roots(self) -> Dict[TemplateTier, Path]:
        """Return tier roots for resolution."""

        return {
            TemplateTier.SYSTEM: self.templates_dir,
            TemplateTier.ORG: self.org_templates_dir,
            TemplateTier.PROJECT: self.project_templates_dir,
        }

    @staticmethod
    def _candidate_extensions(template_name: str) -> List[str]:
        """Determine candidate extensions for a template name."""

        suffix = Path(template_name).suffix
        if suffix:
            return [suffix]
        return [".md", ".yaml", ".yml", ".json"]

    @staticmethod
    def _normalize_force_tier(force_tier: Optional[str]) -> Optional[str]:
        """Normalize force-tier input."""

        if not force_tier:
            return None
        force_tier = force_tier.strip().lower()
        if force_tier in {t.value for t in TemplateTier}:
            return force_tier
        logger.warning("Invalid force tier '%s' provided; ignoring", force_tier)
        return None

    @staticmethod
    def _compute_resolution_order(force_tier: Optional[str]) -> List[TemplateTier]:
        """Compute the lookup order respecting force-tier overrides."""

        default_order = [TemplateTier.PROJECT, TemplateTier.ORG, TemplateTier.SYSTEM]
        if not force_tier:
            return default_order
        forced = TemplateTier(force_tier)
        return [forced]
    
    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Render template with variables
        
        Args:
            template: Template content
            variables: Variables to substitute
            
        Returns:
            Rendered content
        """
        result = template
        
        # Replace {{variable}} syntax
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        
        # Clean up any remaining placeholders
        result = re.sub(r'\{\{[^}]+\}\}', '[TODO]', result)
        
        return result
    
    def _get_default_template(self, template_name: str) -> str:
        """Get default template if file not found"""
        
        if template_name == "prd":
            return self._get_prd_template()
        elif template_name == "adr":
            return self._get_adr_template()
        elif template_name == "spec":
            return self._get_spec_template()
        elif template_name == "ux":
            return self._get_ux_template()
        elif template_name == "review":
            return self._get_review_template()
        
        return "# {{title}}\n\n{{description}}"
    
    def _get_prd_template(self) -> str:
        """Get PRD template"""
        return """# Product Requirements Document (PRD)

**Issue:** #{{issue_number}}  
**Title:** {{title}}  
**Created:** {{created_at}}  
**Author:** {{author}}

---

## Executive Summary

{{description}}

## Problem Statement

**What problem are we solving?**
[Describe the problem this feature/product solves]

**Who are the users?**
[Define target users and personas]

**Why is this important?**
[Business value and user impact]

## Goals & Success Metrics

### Primary Goals
1. [Goal 1]
2. [Goal 2]
3. [Goal 3]

### Success Metrics
| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| [Metric 1] | [Target] | [How to measure] |
| [Metric 2] | [Target] | [How to measure] |

## User Stories

### Epic User Story
As a [user type]  
I want to [action]  
So that [benefit]

### Feature Stories
1. **Story 1:** [Description]
   - Acceptance Criteria:
     - [ ] Criterion 1
     - [ ] Criterion 2

2. **Story 2:** [Description]
   - Acceptance Criteria:
     - [ ] Criterion 1
     - [ ] Criterion 2

## Functional Requirements

### Core Features
1. **Feature 1**
   - Description: [Details]
   - Priority: High/Medium/Low
   - Dependencies: [List]

2. **Feature 2**
   - Description: [Details]
   - Priority: High/Medium/Low
   - Dependencies: [List]

### User Interactions
- [Interaction 1]
- [Interaction 2]

## Non-Functional Requirements

### Performance
- Response time: [Target]
- Throughput: [Target]
- Concurrency: [Target]

### Security
- Authentication: [Requirements]
- Authorization: [Requirements]
- Data protection: [Requirements]

### Scalability
- Initial load: [Expected]
- Growth projections: [Estimates]

### Accessibility
- WCAG compliance level: AA
- Screen reader support: Required
- Keyboard navigation: Full support

## Technical Considerations

### Architecture Impact
- [System component affected]
- [Integration points]

### Data Requirements
- [Data entities]
- [Data flows]
- [Storage requirements]

### API Requirements
- [Endpoints needed]
- [Integration needs]

## Dependencies & Assumptions

### Dependencies
- [External dependency 1]
- [Internal dependency 2]

### Assumptions
- [Assumption 1]
- [Assumption 2]

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| [Risk 1] | High/Medium/Low | High/Medium/Low | [Strategy] |

## Timeline & Milestones

| Phase | Milestone | Target Date | Status |
|-------|-----------|-------------|--------|
| Design | UX designs complete | [Date] | Pending |
| Development | Implementation complete | [Date] | Pending |
| Testing | QA complete | [Date] | Pending |
| Launch | Production release | [Date] | Pending |

## Out of Scope

- [Item explicitly not included]
- [Future consideration]

## Appendix

### Related Issues
- #[issue]

### References
- [Document 1]
- [Document 2]

### Codebase Context
{{codebase_context}}

---

**Status:** Draft  
**Last Updated:** [Date]
"""
    
    def _get_adr_template(self) -> str:
        """Get ADR template"""
        return """# Architecture Decision Record: {{title}}

**Issue:** #{{issue_number}}  
**Status:** Proposed  
**Date:** [Date]  
**Decision Makers:** [Names]

---

## Context

**What is the issue we're trying to address?**

{{description}}

**What are the driving forces behind this decision?**
- [Force 1]
- [Force 2]

**What constraints do we have?**
- [Constraint 1]
- [Constraint 2]

## Decision

**What is our decision?**

[Clear statement of the architectural decision]

**Why did we choose this approach?**

[Detailed reasoning]

## Alternatives Considered

### Alternative 1: [Name]
**Description:** [Details]

**Pros:**
- [Pro 1]
- [Pro 2]

**Cons:**
- [Con 1]
- [Con 2]

**Why not chosen:** [Reason]

### Alternative 2: [Name]
**Description:** [Details]

**Pros:**
- [Pro 1]

**Cons:**
- [Con 1]

**Why not chosen:** [Reason]

## Consequences

### Positive
- [Benefit 1]
- [Benefit 2]

### Negative
- [Cost/limitation 1]
- [Cost/limitation 2]

### Neutral
- [Impact 1]

## Implementation

**Components Affected:**
- [Component 1]
- [Component 2]

**Changes Required:**
1. [Change 1]
2. [Change 2]

**Migration Strategy:**
[If applicable]

## Compliance

**Standards:**
- [Standard 1]
- [Standard 2]

**Security Considerations:**
- [Consideration 1]

**Performance Impact:**
- [Impact assessment]

## Validation

**How will we validate this decision?**
- [Validation method 1]
- [Validation method 2]

**Success Criteria:**
- [ ] Criterion 1
- [ ] Criterion 2

## References

- [Reference 1]
- [Reference 2]

---

**Related Documents:**
- PRD: docs/prd/PRD-{{issue_number}}.md
- Spec: docs/specs/SPEC-{{issue_number}}.md
"""
    
    def _get_spec_template(self) -> str:
        """Get technical spec template"""
        return """# Technical Specification: {{title}}

**Issue:** #{{issue_number}}  
**Version:** 1.0  
**Status:** Draft

---

## Overview

**Summary:**
{{description}}

**Objectives:**
1. [Objective 1]
2. [Objective 2]

## Architecture

### System Design

```mermaid
graph TD
    A[Component A] --> B[Component B]
    B --> C[Component C]
```

### Components

#### Component 1: [Name]
**Responsibility:** [What it does]

**Interfaces:**
- Input: [Description]
- Output: [Description]

**Dependencies:**
- [Dependency 1]

#### Component 2: [Name]
[Details...]

## Data Models

### Entity: [EntityName]

```csharp
public class EntityName
{
    public int Id { get; set; }
    public string Name { get; set; }
    public DateTime CreatedAt { get; set; }
}
```

**Fields:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Id | int | Yes | Primary key |
| Name | string | Yes | Entity name |

### Database Schema

```sql
CREATE TABLE entity_name (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Contracts

### Endpoint: [Endpoint Name]

**Method:** `GET /api/v1/resource`

**Request:**
```json
{
    "param1": "value1"
}
```

**Response:**
```json
{
    "data": [],
    "success": true
}
```

**Status Codes:**
- 200: Success
- 400: Bad request
- 401: Unauthorized
- 500: Server error

## Security

### Authentication
- [Method]

### Authorization
- [Rules]

### Data Protection
- [Encryption]
- [PII handling]

### Security Checklist
- [ ] Input validation
- [ ] SQL parameterization
- [ ] XSS prevention
- [ ] CSRF protection
- [ ] Rate limiting

## Performance

### Requirements
- Response time: < 200ms (p95)
- Throughput: > 1000 req/s
- Concurrency: 100 simultaneous users

### Optimization Strategies
- [Strategy 1]
- [Strategy 2]

### Caching
- [What to cache]
- [Cache invalidation]

## Testing Strategy

### Unit Tests
- Coverage target: ≥80%
- Key test cases:
  - [Test case 1]
  - [Test case 2]

### Integration Tests
- [Scenario 1]
- [Scenario 2]

### E2E Tests
- [User flow 1]

## Implementation Plan

### Phase 1: Foundation
**Tasks:**
1. [Task 1]
2. [Task 2]

**Deliverables:**
- [Deliverable 1]

### Phase 2: Core Features
[Details...]

### Phase 3: Polish & Optimization
[Details...]

## Monitoring & Observability

### Metrics
- [Metric 1]
- [Metric 2]

### Logging
- Log level: INFO
- Key events:
  - [Event 1]

### Alerts
- [Alert condition 1]

## Deployment

### Prerequisites
- [Requirement 1]

### Steps
1. [Step 1]
2. [Step 2]

### Rollback Plan
[Strategy]

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| [Risk 1] | [Strategy] |

## Future Considerations

- [Enhancement 1]
- [Enhancement 2]

---

**Related Documents:**
- ADR: docs/adr/ADR-{{issue_number}}.md
- PRD: docs/prd/PRD-{{issue_number}}.md
"""
    
    def _get_ux_template(self) -> str:
        """Get UX design template"""
        return """# UX Design: {{title}}

**Issue:** #{{issue_number}}  
**Designer:** AI-Squad UX Designer  
**Date:** [Date]

---

## Design Overview

**Goal:**
{{description}}

**Target Users:**
- [User persona 1]
- [User persona 2]

## User Flows

### Primary Flow

```mermaid
graph LR
    A[Start] --> B[Action 1]
    B --> C[Action 2]
    C --> D[Complete]
```

### Alternative Flows
- [Alt flow 1]

## Wireframes

### Screen 1: [Name]

```
+----------------------------------+
|  Header                    [X]   |
+----------------------------------+
|                                  |
|  [Main Content Area]             |
|                                  |
|  +--------------------------+    |
|  | Component 1              |    |
|  +--------------------------+    |
|                                  |
|  [Button]                        |
+----------------------------------+
|  Footer                          |
+----------------------------------+
```

**Purpose:** [What this screen does]

**Key Elements:**
- Header: [Description]
- Content: [Description]
- Actions: [Description]

### Screen 2: [Name]
[Wireframe...]

## Component Specifications

### Component: [Name]

**Purpose:** [What it does]

**States:**
- Default
- Hover
- Active
- Disabled

**Variants:**
- Primary
- Secondary

**Properties:**
| Property | Type | Default | Description |
|----------|------|---------|-------------|
| size | enum | medium | Size variant |
| disabled | boolean | false | Disabled state |

## Interaction Design

### Interactions
1. **[Interaction 1]**
   - Trigger: [Event]
   - Action: [What happens]
   - Feedback: [Visual feedback]

2. **[Interaction 2]**
   [Details...]

### Animations
- [Animation 1]: Duration 200ms, easing ease-out
- [Animation 2]: [Details]

## Responsive Design

### Breakpoints
- Mobile: 320px - 767px
- Tablet: 768px - 1023px
- Desktop: 1024px+

### Mobile Layout
```
+------------------+
| Stacked layout   |
+------------------+
```

### Desktop Layout
```
+--------------------+--------------------+
| Sidebar            | Main Content       |
+--------------------+--------------------+
```

## Accessibility

### WCAG 2.1 AA Compliance

**Checklist:**
- [ ] Proper heading hierarchy (h1-h6)
- [ ] Alt text for all images
- [ ] ARIA labels for interactive elements
- [ ] Keyboard navigation support
- [ ] Focus indicators visible
- [ ] Color contrast ratios ≥ 4.5:1
- [ ] Screen reader tested
- [ ] Form labels and error messages

### Keyboard Navigation
- Tab: Next element
- Shift+Tab: Previous element
- Enter/Space: Activate
- Esc: Close/Cancel

### Screen Reader Support
- [Consideration 1]
- [Consideration 2]

## Visual Design

### Colors
- Primary: [Color code]
- Secondary: [Color code]
- Success: [Color code]
- Error: [Color code]

### Typography
- Headings: [Font family, sizes]
- Body: [Font family, size]
- Code: [Monospace font]

### Spacing
- Base unit: 8px
- Component spacing: 16px, 24px, 32px

## Error States

### Error Messages
- **[Error Type]:** "[Error message text]"
- **[Error Type]:** "[Error message text]"

### Validation
- Real-time validation: Yes/No
- Error display: Inline/Toast

## Loading States

### Skeleton Screens
```
[Loading placeholder animation]
```

### Spinners
- Small: 16px
- Medium: 24px
- Large: 48px

## Success States

### Confirmation Messages
- "[Success message]"

### Feedback
- Visual: [Description]
- Audio: [If applicable]

## Design System Integration

**Existing Components Used:**
- [Component 1]
- [Component 2]

**New Components:**
- [Component 3]

## Implementation Notes

**For Engineers:**
- [Note 1]
- [Note 2]

**Dependencies:**
- [Library/framework 1]

## Testing & Validation

### Usability Testing
- [ ] Task 1: [Can user complete X?]
- [ ] Task 2: [Can user find Y?]

### Device Testing
- [ ] Mobile (iOS)
- [ ] Mobile (Android)
- [ ] Tablet
- [ ] Desktop (Chrome/Firefox/Safari)

---

**Related Documents:**
- PRD: docs/prd/PRD-{{issue_number}}.md
- Spec: docs/specs/SPEC-{{issue_number}}.md
"""
    
    def _get_review_template(self) -> str:
        """Get code review template"""
        return """# Code Review: {{title}}

**PR:** #{{pr_number}}  
**Reviewer:** AI-Squad Reviewer  
**Date:** [Date]

---

## Summary

**What changed:**
{{description}}

**Files changed:**
{{files}}

## Review Checklist

### ✅ Code Quality

- [ ] **SOLID Principles:** Code follows SOLID principles
- [ ] **DRY:** No code duplication
- [ ] **Naming:** Clear, descriptive names
- [ ] **Error Handling:** Proper try-catch blocks
- [ ] **No Warnings:** No compiler/linter warnings

**Comments:**
[Detailed feedback]

### ✅ Testing

- [ ] **Coverage:** Test coverage ≥80%
- [ ] **Unit Tests:** Comprehensive unit tests
- [ ] **Integration Tests:** Key integration scenarios covered
- [ ] **Test Quality:** Tests follow AAA pattern
- [ ] **Edge Cases:** Edge cases and errors tested

**Test Coverage:**
```
Overall: [X]%
New code: [X]%
```

**Comments:**
[Detailed feedback]

### ✅ Security

- [ ] **Input Validation:** All inputs validated
- [ ] **SQL Injection:** Queries parameterized
- [ ] **No Secrets:** No hardcoded credentials
- [ ] **Auth/Authz:** Proper authentication/authorization
- [ ] **XSS Prevention:** User input sanitized (if web)
- [ ] **Dependencies:** No vulnerable dependencies

**Security Findings:**
[List any concerns]

### ✅ Performance

- [ ] **Async/Await:** Proper async patterns
- [ ] **No N+1:** No N+1 query problems
- [ ] **Caching:** Appropriate caching used
- [ ] **Resource Disposal:** Proper resource cleanup
- [ ] **Algorithms:** Efficient algorithms

**Performance Notes:**
[Analysis]

### ✅ Documentation

- [ ] **XML Docs/Docstrings:** All public APIs documented
- [ ] **README:** Updated if needed
- [ ] **API Docs:** Updated if API changed
- [ ] **Comments:** Complex logic explained
- [ ] **Breaking Changes:** Documented

**Documentation Notes:**
[Feedback]

### ✅ Architecture

- [ ] **Structure:** Follows project structure
- [ ] **Separation of Concerns:** Proper separation
- [ ] **Dependency Injection:** Used appropriately
- [ ] **Interfaces:** Abstractions defined
- [ ] **No Circular Dependencies:** Clean dependency graph

**Architecture Notes:**
[Analysis]

## Detailed Feedback

### File: [filename]

**Line [X]:**
```[language]
[code snippet]
```

**Issue:** [Description]

**Suggestion:**
```[language]
[suggested code]
```

**Priority:** High/Medium/Low

---

### File: [filename]

[More feedback...]

## Positive Highlights

✨ **Well done:**
- [Positive aspect 1]
- [Positive aspect 2]

## Issues Found

| Severity | File | Line | Issue | Suggestion |
|----------|------|------|-------|------------|
| 🔴 High | [file] | [line] | [issue] | [fix] |
| 🟡 Medium | [file] | [line] | [issue] | [fix] |
| 🟢 Low | [file] | [line] | [issue] | [fix] |

## Performance Analysis

**Potential Bottlenecks:**
- [Issue 1]

**Optimization Opportunities:**
- [Opportunity 1]

## Security Analysis

**Vulnerabilities:**
- None found / [List issues]

**Recommendations:**
- [Recommendation 1]

## Test Results

**Test Execution:**
```
Tests run: [X]
Passed: [X]
Failed: [X]
Skipped: [X]
```

**Failed Tests:**
- [Test name]: [Reason]

## Recommendation

**Decision:** ✅ Approve / ⚠️ Request Changes / 💬 Comment

**Reasoning:**
[Explanation of decision]

**Must Fix (Blocking):**
1. [Issue 1]
2. [Issue 2]

**Should Fix (Non-blocking):**
1. [Issue 1]
2. [Issue 2]

**Nice to Have:**
1. [Suggestion 1]

## Next Steps

1. [Action 1]
2. [Action 2]

---

**Overall Assessment:**
[Summary paragraph]

**Merge Status:** Ready / Needs Changes / Blocked
"""
