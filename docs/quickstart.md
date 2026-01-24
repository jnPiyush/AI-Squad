# Quick Start Guide

Get AI-Squad running in 30 seconds!

## Prerequisites

- **Python 3.11+**
- **Git** (repository)
- **GitHub account** with Copilot subscription
- **GitHub Personal Access Token** with `repo` and `workflow` scopes

## Installation

### Option 1: PyPI (Recommended)

```bash
pip install ai-squad
```

### Option 2: From Source

```bash
git clone https://github.com/jnPiyush/AI-Squad.git
cd AI-Squad
pip install -e .
```

## Setup

### 1. Initialize in Your Project

```bash
cd your-project
squad init
```

This creates:
- `squad.yaml` - Configuration file
- `docs/` - Output directories (prd, adr, specs, ux, reviews)
- `.github/` - Templates, skills, agents

### 2. Configure GitHub Token

**Linux/Mac:**
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

**Windows PowerShell:**
```powershell
$env:GITHUB_TOKEN="ghp_your_token_here"
```

**Permanent (add to `.bashrc` or PowerShell profile):**
```bash
echo 'export GITHUB_TOKEN=ghp_your_token_here' >> ~/.bashrc
```

### 3. Update Configuration

Edit `squad.yaml`:

```yaml
project:
  name: My Project
  github_repo: my-repo
  github_owner: my-username

agents:
  pm:
    enabled: true
    model: gpt-4
  # ... other agents

output:
  prd_dir: docs/prd
  adr_dir: docs/adr
  # ... other dirs
```

## Your First Command

### Create a PRD

```bash
# Create a GitHub issue first
gh issue create --title "[Story] Add user authentication"

# Run Product Manager
squad pm 123
```

**Output:** `docs/prd/PRD-123.md`

### Design the Solution

```bash
squad architect 123
```

**Output:**
- `docs/adr/ADR-123.md`
- `docs/specs/SPEC-123.md`

### Implement the Feature

```bash
squad engineer 123
```

**Output:** Implementation files with tests

### Create UX Design

```bash
squad ux 123
```

**Output:** `docs/ux/UX-123.md`

### Review a PR

```bash
# Create PR first
gh pr create --title "Add authentication"

# Run Reviewer
squad review 456
```

**Output:** `docs/reviews/REVIEW-456.md`

## Multi-Agent Collaboration

Run multiple agents in sequence:

```bash
# Epic planning (PM + Architect)
squad collab 123 pm architect

# Feature development (Architect + Engineer + UX)
squad collab 456 architect engineer ux

# Full workflow (PM → Architect → Engineer → UX)
squad collab 789 pm architect engineer ux
```

## Validate Setup

Check if everything is configured correctly:

```bash
squad doctor
```

**Output:**
```
✅ GitHub Token: Found
✅ Configuration: Found squad.yaml
✅ Output Directories: All directories exist
✅ Copilot SDK: Installed (v0.1.16)
✅ Git Repository: Found .git/
```

## Common Workflows

### New Feature Development

```bash
# 1. Create epic
gh issue create --title "[Epic] User Management System"

# 2. PM creates PRD
squad pm 100

# 3. Architect designs solution
squad architect 100

# 4. UX creates designs (if UI feature)
squad ux 100

# 5. Engineer implements
squad engineer 101  # feature issue

# 6. Review PR
squad review 102
```

### Bug Fix

```bash
# 1. Create bug issue
gh issue create --title "[Bug] Login fails with special characters"

# 2. Engineer fixes bug
squad engineer 200

# 3. Review fix
squad review 201
```

### Design Review

```bash
# 1. Create design issue
gh issue create --title "[Design] Redesign dashboard"

# 2. UX creates design
squad ux 300

# 3. Review design (manual)
# Review docs/ux/UX-300.md
```

## GitHub Actions Integration

Enable automated workflows:

```bash
# Initialize creates workflow templates
squad init

# Copy to active workflows
cp .github/workflows/squad-*.yml.template .github/workflows/

# Remove .template extension
# Workflows trigger on issue/PR events
```

## Next Steps

- **[Commands Reference](commands.md)** - All available commands
- **[Configuration Guide](configuration.md)** - Customize AI-Squad
- **[Agents Guide](agents.md)** - Learn about each agent
- **[Workflows](workflows.md)** - Multi-agent patterns
- **[Examples](../examples/)** - Sample projects

## Troubleshooting

### Command Not Found

```bash
# Ensure pip install directory is in PATH
python -m pip install --user ai-squad

# Or use full path
python -m ai_squad.cli
```

### GitHub Token Not Working

```bash
# Test token
gh auth status

# Refresh token
gh auth refresh -s repo,workflow
```

### SDK Not Found

```bash
# Install explicitly
pip install github-copilot-sdk>=0.1.16
```

### Need More Help?

Run diagnostics:
```bash
squad doctor
```

Or [open an issue](https://github.com/jnPiyush/AI-Squad/issues).

---

**Ready to go?** Try: `squad pm 123` to create your first PRD!

