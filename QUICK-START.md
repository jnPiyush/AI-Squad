# AI-Squad Quick Start Guide

> Get started with AI-Squad in 5 minutes! 🚀

---

## ✅ Installation Verified

The package has been successfully installed and tested:

```bash
$ squad --version
AI-Squad version 0.6.0

$ squad --help
Usage: squad [OPTIONS] COMMAND [ARGS]...
  AI-Squad - Your AI Development Squad
  ...
```

---

## 🎯 First-Time Setup

### Step 1: Install AI-Squad

```bash
# Already completed! ✅
pip install -e .
```

### Step 2: Initialize Your Project

```bash
cd /path/to/your/project
squad deploy
```

This creates:
- `squad.yaml` - Configuration file
- `docs/` directory structure
- Copies production skills to `.ai-squad/skills/`
- Creates helpful README

### Step 3: Authenticate with GitHub

```bash
# Install GitHub CLI (if not installed)
winget install GitHub.cli  # Windows
brew install gh            # Mac

# Authenticate via OAuth (one command!)
gh auth login

# Verify
gh auth status
```

**Why OAuth?**
- ✅ Secure (no manual tokens)
- ✅ One command setup
- ✅ Works with SSO/MFA
echo 'export GITHUB_TOKEN=ghp_your_token_here' >> ~/.bashrc
```

**Get a GitHub token**:
1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`
4. Copy token immediately (shown only once)

### Step 4: Verify Setup

```bash
squad sitrep
```

Expected output when fully configured:
```
✅ GitHub Token: Set
✅ Configuration: Found (squad.yaml)
✅ Output Directories: Created
✅ GitHub Copilot SDK: Available
✅ Git Repository: Initialized

🎉 All checks passed!
```

---

## 🤖 Using Your AI Squad

### Single Agent Workflow

**1. Product Manager** - Create PRD
```bash
squad pm 123
# Creates: docs/prd/PRD-123.md
# Contains: User stories, acceptance criteria, requirements
```

**2. Architect** - Design Solution
```bash
squad architect 123
# Creates: docs/adr/ADR-123.md, docs/specs/SPEC-123.md, docs/architecture/ARCH-123.md
# Contains: Technical decisions, architecture, implementation plan
```

**3. Engineer** - Implement Feature
```bash
squad engineer 123
# Creates: Code changes, tests, documentation
# Follows: SOLID principles, test coverage ≥80%
```

**4. UX Designer** - Create Design
```bash
squad ux 123
# Creates: docs/ux/UX-123.md
# Contains: Wireframes, user flows, accessibility notes
```

**5. Reviewer** - Review Code
```bash
squad review 456  # PR number
# Creates: docs/reviews/REVIEW-456.md
# Contains: Code quality, security, test coverage feedback
```

### Multi-Agent Collaboration

**Run multiple agents sequentially:**
```bash
squad joint-op 123 pm architect engineer
# PM creates PRD → Architect designs → Engineer implements
# Results aggregated in terminal
```

**Run all agents:**
```bash
squad joint-op 123 --all
# Full workflow: PM → UX → Architect → Engineer → Reviewer
```

---

## 📋 Real-World Example

### Scenario: Add Health Check Endpoint

**1. Create GitHub Issue**
```bash
gh issue create --title "Add health check endpoint" --body "Need /health for monitoring"
# Issue #789 created
```

**2. Run PM Agent**
```bash
squad pm 789
```

Output: `docs/prd/PRD-789.md`
```markdown
# PRD: Health Check Endpoint

## User Stories
- AS a DevOps engineer
- I WANT a health check endpoint
- SO THAT I can monitor service status
...
```

**3. Run Architect Agent**
```bash
squad architect 789
```

Output: `docs/adr/ADR-789.md`, `docs/specs/SPEC-789.md`
```markdown
# ADR: Health Check Implementation

## Decision
Implement ASP.NET Core health checks with:
- /health/live - Liveness probe
- /health/ready - Readiness probe
...
```

**4. Run Engineer Agent**
```bash
squad engineer 789
```

Output: Code changes committed
```csharp
// Program.cs
builder.Services.AddHealthChecks()
    .AddNpgSql(connectionString);
app.MapHealthChecks("/health/live");
...
```

**5. Create PR and Review**
```bash
gh pr create --fill
# PR #790 created

squad review 790
```

Output: `docs/reviews/REVIEW-790.md`
```markdown
# Code Review: Health Check Implementation

## Summary
✅ APPROVED - High quality implementation

## Checklist
✅ Code quality - Follows SOLID principles
✅ Tests - 95% coverage
✅ Security - No vulnerabilities
...
```

---

## 🎨 Common Workflows

### Epic Planning
```bash
# 1. Create epic issue
gh issue create --title "[Epic] User Authentication" --label "type:epic"

# 2. Run PM to break down
squad pm 100

# 3. Collaborate on architecture
squad joint-op 100 pm ux architect

# 4. Implement features individually
squad engineer 101  # Login
squad engineer 102  # Signup
squad engineer 103  # Password reset
```

### Bug Fix
```bash
# 1. Reproduce bug
squad engineer 456 --task "Fix login timeout"

# 2. Review fix
gh pr create --fill
squad review 789
```

### Documentation Update
```bash
# Update docs only
squad pm 555 --no-github  # Use mock data for testing
# Or manually edit and commit
```

---

## ⚙️ Configuration Tips

### Custom Output Paths

Edit `squad.yaml`:
```yaml
outputs:
  prd_dir: "documentation/requirements"
  adr_dir: "architecture/decisions"
  specs_dir: "architecture/specs"
  ux_dir: "design/ux"
  reviews_dir: "quality/reviews"
```

### Custom Agent Settings

```yaml
agents:
  model: "gpt-4"          # or "gpt-3.5-turbo"
  temperature: 0.7        # 0.0 = deterministic, 1.0 = creative
  max_tokens: 4096        # Response length limit
```

### Project-Specific Skills

```bash
# Copy custom skills
cp /path/to/custom-skills/* .ai-squad/skills/

# Reference in agent prompts
# Edit ai_squad/agents/engineer.py to load custom skills
```

---

## 🐛 Troubleshooting

### "GitHub authentication required"
```bash
# Authenticate with GitHub CLI
gh auth login

# Verify authentication
gh auth status

# Verify AI-Squad setup
squad sitrep
```

### "Configuration not found"
```bash
# Run init in project root
cd /path/to/project
squad deploy
```

### "Module not found: ai_squad"
```bash
# Reinstall in development mode
cd /path/to/AI-Squad
pip install -e .
```

### "GitHub API rate limit"
```bash
# Check rate limit (uses gh CLI OAuth)
gh api rate_limit

# OAuth provides higher rate limits than tokens
```

### "Agent timeout"
```bash
# Increase timeout in squad.yaml
agents:
  timeout: 300  # 5 minutes
```

---

## 📚 Next Steps

### Learn More
- **Full Documentation**: [docs/README.md](docs/README.md)
- **Command Reference**: [docs/commands.md](docs/commands.md)
- **Configuration Guide**: [docs/configuration.md](docs/configuration.md)
- **Examples**: [examples/](examples/)

### Contribute
- **Contributing Guide**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **Code Standards**: Follow skills in `.ai-squad/skills/`
- **Report Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

### Advanced Usage
- **Custom Agents**: Plugin system (coming soon)
- **CI/CD Integration**: GitHub Actions examples
- **Team Setup**: Shared configurations
- **Self-Hosting**: Enterprise deployment

---

## 🎉 You're Ready!

**Your AI development squad is ready to assist.**

Try your first command:
```bash
cd your-project
squad deploy
squad sitrep
squad pm 123
```

**Need help?** Run `squad COMMAND --help` for any command.

**Happy coding with your AI Squad! 🚀**

---

**Last Updated**: January 22, 2026  
**AI-Squad Version**: 0.6.0
