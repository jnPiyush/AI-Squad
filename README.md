# AI-Squad

```
   ___   ____      _____                      __
  / _ | /  _/____ / __/ /_ ___  ___  ___  ___/ /
 / __ |_/ /_/___/_\ \/ / // / / _ \/ _ \/ _  / 
/_/ |_/___/     /___/_/\_, /_/\_,_/\_,_/\_,_/  
                      /___/                     
```

[![PyPI version](https://badge.fury.io/py/ai-squad.svg)](https://badge.fury.io/py/ai-squad)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Test Coverage](https://img.shields.io/badge/coverage-49%25-yellow.svg)](tests/)
[![Downloads](https://pepy.tech/badge/ai-squad)](https://pepy.tech/project/ai-squad)

> **Your AI Development Squad, One Command Away**  
> Five expert AI agents. Zero hosting costs. Beta - Core features stable, orchestration in preview.

---

## 🎯 What is AI-Squad?

AI-Squad is a **command-line tool** (Beta) that brings five specialized AI agents to your project:

- 🎨 **Product Manager** - Creates PRDs, breaks down epics into stories
- 🏗️ **Architect** - Designs solutions, writes ADRs and technical specs
- 💻 **Engineer** - Implements features with comprehensive tests
- 🎭 **UX Designer** - Creates wireframes, HTML prototypes, accessibility guidelines
- ✅ **Reviewer** - Reviews code, auto-closes issues, ensures quality

**New in v0.4.0**: Advanced orchestration (Captain, Formulas, Convoys), retry logic, rate limiting, persistent storage, performance benchmarks!

**Install once. Use everywhere. No hosting required.**

---

## ⚡ Quick Start

### 1. Install AI-Squad

```bash
pip install ai-squad
```

### 2. Initialize in Your Project

```bash
cd /path/to/your-project
squad init
```

This creates:
- ✅ `.github/workflows/` - Automated agent execution
- ✅ `.github/agents/` - Agent definitions
- ✅ `.github/skills/` - 18 production skills
- ✅ `.github/templates/` - Document templates
- ✅ `squad.yaml` - Configuration
- ✅ `docs/` - Output directories

### 3. Use Your Squad!

```bash
# Create PRD for an issue
squad pm 123

# Design architecture
squad architect 123

# Implement feature
squad engineer 123

# Multi-agent collaboration
squad collab 100 pm architect

# Automatic orchestration (watch mode)
squad watch
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

## 🚀 Features

### 🤖 Five Expert Agents

| Agent | Command | Output |
|-------|---------|--------|
| **Product Manager** | `squad pm <issue>` | PRD + User Stories + Backlog |
| **Architect** | `squad architect <issue>` | ADR + Technical Spec + Diagrams |
| **Engineer** | `squad engineer <issue>` | Code + Tests + Documentation |
| **UX Designer** | `squad ux <issue>` | Wireframes + User Flows + Guidelines |
| **Reviewer** | `squad review <pr>` | Code Review + Security Analysis |

### 🧠 Multi-Agent Collaboration

```bash
# PM and Architect collaborate on Epic planning
squad collab 100 pm architect

# Flow:
# 1. PM drafts PRD
# 2. Architect reviews for feasibility
# 3. They iterate together
# 4. Both finalize documents
```

### 📚 18 Production Skills

Every agent follows battle-tested production standards:

**Foundation:** Testing, Security, Error Handling, Core Principles  
**Architecture:** Performance, Scalability, Database, API Design  
**Development:** Configuration, Documentation, Type Safety, Logging  
**Operations:** Git Workflows, Code Review, Deployment

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
squad collab 100 pm architect

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
squad init                    # Initialize AI-Squad in project
squad doctor                  # Validate setup
squad update                  # Update AI-Squad
```

### Agent Commands

```bash
squad pm <issue>              # Product Manager: Create PRD
squad architect <issue>       # Architect: Create ADR/Spec
squad engineer <issue>        # Engineer: Implement feature
squad ux <issue>              # UX Designer: Create design
squad review <pr>             # Reviewer: Review PR
```

### Collaboration

```bash
squad collab <issue> <agents>  # Multi-agent collaboration
squad chat <agent>             # Interactive mode with agent
```

**Examples:**
```bash
squad collab 123 pm architect       # Epic planning
squad collab 456 architect engineer # Technical design + implementation
squad collab 789 ux engineer        # Design + development
squad chat engineer                  # Ask engineer questions interactively
```

---

## ⚙️ Configuration

AI-Squad uses `squad.yaml` (created by `squad init`):

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
    model: "claude-opus-4-5"  # Best for architecture
    temperature: 0.2
    
  engineer:
    enabled: true
    model: "gpt-5.1-codex-max"  # Best for coding
    temperature: 0.1

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

**Customize models, enable/disable agents, change output paths.**

---

## 🏗️ Architecture

### CLI Tool + GitHub Actions

```
┌─────────────────────────────────────────────────────────┐
│ Developer                                                │
│   ↓                                                      │
│ squad pm 123                                             │
│   ↓                                                      │
│ AI-Squad CLI (Python)                                   │
│   ├─ Loads squad.yaml                                   │
│   ├─ Fetches issue from GitHub                          │
│   ├─ Loads agent definition                             │
│   └─ Initializes Copilot SDK                            │
│   ↓                                                      │
│ Copilot SDK Session                                     │
│   ├─ Custom agent (PM)                                  │
│   ├─ Production skills                                  │
│   ├─ Tools (GitHub, templates)                          │
│   └─ Executes task                                      │
│   ↓                                                      │
│ Output: docs/prd/PRD-123.md                             │
│   ↓                                                      │
│ Git commit + push (if auto_commit: true)                │
└─────────────────────────────────────────────────────────┘

GitHub Actions (Optional)
┌─────────────────────────────────────────────────────────┐
│ Issue labeled 'type:feature'                            │
│   ↓                                                      │
│ Workflow triggered                                      │
│   ├─ Install: pip install ai-squad                     │
│   ├─ Execute: squad pm $ISSUE_NUMBER                   │
│   └─ Commit output                                      │
└─────────────────────────────────────────────────────────┘
```

**Key Points:**
- Runs locally OR in GitHub Actions
- No hosted service
- No Docker containers
- Zero infrastructure costs

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
- **[Command Reference](docs/commands.md)** - All commands explained
- **[Configuration](docs/configuration.md)** - Customize `squad.yaml`
- **[Agents Guide](docs/agents.md)** - How each agent works
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

