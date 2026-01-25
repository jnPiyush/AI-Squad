# AI-Squad

<p align="center">
  <img src="assets/banner.svg" alt="AI-Squad Banner" width="100%"/>
</p>

<p align="center">
  <a href="https://badge.fury.io/py/ai-squad"><img src="https://badge.fury.io/py/ai-squad.svg" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="tests/"><img src="https://img.shields.io/badge/coverage-target%2080%25-yellow.svg" alt="Coverage Target"></a>
  <a href="https://pypi.org/project/ai-squad/"><img src="https://img.shields.io/pypi/dm/ai-squad?label=downloads&color=blue" alt="Downloads"></a>
</p>

<p align="center">
  <strong>🎖️ Five expert AI agents orchestrated by a Captain</strong><br/>
  <em>Squad Assembled • Mission Ready • Awaiting Orders</em>
</p>

---

## 🎯 What is AI-Squad?

AI-Squad is a **command-line tool** (Beta) that brings five specialized AI agents to your project:

| Agent | Role | What They Do |
|-------|------|--------------|
| 🎨 **Product Manager** | Requirements | Creates PRDs, breaks down epics into stories |
| 🧩 **Architect** | Design | Designs solutions, writes ADRs and technical specs |
| 🔧 **Engineer** | Implementation | Implements features with comprehensive tests |
| 🎭 **UX Designer** | User Experience | Creates wireframes, HTML prototypes, accessibility guidelines |
| 🛡️ **Reviewer** | Quality | Reviews code, security analysis, ensures quality |

**New in v0.5.0**: 🎖️ Squad Mission Mode - True autonomous development! Provide requirements, Captain orchestrates multi-agent collaboration to complete entire features end-to-end!

**From v0.4.0**: Advanced orchestration (Captain, Battle Plans, Convoys), web dashboard, retry logic, rate limiting, persistent storage

**Install once. Use everywhere. No hosting required.**

---

## ⚔️ Squad Terminology

AI-Squad uses military-inspired terminology to describe its orchestration system:

```mermaid
graph TB
    subgraph "⚔️ COMMAND HQ"
        Captain["🎖️ Captain<br/><i>Coordinator</i>"]
        Router["🧭 Command Router<br/><i>Policy & Health</i>"]
    end
    
    subgraph "🎯 MISSION CONTROL"
        BP["📜 Battle Plans<br/><i>Workflows</i>"]
        WI["💼 operations<br/><i>Tasks</i>"]
        Convoy["🚐 Convoys<br/><i>Parallel Batches</i>"]
    end
    
    subgraph "🤖 FIELD AGENTS"
        PM["🎨 PM"]
        Arch["🧩 Architect"]
        Eng["🔧 Engineer"]
        UX["🎭 UX"]
        Rev["🛡️ Reviewer"]
    end
    
    Captain --> BP
    Captain --> Router
    Router --> PM & Arch & Eng & UX & Rev
    BP --> WI
    WI --> Convoy
```

| Term | What It Means | Example |
|------|---------------|--------|
| **🎖️ Captain** | Coordinator that orchestrates agents | `squad captain 123` - analyzes issue and delegates |
| **📜 Battle Plan** | Predefined workflow template | `feature` plan: PM → Architect → Engineer → Reviewer |
| **💼 operation** | Single unit of work tracked in system | Issue #123 becomes operation `sq-abc12` |
| **🚐 Convoy** | Parallel batch of related operations | 5 stories from an epic processed together |
| **👋➡️ Handoff** | Transfer of work between agents | PM completes PRD, hands off to Architect |
| **📡 Signal** | Message sent between agents | "PRD ready for review" notification |
| **👉 Delegation** | Explicit assignment with audit trail | PM delegates API design to Architect |
| **🕸️ Graph** | Tracks relationships between entities | Shows which agent owns which operation |
| **🪪 Identity** | Provenance metadata embedded in outputs | Tracks who created what, when, and why |
| **🔍 Scout** | Background worker for discovery tasks | Scans workspace for patterns |
| **🧭 Router** | Policy enforcement and health monitoring | Routes requests to healthy agents |

---

## 🔄 How It Works

### The Flow

```mermaid
sequenceDiagram
    participant Dev as ⭐ High Command
    participant CLI as 🖥️ CLI
    participant Captain as 🎖️ Captain
    participant Router as 🧭 Router
    participant Agent as 🤖 Agent
    participant Output as 📄 Output
    
    Dev->>CLI: squad captain 123
    CLI->>Captain: Coordinate issue #123
    Captain->>Captain: Analyze & create operations
    Captain->>Router: Route to best agent
    Router->>Router: Check policy & health
    Router->>Agent: Execute task
    Agent->>Agent: Generate with skills
    Agent->>Output: docs/prd/PRD-123.md
    Agent->>CLI: ✅ Complete
    CLI->>Dev: Success!
```

### Battle Plan Execution

When you run a **Battle Plan**, the system orchestrates multiple agents automatically:

```mermaid
flowchart LR
    subgraph "📜 Feature Battle Plan"
        direction LR
        P1["Phase 1<br/>🎨 PM<br/>Create PRD"]
        P2["Phase 2<br/>🧩 Architect<br/>Design Solution"]
        P3["Phase 3<br/>🔧 Engineer<br/>Implement"]
        P4["Phase 4<br/>🛡️ Reviewer<br/>Review Code"]
        
        P1 -->|handoff| P2
        P2 -->|handoff| P3
        P3 -->|handoff| P4
    end
    
    style P1 fill:#ec4899,color:#fff
    style P2 fill:#f59e0b,color:#fff
    style P3 fill:#10b981,color:#fff
    style P4 fill:#3b82f6,color:#fff
```

### Routing & Health

The **Command Router** ensures reliable execution with policy enforcement and health monitoring:

```mermaid
flowchart TD
    Req[🔄 Request] --> Policy{🧭 Policy Check}
    Policy -->|Denied| Block[🚫 Blocked]
    Policy -->|Allowed| Health{❤️ Health Check}
    
    Health --> Status{Status?}
    Status -->|🟢 Healthy| Route[✅ Route to Agent]
    Status -->|🟡 Throttled| Alt{Alternatives?}
    Status -->|🔴 Circuit Open| CB[⚡ Circuit Breaker]
    
    Alt -->|Yes| Route
    Alt -->|No| Fallback[⚠️ Fallback]
    
    style Route fill:#10b981,color:#fff
    style Block fill:#ef4444,color:#fff
    style CB fill:#ef4444,color:#fff
    style Fallback fill:#f59e0b,color:#fff
```

---

## ⚡ Quick Start

### 1. Install AI-Squad

```bash
pip install ai-squad
```

### 2. Initialize in Your Project

```bash
cd /path/to/your-project
squad deploy
```

**Interactive Setup**: The init command will:
- Create all necessary directories and files
- Check your GitHub CLI authentication status
- Guide you through OAuth setup with `gh auth login`
- Show clear setup instructions if not authenticated

This creates:
- ✅ `.github/agents/` - 5 agent definition files (pm, architect, engineer, ux, reviewer)
- ✅ `.github/skills/` - 18 production skills
- ✅ `.github/templates/` - 7 document templates
- ✅ `.github/copilot-instructions.md` - GitHub Copilot integration instructions
- ✅ `squad.yaml` - Configuration
- ✅ `docs/` - Output directories (prd, adr, specs, ux, reviews)
- ✅ `.squad/` - Internal state (graph, events, identity)

### 3. Use Your Squad!

**🎖️ Squad Mission Mode (Recommended - Military-Themed Workflow):**
```bash
# Provide mission brief and Squad DEPLOYS TO CAPTAIN:
# 1. PM analyzes mission (validates as epic or feature)
# 2. Creates Mission Brief in GitHub
# 3. Breaks down into Mission Objectives
# 4. 🎖️ DEPLOYS TO CAPTAIN for orchestration
# 5. Captain selects Battle Plan (feature/epic workflow)
# 6. Captain executes agents via collaboration: PM → Architect → Engineer → UX → Reviewer
# 7. Multi-agent team collaborates to complete mission!

squad mission -p "Create a REST API for user management with authentication"

# From a file
squad mission -f mission-brief.txt

# Interactive mode
squad mission -i

# Create mission brief only (manual Captain deployment)
squad mission -p "Add payment integration" --plan-only
```

**Individual Agent Commands:**
```bash
# Single agent commands (requires existing GitHub issue)
squad pm 123           # Product Manager creates PRD
squad architect 123    # Architect designs solution
squad engineer 123     # Engineer implements feature
squad ux 123           # UX Designer creates wireframes
squad review 456       # Reviewer checks PR

# Orchestration commands
squad captain 123      # 🎖️ Captain coordinates everything
squad joint-op 100 pm architect  # Multi-agent collaboration
squad patrol            # Auto-trigger on GitHub labels

# Monitoring commands
squad status           # View routing health
squad ops             # List operations
squad dashboard        # Launch web UI
```

#### 💬 GitHub Copilot Chat Integration
Your agents work naturally in Copilot Chat - just mention them by name:

```
"PM, create requirements for user authentication"
"Architect, design a REST API for users"
"Engineer, implement JWT auth with tests"
```

See `.github/copilot-instructions.md` and `.github/agents/` for agent definitions.

---

## 🎖️ Complete Squad Mission Workflow

Here's how Squad Mission Mode orchestrates your entire development lifecycle:

```mermaid
graph TB
    subgraph "1️⃣ Mission Submission"
        User["⭐ High Command"] -->|"squad auto -p 'requirements'"| Auto["🎖️ Squad Mission Mode"]
    end
    end
    
    subgraph "2️⃣ Mission Analysis"
        Auto --> PM["🎨 PM Agent"]
        PM -->|Validates| Type{Mission Type?}
        Type -->|Complex| Epic["📋 EPIC"]
        Type -->|Simple| Feature["📋 FEATURE"]
    end
    
    subgraph "3️⃣ GitHub Integration"
        Epic --> Brief1["📝 Mission Brief #123<br/>(Epic Issue)"]
        Feature --> Brief2["📝 Mission Brief #123<br/>(Feature Issue)"]
        Brief1 --> Obj["🎯 Mission Objectives<br/>#124, #125, #126"]
        Brief2 --> Obj
    end
    
    subgraph "4️⃣ Captain Deployment"
        Obj -->|Deploys to| Captain["🎖️ Captain"]
        Captain --> Analyze["Analyze Mission"]
        Analyze --> BP["Select Battle Plan"]
        BP --> WI["Create operations"]
        WI --> Convoy["Organize Convoys"]
    end
    
    subgraph "5️⃣ Multi-Agent Execution"
        Convoy --> Collab["🤝 run_collaboration()"]
        Collab --> PM2["🎨 PM: Create PRD"]
        PM2 --> Arch["🧩 Architect: Design ADR"]
        Arch --> Eng["🔧 Engineer: Implement + Tests"]
        Eng --> UX["🎭 UX: Design Prototype"]
        UX --> Rev["🛡️ Reviewer: Review + PR"]
    end
    
    subgraph "6️⃣ Monitoring & Completion"
        Rev --> Monitor["📊 Monitoring"]
        Monitor --> Patrol["🔍 Patrol: Check stale work"]
        Monitor --> Recon["🔍 Recon: Status reports"]
        Monitor --> Scout["🔍 Scout: Pattern discovery"]
        Monitor --> Done["✅ Mission Complete!"]
    end
    
    style Captain fill:#4A90E2,stroke:#2E5C8A,color:#fff
    style Collab fill:#50C878,stroke:#2E7D4E,color:#fff
    style Done fill:#28A745,stroke:#1E7E34,color:#fff
```

### Key Components

| Component | Role | Output |
|-----------|------|--------|
| **🎖️ Captain** | Meta-coordinator | Analyzes, plans, and orchestrates |
| **📜 Battle Plan** | Workflow template | Defines agent sequence |
| **💼 operations** | Task tracking | Tracks status per issue |
| **🚐 Convoy** | Parallel executor | Runs independent tasks simultaneously |
| **🤝 Collaboration** | Multi-agent coordinator | Executes agents in sequence |
| **🔍 Patrol** | Monitoring | Detects stale/stuck work |
| **🔍 Recon** | Intelligence | System status reports |
| **🔍 Scout** | Discovery | Pattern detection |

---

## 🚀 Features

### 🏰 Orchestration System

```mermaid
graph LR
    subgraph "Command"
        C1["squad captain 123"]
        C2["squad run-plan feature 123"]
    end
    
    subgraph "Orchestration"
        Captain["🎖️ Captain"]
        BP["📜 Battle Plan"]
        Conv["🚐 Convoy"]
    end
    
    subgraph "Execution"
        WI1["📦 PRD"]
        WI2["📦 ADR"]
        WI3["📦 Code"]
        WI4["📦 Review"]
    end
    
    C1 --> Captain
    C2 --> BP
    Captain --> BP
    BP --> Conv
    Conv --> WI1 --> WI2 --> WI3 --> WI4
```

| Feature | Description |
|---------|-------------|
| **🎖️ Captain** | Intelligent coordinator that analyzes issues and delegates to agents |
| **📜 Battle Plans** | Pre-defined workflows (feature, bugfix, epic) with phase dependencies |
| **🚐 Convoys** | Parallel processing of related operations |
| **👋➡️ Handoffs** | Automatic work transfer between agents with context |
| **📡 Signals** | Inter-agent messaging system |
| **👉 Delegations** | Explicit assignments with full audit trails |

### 🤖 Five Expert Agents

| Agent | Command | Output |
|-------|---------|--------|
| **🎨 Product Manager** | `squad pm <issue>` | PRD + User Stories + Backlog |
| **🧩 Architect** | `squad architect <issue>` | ADR + Technical Spec + Diagrams |
| **🔧 Engineer** | `squad engineer <issue>` | Code + Tests + Documentation |
| **🎭 UX Designer** | `squad ux <issue>` | Wireframes + User Flows + Prototype |
| **🛡️ Reviewer** | `squad review <pr>` | Code Review + Security Analysis |

### 📊 Web Dashboard

Launch the monitoring dashboard to visualize your Squad's operations:

```bash
squad dashboard
# Opens http://127.0.0.1:5050
```

**Dashboard Pages:**
- **Overview** - Stats, health status, recent activity
- **Health** - Routing health with circuit breakers
- **operations** - Track all work across agents
- **Delegations** - View delegation links and audit trails
- **Convoys** - Monitor parallel work batches
- **Graph** - Interactive operational graph visualization

### 🗣️👥 Multi-Agent Collaboration

```bash
# PM and Architect collaborate on Epic planning
squad joint-op 100 pm architect

# Flow:
# 1. PM drafts PRD
# 2. Architect reviews for feasibility
# 3. They iterate together
# 4. Both finalize documents
```

### 🗡️ 18 Production Skills

Every agent follows battle-tested production standards:

```mermaid
mindmap
  root((Skills))
    Foundation
      Testing
      Security
      Error Handling
      Core Principles
    Architecture
      Performance
      Scalability
      Database
      API Design
    Development
      Configuration
      Documentation
      Type Safety
      Logging
    Operations
      Git Workflows
      Code Review
      Deployment
```

[See all skills →](docs/skills.md)

### 🎨 Template-Driven Documents

All outputs use standardized templates:
- **PRD** - Product Requirements Document
- **ADR** - Architecture Decision Record
- **Spec** - Technical Specification
- **UX** - UX Design Document
- **Review** - Code Review Report

### 🔄 GitHub Actions Integration

**Automatic agent execution when issues are labeled:**

```yaml
# .github/workflows/squad-orchestrator.yml (auto-generated)
on:
  issues:
    types: [labeled]

# Label 'type:feature' → PM creates PRD
# Label 'type:story' → Engineer implements
# Label 'needs:design' → UX Designer creates wireframes
```

---

## 💡 Usage Examples

### Example 1: Feature Development

```bash
# You have issue #123: "Add OAuth Login"

# Step 1: PM creates requirements
squad pm 123
# ✅ Output: docs/prd/PRD-123.md

# Step 2: Architect designs solution
squad architect 123
# ✅ Output: docs/adr/ADR-123.md + docs/specs/SPEC-123.md

# Step 3: UX designs interface
squad ux 123
# ✅ Output: docs/ux/UX-123.md

# Step 4: Engineer implements
squad engineer 123
# ✅ Output: src/auth/*.py + tests/auth/*.py + PR created

# Step 5: Reviewer checks quality
squad review 456
# ✅ Output: docs/reviews/REVIEW-456.md + PR comments
```

### Example 2: Epic Planning

```bash
# Issue #100: "User Authentication System" (Epic)

# Multi-agent collaboration
squad joint-op 100 pm architect

# What happens:
# - PM drafts initial PRD
# - Architect reviews for technical feasibility
# - PM addresses concerns
# - Architect creates ADR
# - Both approve final plan
# - Output: PRD-100.md + ADR-100.md
```

### Example 3: Bug Fixing

```bash
# Issue #789: "Login returns 500 error"

# Engineer investigates and fixes
squad engineer 789

# What happens:
# - Analyzes codebase
# - Identifies root cause
# - Implements fix
# - Adds regression test
# - Creates PR with fix
```

---

## 📖 Command Reference

### Initialization

```bash
squad deploy                    # Initialize AI-Squad in project
squad sitrep                  # Validate setup
squad update                  # Update AI-Squad
```

### Agent Commands

```bash
squad pm <issue>              # 🎨 Product Manager: Create PRD
squad architect <issue>       # 🧩 Architect: Create ADR/Spec
squad engineer <issue>        # 🔧 Engineer: Implement feature
squad ux <issue>              # 🎭 UX Designer: Create design
squad review <pr>             # 🛡️ Reviewer: Review PR
```

### Orchestration Commands

```bash
squad captain <issue>         # 🎖️ Captain coordinates work
squad joint-op <issue> <agents> # Multi-agent collaboration
squad patrol                   # Auto-trigger on labels
squad run-plan <plan> <issue> # Execute a battle plan
```

### Monitoring Commands

```bash
squad status                  # View routing health status
squad ops                    # List all operations
squad convoys                 # List active convoys
squad dashboard               # Launch web dashboard
squad graph export            # Export operational graph
squad graph impact <node>     # Analyze impact of changes
```

**Examples:**
```bash
squad captain 123                   # Let Captain handle everything
squad joint-op 123 pm architect       # Epic planning
squad joint-op 456 architect engineer # Technical design + implementation
squad run-plan feature 123          # Execute feature workflow
squad status                        # Check system health
squad dashboard --port 8080         # Custom dashboard port
```

---

## ⚙️ Configuration

AI-Squad uses `squad.yaml` (created by `squad deploy`):

```yaml
# squad.yaml
version: "1.0"

project:
  name: "YourProject"
  repository: "owner/repo"

agents:
  product_manager:
    enabled: true
    model: "gpt-5.1"
    temperature: 0.3
    
  architect:
    enabled: true
    model: "claude-opus-4-5"
    temperature: 0.2
    
  engineer:
    enabled: true
    model: "gpt-5.1-codex-max"
    temperature: 0.1

# 📡 Routing Policy (NEW)
routing:
  enforce_cli_routing: false
  warn_block_rate: 0.25
  critical_block_rate: 0.5
  circuit_breaker_block_rate: 0.7
  trust_level: high
  data_sensitivity: internal

output:
  prd: "docs/prd"
  adr: "docs/adr"
  specs: "docs/specs"
  ux: "docs/ux"
  reviews: "docs/reviews"

github:
  auto_commit: true
  create_pr: false
  add_labels: true
```

**Customize models, routing policies, enable/disable agents, change output paths.**

---

## 🧩 Architecture

### System Overview

```mermaid
graph TB
    subgraph "👩‍💻 User Interface"
        CLI["🖥️ CLI Commands"]
        Dashboard["📊 Web Dashboard"]
        GH["🐙 GitHub Events"]
    end
    
    subgraph "🎖️ Orchestration Layer"
        Captain["🎖️ Captain"]
        Router["📡 Command Router"]
        BPE["📜 BattlePlan Executor"]
    end
    
    subgraph "🤖 Agent Layer"
        PM["🎨 PM"]
        Arch["🧩 Architect"]
        Eng["🔧 Engineer"]
        UX["🎭 UX"]
        Rev["🛡️ Reviewer"]
    end
    
    subgraph "⚙️ Core Services"
        WS["📦 WorkState"]
        Signal["📡 Signals"]
        Handoff["👋➡️ Handoffs"]
        Del["👉 Delegations"]
    end
    
    subgraph "💾 Persistence"
        Graph[("🕸️ Graph")]
        Events[("📊 Events")]
        Identity[("🪪 Identity")]
    end
    
    CLI & Dashboard & GH --> Captain
    Captain --> Router --> PM & Arch & Eng & UX & Rev
    Captain --> BPE
    PM & Arch & Eng & UX & Rev --> WS & Signal & Handoff
    WS --> Graph
    Del --> Graph
    Router --> Events
```

### Storage Structure

```
.squad/
├── capabilities/        # Installed capability packages
├── delegations/         # Delegation links with audit trails
├── events/              # Routing events (JSONL)
├── graph/               # Operational graph (nodes + edges)
├── handoffs/            # Handoff records
├── identity/            # Current identity dossier
├── scout_workers/       # Scout run checkpoints
├── signals/             # Inter-agent messages
└── work_items/          # operation state
```

### CLI Tool + GitHub Actions

```
┌─────────────────────────────────────────────────────────┐
│ High Command                                             │
│   ↓                                                      │
│ squad captain 123                                        │
│   ↓                                                      │
│ AI-Squad CLI (Python)                                   │
│   ├─ Loads squad.yaml                                   │
│   ├─ Fetches issue from GitHub                          │
│   ├─ Captain analyzes & creates operations              │
│   └─ Routes to appropriate agents                       │
│   ↓                                                      │
│ Agent Execution                                         │
│   ├─ Production skills loaded                           │
│   ├─ Tools (GitHub, templates)                          │
│   ├─ Identity dossier attached                          │
│   └─ Output generated                                   │
│   ↓                                                      │
│ Output: docs/prd/PRD-123.md (with provenance)           │
│   ↓                                                      │
│ Git commit + push (if auto_commit: true)                │
└─────────────────────────────────────────────────────────┘
```

**Key Points:**
- Runs locally OR in GitHub Actions
- No hosted service needed
- Full audit trail with Identity dossiers
- Health-aware routing with circuit breakers

---

## 💰 Cost

### AI-Squad: FREE

- ✅ CLI Tool: **$0** (MIT License)
- ✅ Installation: **$0**
- ✅ All Features: **$0**
- ✅ Updates: **$0**

### Usage Costs

| Service | Cost | Notes |
|---------|------|-------|
| GitHub Copilot | $10-39/mo per user | Already paying if using Copilot |
| GitHub Actions | Free tier: 2,000 min/mo | ~400 agent runs/mo |
| **AI-Squad** | **$0** | **Completely free** |

**No Hidden Costs:**
- ❌ No hosting fees
- ❌ No database costs
- ❌ No infrastructure
- ❌ No per-seat licensing

**ROI Example:**  
Team of 10 developers, 100 agent runs/week:
- Time saved: ~200 hours/month
- Value: ~$30,000/month
- **AI-Squad cost: $0**

---

## 🚀 Why AI-Squad?

### vs Manual Work

| Task | Manual | AI-Squad | Savings |
|------|--------|----------|---------|
| **PRD Creation** | 4-8 hours | 2 minutes | 96%+ faster |
| **Architecture Design** | 6-12 hours | 3 minutes | 97%+ faster |
| **Feature Implementation** | 2-5 days | 10-30 minutes | 90%+ faster |
| **Code Review** | 1-2 hours | 2 minutes | 98%+ faster |

### vs Other Tools

| Feature | AI-Squad | Other AI Tools |
|---------|----------|----------------|
| **Multi-agent system** | ✅ 5 specialized agents | ❌ Single generic AI |
| **Production skills** | ✅ 18 battle-tested skills | ❌ Generic advice |
| **GitHub integration** | ✅ Native issue/PR workflow | ⚠️ Manual copying |
| **Template-driven** | ✅ Standardized outputs | ❌ Inconsistent |
| **Cost** | ✅ $0 (uses your Copilot) | ⚠️ $20-100+/mo |
| **Hosting** | ✅ None needed | ⚠️ Cloud service |

---

## 📚 Documentation

- **[Quick Start Guide](docs/quickstart.md)** - Get started in 5 minutes
- **[Autonomous Mode Guide](docs/AUTONOMOUS.md)** - ⚡ NEW: Fully automatic development workflow
- **[CLI Commands Guide](docs/CLI-GUIDE.md)** - All commands with examples
- **[Configuration](docs/configuration.md)** - Customize `squad.yaml`
- **[Agents Guide](AGENTS.md)** - How each agent works
- **[Architecture Diagrams](docs/architecture/ARCHITECTURE-DIAGRAMS.md)** - Visual system design
- **[Skills Reference](docs/skills.md)** - 18 production skills
- **[GitHub Actions](docs/github-actions.md)** - Automation setup
- **[Examples](examples/)** - Real-world usage examples
- **[Contributing](CONTRIBUTING.md)** - Help improve AI-Squad

---

## 🧪 Examples

Check out the [`examples/`](examples/) directory:

- **[basic-usage/](examples/basic-usage/)** - Simple single-agent usage
- **[multi-agent-collab/](examples/multi-agent-collab/)** - PM + Architect collaboration
- **[github-actions/](examples/github-actions/)** - Full CI/CD integration
- **[custom-config/](examples/custom-config/)** - Advanced configuration

---

## 🔧 Troubleshooting

### Import Error: No module named 'github_copilot_sdk'

**Issue:** You see an error like `ModuleNotFoundError: No module named 'github_copilot_sdk'`

**Cause:** The PyPI package is named `github-copilot-sdk`, but it provides the `copilot` module (not `github_copilot_sdk`).

**Solution:** 
1. Ensure you have the latest version of AI-Squad:
   ```bash
   pip install --upgrade ai-squad
   ```

2. Verify the GitHub Copilot SDK is installed:
   ```bash
   pip install --upgrade github-copilot-sdk>=0.1.16
   ```

3. Test the import:
   ```python
   python -c "from copilot import CopilotSDK; print('✓ SDK available')"
   ```

### GitHub Authentication Required

**Issue:** Authentication errors or "GitHub authentication not configured"

**Solution: GitHub CLI OAuth Authentication**

AI-Squad uses **GitHub CLI OAuth** as the only authentication method.

```bash
# 1. Install GitHub CLI (if not installed)
winget install GitHub.cli  # Windows
brew install gh            # Mac
# Linux: https://github.com/cli/cli#installation

# 2. Authenticate with OAuth
gh auth login

# 3. Verify authentication
gh auth status

# 4. Verify AI-Squad setup
squad sitrep
```

**Why OAuth Only?**
- ✅ No manual token management or security risks
- ✅ Automatic token rotation by GitHub
- ✅ More secure than static tokens
- ✅ Supports SSO, MFA, and enterprise features
- ✅ Same auth method used by GitHub CLI
- ✅ Simpler setup - just one command

### Missing .github Files After Installation

**Issue:** After installing AI-Squad and running `squad deploy`, the `.github/` folder is missing files or is empty

**Solution:**
1. Ensure you have the latest version:
   ```bash
   pip install --upgrade ai-squad
   ```

2. Reinitialize the project:
   ```bash
   squad deploy --force
   ```

3. Verify files were created:
   ```bash
   # Windows PowerShell
   Get-ChildItem -Path ".github" -Recurse | Select-Object FullName
   
   # Linux/Mac
   find .github -type f
   ```

   You should see:
   - `.github/agents/` (5 files: pm.md, architect.md, engineer.md, ux.md, reviewer.md)
   - `.github/skills/` (18 directories with SKILL.md files)
   - `.github/templates/` (7 template files)
   - `.github/copilot-instructions.md`

### For More Issues

- Check [docs/commands.md](docs/commands.md) for detailed command usage
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup
- Open an issue: https://github.com/jnPiyush/AI-Squad/issues

---

## 🤝 Contributing

We love contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- How to set up development environment
- Code style guidelines
- How to add new agents
- How to add new skills
- Testing requirements

---

## 📜 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built on:
- [GitHub Copilot SDK](https://github.com/github/copilot-sdk) - AI agent framework
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting

Inspired by:
- [AgentX](https://github.com/jnPiyush/AgentX) - Original multi-agent workflow framework
- GitHub Copilot - Revolutionizing developer productivity

---

## 🔗 Links

- **GitHub:** https://github.com/jnPiyush/AI-Squad
- **PyPI:** https://pypi.org/project/ai-squad/
- **Documentation:** https://github.com/jnPiyush/AI-Squad/tree/main/docs
- **Issues:** https://github.com/jnPiyush/AI-Squad/issues
- **Discussions:** https://github.com/jnPiyush/AI-Squad/discussions

---

## ⭐ Star Us!

If AI-Squad saves you time, give us a star on GitHub! ⭐

It helps others discover the tool and motivates us to keep improving it.

---

**AI-Squad** - Your AI Development Squad, One Command Away 🚀












