# AI-Squad Architecture Diagrams

This document provides visual representations of the AI-Squad orchestration architecture.

## Table of Contents

1. [System Overview](#system-overview)
2. [Control Planes](#control-planes)
3. [Agent Workflow](#agent-workflow)
4. [Routing Flow](#routing-flow)
5. [Delegation Flow](#delegation-flow)
6. [Battle Plan Execution](#battle-plan-execution)
7. [Component Dependencies](#component-dependencies)

---

## System Overview

```mermaid
graph TB
    subgraph "User Interface"
        CLI[CLI Commands]
        Dashboard[Web Dashboard]
        GH[GitHub Events]
    end
    
    subgraph "Orchestration Layer"
        Captain[🎖️ Captain<br/>Coordinator]
        Router[OrgRouter<br/>Policy Enforcement]
        BPE[BattlePlan<br/>Executor]
    end
    
    subgraph "Agent Layer"
        PM[🎨 Product Manager]
        Arch[🏗️ Architect]
        Eng[💻 Engineer]
        UX[🎭 UX Designer]
        Rev[✅ Reviewer]
    end
    
    subgraph "Core Services"
        WS[WorkState<br/>Manager]
        Signal[Signal<br/>Manager]
        Handoff[Handoff<br/>Manager]
        Convoy[Convoy<br/>Manager]
        Del[Delegation<br/>Manager]
    end
    
    subgraph "Persistence"
        Graph[(Operational<br/>Graph)]
        Events[(Routing<br/>Events)]
        Identity[(Identity<br/>Dossiers)]
        Caps[(Capabilities)]
    end
    
    CLI --> Captain
    Dashboard --> Router
    GH --> Captain
    
    Captain --> Router
    Captain --> BPE
    Router --> PM & Arch & Eng & UX & Rev
    
    PM & Arch & Eng & UX & Rev --> WS
    PM & Arch & Eng & UX & Rev --> Signal
    PM & Arch & Eng & UX & Rev --> Handoff
    
    WS --> Graph
    Router --> Events
    Signal --> Events
    Del --> Graph
    
    classDef user fill:#0891b2,stroke:#0e7490,color:#fff
    classDef orch fill:#dc2626,stroke:#991b1b,color:#fff
    classDef agent fill:#059669,stroke:#047857,color:#fff
    classDef core fill:#ec4899,stroke:#be185d,color:#fff
    classDef persist fill:#7c3aed,stroke:#6d28d9,color:#fff
    
    class CLI,Dashboard,GH user
    class Captain,Router,BPE orch
    class PM,Arch,Eng,UX,Rev agent
    class WS,Signal,Handoff,Convoy,Del core
    class Graph,Events,Identity,Caps persist
```

---

## Control Planes

```mermaid
graph TB
    subgraph "Command HQ (Organization Plane)"
        Policy[Policy Rules]
        Health[Health Monitor]
        Circuit[Circuit Breaker]
        Telemetry[Telemetry Aggregation]
    end
    
    subgraph "Mission Squad (Project Plane)"
        BP[Battle Plans]
        Cache[Response Cache]
        Signals[Signal Queue]
        State[Work State]
    end
    
    subgraph "Field Operations"
        Agents[AI Agents]
        Scout[Scout Workers]
        Tools[Tools & Templates]
    end
    
    Policy --> Agents
    Health --> Circuit
    Circuit --> Agents
    
    BP --> Agents
    State --> Agents
    Signals --> Agents
    
    Agents --> Telemetry
    Scout --> State
    
    classDef org fill:#1e40af,stroke:#1e3a8a,color:#fff
    classDef project fill:#059669,stroke:#047857,color:#fff
    classDef field fill:#ca8a04,stroke:#a16207,color:#fff
    
    class Policy,Health,Circuit,Telemetry org
    class BP,Cache,Signals,State project
    class Agents,Scout,Tools field
```

---

## Agent Workflow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Executor as AgentExecutor
    participant Router as OrgRouter
    participant Agent
    participant WS as WorkState
    participant Signal
    participant Graph
    
    User->>CLI: squad pm 123
    CLI->>Executor: execute("pm", 123)
    
    alt Routing Enabled
        Executor->>Router: route(candidates, tags)
        Router->>Router: Check policy
        Router->>Router: Check health
        Router-->>Executor: Selected agent
    end
    
    Executor->>Agent: execute(issue_number)
    
    Agent->>Agent: Validate prerequisites
    Agent->>Agent: Build identity dossier
    
    Agent->>Graph: Add nodes & edges
    Agent->>WS: Update work state
    
    Agent->>Agent: Execute agent logic
    Agent->>Agent: Generate output
    
    Agent->>WS: Attach artifacts
    Agent->>Signal: Send completion signal
    
    Agent-->>Executor: Result
    Executor-->>CLI: Success/failure
    CLI-->>User: Output message
```

---

## Routing Flow

```mermaid
flowchart TD
    Request[Routing Request] --> Policy{Policy Check}
    
    Policy -->|Denied| Block[Block Request]
    Policy -->|Allowed| Health{Health Check}
    
    Health --> Window[Load Event Window]
    Window --> Calc[Calculate Block Rate]
    
    Calc --> Status{Status?}
    
    Status -->|Circuit Open| CircuitBlock[Circuit Breaker Block]
    Status -->|Throttled| Throttle{Has Healthy<br/>Alternatives?}
    Status -->|Healthy| Select[Select Best Candidate]
    
    Throttle -->|Yes| Select
    Throttle -->|No| FallbackSelect[Use Throttled Candidate]
    
    Select --> Latency{Latency Available?}
    FallbackSelect --> Route
    
    Latency -->|Yes| PickLowest[Pick Lowest Latency]
    Latency -->|No| PickFirst[Pick First Viable]
    
    PickLowest --> Route[Route to Agent]
    PickFirst --> Route
    
    Route --> Emit[Emit Routing Event]
    Block --> Emit
    CircuitBlock --> Emit
    
    Emit --> Done[Complete]
    
    classDef success fill:#059669,stroke:#047857,color:#fff
    classDef block fill:#dc2626,stroke:#991b1b,color:#fff
    classDef decision fill:#ca8a04,stroke:#a16207,color:#fff
    
    class Route,Select,Done success
    class Block,CircuitBlock block
    class Policy,Health,Status,Throttle,Latency decision
```

---

## Delegation Flow

```mermaid
sequenceDiagram
    participant FromAgent as From Agent
    participant DelMgr as DelegationManager
    participant Graph as OperationalGraph
    participant Signal as SignalManager
    participant ToAgent as To Agent
    
    FromAgent->>DelMgr: create_delegation(from, to, work_item)
    
    DelMgr->>DelMgr: Generate delegation ID
    DelMgr->>DelMgr: Create audit log entry
    
    DelMgr->>Graph: Add agent nodes
    DelMgr->>Graph: Add delegation edge
    
    DelMgr->>Signal: Send notification to To Agent
    
    Signal-->>ToAgent: Delegation Request
    
    Note over ToAgent: Agent performs work
    
    ToAgent->>DelMgr: complete_delegation(id, status)
    
    DelMgr->>DelMgr: Update status
    DelMgr->>DelMgr: Add audit entry
    
    DelMgr->>Signal: Send completion to From Agent
    
    Signal-->>FromAgent: Delegation Complete
```

---

## Battle Plan Execution

```mermaid
flowchart TD
    subgraph "Initialization"
        Start[Start Execution] --> Load[Load Battle Plan]
        Load --> Create[Create Work Items]
        Create --> Init[Initialize Execution State]
    end
    
    subgraph "Phase Execution"
        Init --> NextPhase{Next Phase?}
        
        NextPhase -->|Yes| GetPhase[Get Phase Details]
        NextPhase -->|No| Complete[Execution Complete]
        
        GetPhase --> CheckDeps{Dependencies<br/>Satisfied?}
        
        CheckDeps -->|No| Wait[Wait for Dependencies]
        CheckDeps -->|Yes| Execute[Execute Phase]
        
        Wait --> CheckDeps
        
        Execute --> Update[Update Work State]
        Update --> Handoff[Trigger Handoff]
        Handoff --> NextPhase
    end
    
    subgraph "Completion"
        Complete --> Summary[Generate Summary]
        Summary --> Notify[Send Notifications]
        Notify --> Done[Done]
    end
    
    classDef init fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef exec fill:#059669,stroke:#047857,color:#fff
    classDef complete fill:#f97316,stroke:#ea580c,color:#fff
    
    class Start,Load,Create,Init init
    class NextPhase,GetPhase,CheckDeps,Wait,Execute,Update,Handoff exec
    class Complete,Summary,Notify,Done complete
```

---

## Component Dependencies

```mermaid
graph LR
    subgraph "CLI Layer"
        CLI[cli.py]
    end
    
    subgraph "Executor Layer"
        AE[AgentExecutor]
        Captain
    end
    
    subgraph "Routing Layer"
        Router[OrgRouter]
        Health[HealthView]
        Events[EventEmitter]
    end
    
    subgraph "Orchestration Layer"
        WS[WorkStateManager]
        BP[BattlePlanManager]
        BPE[BattlePlanExecutor]
        Convoy[ConvoyManager]
        Signal[SignalManager]
        Handoff[HandoffManager]
        Del[DelegationManager]
    end
    
    subgraph "Agent Layer"
        Base[BaseAgent]
        PM[ProductManager]
        Arch[Architect]
        Eng[Engineer]
        UX[UXDesigner]
        Rev[Reviewer]
    end
    
    subgraph "Data Layer"
        Graph[OperationalGraph]
        Identity[IdentityManager]
        Caps[CapabilityRegistry]
        Scout[ScoutWorker]
        Discovery[DiscoveryIndex]
    end
    
    CLI --> AE
    CLI --> Captain
    
    AE --> Router
    AE --> WS & BP & Convoy & Signal & Handoff & Del
    
    Captain --> WS & BP & Convoy & Signal & Handoff
    
    Router --> Health --> Events
    
    Handoff --> WS & Signal & Del
    Del --> Signal & Graph
    
    Base --> WS & Signal & Handoff
    PM & Arch & Eng & UX & Rev --> Base
    
    Base --> Graph & Identity
    
    WS --> Graph
```

---

## Data Flow Diagram

```mermaid
flowchart LR
    subgraph "Input"
        Issue[GitHub Issue]
        Config[squad.yaml]
        Env[Environment]
    end
    
    subgraph "Processing"
        Parse[Parse Input]
        Route[Route Request]
        Execute[Execute Agent]
        Generate[Generate Output]
    end
    
    subgraph "Output"
        Docs[Documents<br/>PRD/ADR/Spec]
        Code[Code & Tests]
        Events[Events<br/>routing.jsonl]
        State[State<br/>work_items.json]
    end
    
    subgraph "Feedback"
        Health[Health Metrics]
        Graph[Graph Updates]
        Identity[Identity Dossier]
    end
    
    Issue --> Parse
    Config --> Parse
    Env --> Parse
    
    Parse --> Route
    Route --> Execute
    Execute --> Generate
    
    Generate --> Docs & Code
    
    Route --> Events
    Execute --> State
    Execute --> Graph
    Execute --> Identity
    
    Events --> Health
    Health -.-> Route
```

---

## Storage Structure

```
.squad/
├── capabilities/
│   ├── installed.json         # Installed packages registry
│   ├── signature.key          # Optional signature verification key
│   └── <pkg-name>-<version>/  # Installed package contents
├── delegations/
│   └── delegations.json       # Delegation links with audit trails
├── discovery/
│   └── remotes.json           # Remote discovery metadata
├── events/
│   └── routing.jsonl          # Routing events (JSONL format)
├── graph/
│   ├── nodes.json             # Operational graph nodes
│   └── edges.json             # Operational graph edges
├── handoffs/
│   └── handoffs.json          # Handoff records
├── identity/
│   └── identity.json          # Current identity dossier
├── scout_workers/
│   └── scout-*.json           # Scout run checkpoints
├── signals/
│   └── messages.json          # Signal messages
└── work_items/
    └── work_items.json        # Work item state
```

---

## Health Status Flow

```mermaid
stateDiagram-v2
    [*] --> Healthy: Initial State
    
    Healthy --> Warn: Block Rate ≥ 25%
    Warn --> Healthy: Block Rate < 25%
    
    Warn --> Critical: Block Rate ≥ 50%
    Critical --> Warn: Block Rate < 50%
    
    Critical --> CircuitOpen: Block Rate ≥ 70%
    CircuitOpen --> Critical: Manual Reset
    
    state Healthy {
        [*] --> Routing
        Routing --> [*]
    }
    
    state Warn {
        [*] --> ThrottledRouting
        ThrottledRouting --> [*]
    }
    
    state Critical {
        [*] --> PreferHealthy
        PreferHealthy --> FallbackThrottled
        FallbackThrottled --> [*]
    }
    
    state CircuitOpen {
        [*] --> Blocked
        Blocked --> [*]
    }
```

---

## Integration Points

```mermaid
graph TB
    subgraph "External Systems"
        GitHub[GitHub API]
        SDK[Copilot SDK]
        LLM[LLM Models]
    end
    
    subgraph "AI-Squad Core"
        Agents[Agents]
        Tools[Tools]
        Templates[Templates]
    end
    
    subgraph "Web Interface"
        Dashboard[Dashboard]
        API[REST API]
    end
    
    GitHub <-->|Issues, PRs| Agents
    SDK <-->|AI Generation| Agents
    LLM <-->|Fallback| Agents
    
    Agents <--> Tools
    Agents <--> Templates
    
    API --> Dashboard
    Agents --> API
    
    classDef external fill:#0891b2,stroke:#0e7490,color:#fff
    classDef core fill:#059669,stroke:#047857,color:#fff
    classDef web fill:#f97316,stroke:#ea580c,color:#fff
    
    class GitHub,SDK,LLM external
    class Agents,Tools,Templates core
    class Dashboard,API web
```

---

## Summary

The AI-Squad architecture follows a layered design:

1. **User Interface Layer** - CLI and Web Dashboard
2. **Orchestration Layer** - Captain, Router, Battle Plans
3. **Agent Layer** - Five specialized agents
4. **Core Services Layer** - State, signals, handoffs, delegations
5. **Persistence Layer** - Graph, events, identity, capabilities

Key principles:
- **Policy-driven routing** with health-aware decisions
- **Explicit delegation** with audit trails
- **Operational graph** for dependency tracking
- **Event sourcing** for telemetry
- **Identity dossiers** for provenance

All components communicate through well-defined interfaces and persist state to the `.squad/` directory structure.
