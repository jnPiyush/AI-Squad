# AI-Squad Architecture Diagrams

This document provides visual representations of the AI-Squad orchestration architecture.

## Table of Contents

1. [System Overview](#system-overview)
2. [Agent Workflow](#agent-workflow)
3. [Battle Plan Execution](#battle-plan-execution)
4. [Storage Structure](#storage-structure)
5. [Integration Points](#integration-points)
6. [Summary](#summary)

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
        Executor[AgentExecutor]
        BPE[Battle Plan<br/>Runner]
    end
    
    subgraph "Agent Layer"
        PM[🎨 Product Manager]
        Arch[📐 Architect]
        Eng[💻 Engineer]
        UX[🎭 UX Designer]
        Rev[✅ Reviewer]
    end
    
    subgraph "Core Services"
        WS[WorkState<br/>Manager]
        Hooks[Hook<br/>Manager]
        Workers[Worker<br/>Lifecycle]
        Graph[Operational<br/>Graph]
        Providers[Provider<br/>Chain]
    end
    
    subgraph "Persistence"
        State[(.squad/workstate.json)]
        HookStore[(.squad/hooks)]
        WorkerStore[(.squad/workers.json)]
        GraphStore[(.squad/graph.json)]
    end
    
    CLI --> Captain
    Dashboard --> Captain
    GH --> Captain

    Captain --> Executor
    Captain --> BPE
    Executor --> PM & Arch & Eng & UX & Rev

    PM & Arch & Eng & UX & Rev --> WS
    PM & Arch & Eng & UX & Rev --> Hooks
    PM & Arch & Eng & UX & Rev --> Workers
    PM & Arch & Eng & UX & Rev --> Graph
    PM & Arch & Eng & UX & Rev --> Providers

    WS --> State
    Hooks --> HookStore
    Workers --> WorkerStore
    Graph --> GraphStore
    
    classDef user fill:#0891b2,stroke:#0e7490,color:#fff
    classDef orch fill:#dc2626,stroke:#991b1b,color:#fff
    classDef agent fill:#059669,stroke:#047857,color:#fff
    classDef core fill:#ec4899,stroke:#be185d,color:#fff
    classDef persist fill:#7c3aed,stroke:#6d28d9,color:#fff
    
    class CLI,Dashboard,GH user
    class Captain,Executor,BPE orch
    class PM,Arch,Eng,UX,Rev agent
    class WS,Hooks,Workers,Graph,Providers core
    class State,HookStore,WorkerStore,GraphStore persist
```

---

## Agent Workflow

```mermaid
sequenceDiagram
    participant User
    participant CLI
    participant Executor as AgentExecutor
    participant Agent
    participant WS as WorkState
    participant Hooks
    participant Workers
    participant Graph
    
    User->>CLI: squad pm 123
    CLI->>Executor: execute("pm", 123)
    
    Executor->>Agent: execute(issue_number)
    
    Agent->>Agent: Validate prerequisites
    Agent->>Agent: Build identity dossier
    
    Agent->>Graph: Add nodes & edges
    Agent->>WS: Update work state
    Agent->>Hooks: Persist hooks (if enabled)
    Agent->>Workers: Track lifecycle
    
    Agent->>Agent: Execute agent logic
    Agent->>Agent: Generate output
    
    Agent->>WS: Attach artifacts
    Agent-->>Executor: Result
    Executor-->>CLI: Success/failure
    CLI-->>User: Output message
```

---

## Battle Plan Execution

```mermaid
flowchart TD
    subgraph "Initialization"
        Start[Start Execution] --> Load[Load Battle Plan]
        Load --> Render[Render Variables]
        Render --> Create[Create Work Items]
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
        Update --> NextPhase
    end
    
    subgraph "Completion"
        Complete --> Summary[Generate Summary]
        Summary --> Done[Done]
    end
    
    classDef init fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef exec fill:#059669,stroke:#047857,color:#fff
    classDef complete fill:#f97316,stroke:#ea580c,color:#fff
    
    class Start,Load,Render,Create,Init init
    class NextPhase,GetPhase,CheckDeps,Wait,Execute,Update exec
    class Complete,Summary,Done complete
```

---

## Storage Structure

```
.squad/
├── workstate.json         # Work item state
├── workers.json           # Worker lifecycle records
├── graph.json             # Operational graph
└── hooks/                 # Hook snapshots (if enabled)
    └── <work_item_id>/
```

---

## Integration Points

```mermaid
graph TB
    subgraph "External Systems"
        GitHub[GitHub CLI/Auth]
        Copilot[Copilot CLI/SDK]
        OpenAI[OpenAI]
        Azure[Azure OpenAI]
    end
    
    subgraph "AI-Squad Core"
        Agents[Agents]
        Providers[Provider Chain]
        WorkState[WorkState + Hooks + Workers]
        Graph[Operational Graph]
    end
    
    subgraph "Web Interface"
        Dashboard[Dashboard]
        API[REST API]
    end
    
    GitHub --> Agents
    Copilot --> Providers
    OpenAI --> Providers
    Azure --> Providers
    Providers --> Agents
    Agents --> WorkState
    Agents --> Graph
    Agents --> API
    API --> Dashboard
    
    classDef external fill:#0891b2,stroke:#0e7490,color:#fff
    classDef core fill:#059669,stroke:#047857,color:#fff
    classDef web fill:#f97316,stroke:#ea580c,color:#fff
    
    class GitHub,Copilot,OpenAI,Azure external
    class Agents,Providers,WorkState,Graph core
    class Dashboard,API web
```

---

## Summary

The AI-Squad architecture follows a layered design:

1. **User Interface Layer** - CLI and Web Dashboard
2. **Orchestration Layer** - Captain, AgentExecutor, Battle Plan runner
3. **Agent Layer** - Five specialized agents
4. **Core Services Layer** - WorkState, hooks, worker lifecycle, operational graph, provider chain
5. **Persistence Layer** - `.squad/` state files

All components communicate through well-defined interfaces and persist state to the `.squad/` directory structure.
