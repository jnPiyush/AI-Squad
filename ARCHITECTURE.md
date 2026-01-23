# AI-Squad Architecture

## Component Wiring

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   GitHub Copilot Chat              CLI Commands              │
│   "PM, help with reqs"             squad pm 123              │
│          │                              │                    │
│          ▼                              ▼                    │
│   .github/                        ai_squad/                  │
│   ├─ copilot-instructions.md      ├─ cli.py                 │
│   └─ agents/                      ├─ agents/                │
│      ├─ pm.md ◄──────────────────►│  ├─ product_manager.py  │
│      ├─ architect.md ◄───────────►│  ├─ architect.py        │
│      ├─ engineer.md ◄────────────►│  ├─ engineer.py         │
│      ├─ ux.md ◄──────────────────►│  ├─ ux_designer.py      │
│      └─ reviewer.md ◄────────────►│  └─ reviewer.py         │
│                                    │                         │
│   (Guidance)                      (Execution)               │
│                                        │                     │
│                                        ▼                     │
│                                   SHARED RESOURCES           │
│                             ┌──────────────────────┐         │
│                             │ ai_squad/skills/     │         │
│                             │ (18 skills)          │         │
│                             │ • core-principles    │         │
│                             │ • api-design         │         │
│                             │ • testing            │         │
│                             │ • security           │         │
│                             │ • etc.               │         │
│                             └──────────────────────┘         │
│                             ┌──────────────────────┐         │
│                             │ ai_squad/tools/      │         │
│                             │ • templates.py       │         │
│                             │ • github.py          │         │
│                             │ • codebase.py        │         │
│                             └──────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

## How Components Are Wired

### Chat → CLI Integration

When you talk to agents in Copilot Chat, I can **execute the CLI** for actual work:

```
You: "PM, create a PRD for issue #123"
     │
     ▼
Copilot reads .github/copilot-instructions.md
     │
     ▼
Copilot uses run_in_terminal to execute:
     │
     └──→ squad pm 123
              │
              ▼
         ai_squad/agents/product_manager.py runs
              │
              ▼
         Creates docs/prd/PRD-123.md
              │
              ▼
Copilot reports: "✅ PRD created at docs/prd/PRD-123.md"
```

### 1. Agent Definitions (Aligned)

| Copilot (.github/agents/) | CLI (ai_squad/agents/) | Skills Used |
|---------------------------|------------------------|-------------|
| pm.md | product_manager.py | core-principles, documentation |
| architect.md | architect.py | api-design, database, scalability, security |
| engineer.md | engineer.py | testing, error-handling, code-organization, type-safety |
| ux.md | ux_designer.py | documentation, core-principles |
| reviewer.md | reviewer.py | code-review-and-audit, security, performance, testing |

### 2. Template System

Templates are **embedded** in `ai_squad/tools/templates.py`:
- `_get_prd_template()` - PRD template
- `_get_adr_template()` - ADR template  
- `_get_spec_template()` - Spec template
- `_get_ux_template()` - UX template
- `_get_review_template()` - Review template

**NOT** a separate `/templates/` directory.

### 3. Skills System

All 18 skills in `ai_squad/skills/`:
```
ai-agent-development  api-design         code-organization
code-review-and-audit configuration      core-principles
database              dependency-management  documentation
error-handling        logging-monitoring performance
remote-git-operations scalability        security
testing               type-safety        version-control
```

### 4. Config Flow

```
squad.yaml (user config)
    ↓
ai_squad/core/config.py (loads config)
    ↓
ai_squad/core/agent_executor.py (creates agents with config)
    ↓
ai_squad/agents/*.py (agents use config for model, skills, etc.)
```

## Key Files

| Purpose | File |
|---------|------|
| CLI entry | ai_squad/cli.py |
| Agent execution | ai_squad/core/agent_executor.py |
| Configuration | ai_squad/core/config.py |
| Watch mode | ai_squad/core/watch.py |
| Status tracking | ai_squad/core/status.py |
| GitHub API | ai_squad/tools/github.py |
| Templates | ai_squad/tools/templates.py |
| Copilot context | .github/copilot-instructions.md |
| Agent definitions | .github/agents/*.md |

## No Conflicts

✅ **Copilot agents** (.github/agents/*.md) provide **guidance**  
✅ **CLI agents** (ai_squad/agents/*.py) provide **execution**  
✅ **Both reference** the same skills and templates  
✅ **Both produce** output in same directories (docs/prd/, etc.)  
✅ **Skills references** are now accurate (actual directories)  
✅ **Template references** are now accurate (embedded in .py)

## Usage

### CLI
```bash
squad pm 123         # Execute PM agent
squad architect 123  # Execute Architect agent
squad engineer 123   # Execute Engineer agent
squad watch          # Auto-orchestration
```

### Copilot Chat
```
"PM, create requirements for login"    → Guidance
"Architect, design a REST API"         → Guidance
"Engineer, implement authentication"   → Guidance
```

Both can be used together - Copilot for exploration, CLI for execution.
