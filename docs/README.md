# AI-Squad Documentation

Welcome to AI-Squad! 🎖️ Five expert AI agents orchestrated by a Captain.

## Quick Links

- [Quick Start Guide](../QUICK-START.md) - Get up and running in 5 minutes
- [Commands Reference](commands.md) - All available commands
- [Configuration](configuration.md) - Customize AI-Squad
- [Orchestration Guide](ORCHESTRATION.md) - Battle Plans, Convoys, Handoffs
- [Agents Guide](../AGENTS.md) - Learn about each agent
- [Architecture](architecture/ARCHITECTURE.md) - System design diagrams
- [Contributing](../CONTRIBUTING.md) - Contribute to AI-Squad

## What is AI-Squad?

AI-Squad is a CLI tool that brings five expert AI agents to your project:

1. **Product Manager** - Creates PRDs and breaks down epics
2. **Architect** - Designs solutions and writes ADRs
3. **Engineer** - Implements features with tests
4. **UX Designer** - Creates wireframes and flows
5. **Reviewer** - Reviews code and ensures quality

## Why AI-Squad?

- **96%+ faster** than manual development process
- **Zero hosting costs** - runs locally or in GitHub Actions
- **Production-ready** - follows 18 production skills
- **Hook persistence** - work items survive restarts
- **Worker lifecycle** - track ephemeral agent runs
- **Template-driven** - consistent documentation
- **Multi-agent collaboration** - coordinated teamwork

## Architecture

```
User Command → AI-Squad CLI → Provider Chain → Agent Execution → Output
```

**Local Mode:** Runs on your machine  
**GitHub Actions:** Runs on issue/PR events

## Getting Started

### Install

```bash
pip install ai-squad
```

### Initialize

```bash
cd your-project
squad init
```

### Configure

```bash
gh auth login
```

### Run

```bash
squad pm 123      # Create PRD for issue #123
squad engineer 456 # Implement issue #456
```

## Learn More

- [Quick Start →](../QUICK-START.md)
- [Commands →](commands.md)
- [Examples →](../examples/)
- [GitHub Repository](https://github.com/jnPiyush/AI-Squad)

---

**Need Help?** [Open an issue](https://github.com/jnPiyush/AI-Squad/issues) or [start a discussion](https://github.com/jnPiyush/AI-Squad/discussions)

