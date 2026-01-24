# Backlog Issues (Epic / Feature / User Story)

> Format: each entry is written as if it were a GitHub issue. Use the Type tag in the title.

---

## [EPIC] Theater and Routing (Simple)
**Type:** epic

**Mission Intent (Command and Control):** Create a lightweight theater/sector registry and routing table to coordinate missions across sectors while keeping battle plans unchanged.

**Scope:**
- Theater registry
- Sector registry
- Routing table (prefix → sector)

**Out of Scope:**
- No federation or multi-tenant governance in this phase

**Acceptance Criteria:**
- Theater and sector configuration can be created and listed.
- Routing table resolves a work item prefix to a sector.
- Existing battle plan execution works unchanged.

**Dependencies:** None

**Military Terms Used:** command and control, command center, command hierarchy, staging area

---

## [FEATURE] Theater Registry
**Type:** feature

**User Story:**
As Staff, I want a theater registry so I can coordinate missions across sectors with clear command hierarchy.

**Description:**
Provide a simple registry for theaters that contains sectors, repositories, and a routing table reference.

**Acceptance Criteria:**
- Can create, list, update, and delete theaters.
- Each theater references one or more sectors.
- Stored in configuration without breaking current CLI flows.

**Military Terms Used:** command hierarchy, command center

---

## [FEATURE] Sector Registry
**Type:** feature

**User Story:**
As Staff, I want a sector registry so I can assign missions to the correct sector.

**Description:**
Define sector metadata (name, repo path, staging area path).

**Acceptance Criteria:**
- Can create, list, update, and delete sectors.
- Sector includes repo path and staging area location.

**Military Terms Used:** staging area

---

## [USER STORY] Routing Table Resolution
**Type:** user story

**User Story:**
As Staff, I want a routing table so I can direct missions to the correct sector based on a prefix.

**Acceptance Criteria:**
- Given a prefix, routing returns a sector.
- If no match, it defaults to current workspace.

**Military Terms Used:** command and control

---

## [EPIC] Reconnaissance and Patrol (Simple)
**Type:** epic

**Mission Intent (Situation Awareness):** Add a minimal reconnaissance index and patrolling for stale work detection.

**Scope:**
- Reconnaissance index
- Patrolling for stale work

**Acceptance Criteria:**
- Reconnaissance index summarizes work items, convoys, and signals.
- Patrolling flags stale items and logs escalation events.

**Dependencies:** None

**Military Terms Used:** reconnaissance, patrolling, situation awareness

---

## [FEATURE] Reconnaissance Index
**Type:** feature

**User Story:**
As Staff, I want a reconnaissance index so I can maintain situation awareness across missions.

**Acceptance Criteria:**
- Summary includes active work items, convoys, and signal counts.
- Output is available via CLI or report file.

**Military Terms Used:** reconnaissance, situation awareness

---

## [USER STORY] Patrolling for Stale Work
**Type:** user story

**User Story:**
As the Sentinel, I want patrolling so I can detect stalled missions and trigger escalation.

**Acceptance Criteria:**
- Patrol identifies work items stale beyond a threshold.
- Patrol writes an escalation event to logs or state.

**Military Terms Used:** patrolling

---

## [EPIC] After-Operation Reporting (Simple)
**Type:** epic

**Mission Intent:** Provide a minimal after-operation report for command review.

**Scope:**
- A single report per convoy or mission

**Acceptance Criteria:**
- Report includes completed/failed counts and top errors.

**Dependencies:** None

**Military Terms Used:** command and control

---

## [FEATURE] After-Operation Report
**Type:** feature

**User Story:**
As the Commander, I want an after-operation report so I can review outcomes and adjust guidance.

**Acceptance Criteria:**
- Report includes completed/failed counts and top errors.
- Report stored in a predictable location.

**Military Terms Used:** command and control

---

## [USER STORY] Minimal Report Output
**Type:** user story

**User Story:**
As Staff, I want a minimal report output so I can quickly brief the Commander.

**Acceptance Criteria:**
- Report includes mission ID, timeframe, and result summary.

**Military Terms Used:** command and control
