# Commands Reference

Complete reference for all AI-Squad commands.

## Command Format

```bash
squad [command] [arguments] [options]
```

## Global Options

- `--version` - Show AI-Squad version
- `--help` - Show help message

## Commands

### `squad init`

Initialize AI-Squad in your project.

**Usage:**
```bash
squad init [--force]
```

**Options:**
- `--force` - Overwrite existing files

**What it does:**
1. Creates `squad.yaml` configuration
2. Creates output directories (`docs/prd`, `docs/adr`, etc.)
3. Copies templates to `.github/templates/`
4. Copies 18 production skills to `.github/skills/`
5. Creates README with AI-Squad badge

**Example:**
```bash
cd my-project
squad init
```

---

### `squad pm <issue#>`

Run Product Manager agent - creates PRD.

**Usage:**
```bash
squad pm <issue-number>
```

**Arguments:**
- `issue-number` - GitHub issue number

**Output:**
- `docs/prd/PRD-<issue>.md` - Product Requirements Document
- Feature issues (if epic)

**Example:**
```bash
squad pm 123
```

**When to use:**
- New feature requests
- Epic planning
- Requirements gathering

---

### `squad architect <issue#>`

Run Architect agent - creates ADR and technical spec.

**Usage:**
```bash
squad architect <issue-number>
```

**Arguments:**
- `issue-number` - GitHub issue number

**Output:**
- `docs/adr/ADR-<issue>.md` - Architecture Decision Record
- `docs/specs/SPEC-<issue>.md` - Technical Specification

**Example:**
```bash
squad architect 456
```

**When to use:**
- After PRD is complete
- Technical design needed
- Architecture decisions required

---

### `squad engineer <issue#>`

Run Engineer agent - implements feature with tests.

**Usage:**
```bash
squad engineer <issue-number>
```

**Arguments:**
- `issue-number` - GitHub issue number

**Output:**
- Implementation files
- Unit tests
- Integration tests
- Documentation

**Example:**
```bash
squad engineer 789
```

**When to use:**
- After technical spec is ready
- Implementing features
- Fixing bugs

---

### `squad ux <issue#>`

Run UX Designer agent - creates wireframes and flows.

**Usage:**
```bash
squad ux <issue-number>
```

**Arguments:**
- `issue-number` - GitHub issue number

**Output:**
- `docs/ux/UX-<issue>.md` - UX Design Document
- Wireframes (ASCII art / Mermaid)
- User flows
- Accessibility checklist

**Example:**
```bash
squad ux 101
```

**When to use:**
- UI features
- After PRD is complete
- Before implementation

---

### `squad review <pr#>`

Run Reviewer agent - reviews code quality.

**Usage:**
```bash
squad review <pr-number>
```

**Arguments:**
- `pr-number` - GitHub pull request number

**Output:**
- `docs/reviews/REVIEW-<pr>.md` - Code Review Report

**Example:**
```bash
squad review 202
```

**When to use:**
- After implementation
- Before merging PR
- Code quality checks

---

### `squad collab <issue#> <agents...>`

Multi-agent collaboration - run multiple agents in sequence.

**Usage:**
```bash
squad collab <issue-number> <agent1> <agent2> [agent3...]
```

**Arguments:**
- `issue-number` - GitHub issue number
- `agents` - Space-separated agent names (`pm`, `architect`, `engineer`, `ux`, `reviewer`)

**Example:**
```bash
# Epic planning
squad collab 123 pm architect

# Feature development
squad collab 456 architect engineer ux

# Full workflow
squad collab 789 pm architect engineer ux
```

**Common Patterns:**

**Epic Planning:**
```bash
squad collab <epic#> pm architect
```

**Feature Development:**
```bash
squad collab <feature#> architect engineer ux
```

**Bug Fix:**
```bash
squad collab <bug#> engineer
```

**Design Review:**
```bash
squad collab <design#> ux architect
```

---

### `squad chat <agent>`

Interactive chat with an agent (coming soon).

**Usage:**
```bash
squad chat <agent-type>
```

**Arguments:**
- `agent-type` - Agent to chat with (`pm`, `architect`, `engineer`, `ux`, `reviewer`)

**Example:**
```bash
squad chat engineer
> How should I implement authentication?
...
> exit
```

**Status:** Coming in v0.2.0

---

### `squad doctor`

Validate AI-Squad setup and configuration.

**Usage:**
```bash
squad doctor
```

**Checks:**
- ✅ GitHub Token present
- ✅ Configuration file exists
- ✅ Output directories exist
- ✅ Copilot SDK installed
- ✅ Git repository present

**Example:**
```bash
squad doctor
```

**Output:**
```
Running diagnostic checks...

✅ GitHub Token: Found
✅ Configuration: Found squad.yaml
✅ Output Directories: All directories exist
✅ Copilot SDK: Installed (v0.1.16)
✅ Git Repository: Found .git/

All checks passed! AI-Squad is ready to use.
```

---

### `squad update`

Update AI-Squad to latest version.

**Usage:**
```bash
squad update
```

**What it does:**
- Runs `pip install --upgrade ai-squad`
- Updates to latest PyPI version

**Example:**
```bash
squad update
```

---

## Command Chaining

You can run commands in sequence using shell operators:

```bash
# Run PM, then Architect
squad pm 123 && squad architect 123

# Run Architect, then Engineer if successful
squad architect 456 && squad engineer 456

# Full workflow
squad pm 789 && squad architect 789 && squad engineer 789
```

## Environment Variables

### `GITHUB_TOKEN`

**Required:** Yes  
**Description:** GitHub Personal Access Token with `repo` and `workflow` scopes

**Set:**
```bash
export GITHUB_TOKEN=ghp_your_token_here
```

### `SQUAD_CONFIG`

**Required:** No  
**Description:** Path to custom `squad.yaml` file  
**Default:** `./squad.yaml`

**Set:**
```bash
export SQUAD_CONFIG=/path/to/custom-squad.yaml
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | GitHub error |
| 4 | Agent execution error |

## Examples

### Full Feature Development Workflow

```bash
# 1. Create issue
gh issue create --title "[Feature] User authentication" --label "type:feature"

# 2. Run PM for PRD
squad pm 100

# 3. Run Architect for design
squad architect 100

# 4. Run UX for interface
squad ux 100

# 5. Run Engineer for implementation
squad engineer 100

# 6. Create PR
gh pr create --title "Add user authentication"

# 7. Run Reviewer
squad review 101
```

### Bug Fix Workflow

```bash
# 1. Create bug issue
gh issue create --title "[Bug] Login fails" --label "type:bug,priority:p0"

# 2. Run Engineer to fix
squad engineer 200

# 3. Create PR
gh pr create --title "Fix login bug"

# 4. Review
squad review 201
```

### Epic Planning Workflow

```bash
# 1. Create epic
gh issue create --title "[Epic] User Management System" --label "type:epic"

# 2. PM creates PRD and breaks down
squad pm 300

# 3. Architect reviews and designs
squad architect 300

# PM creates feature issues (manual or automated)
# Agents work on features individually
```

## Tips

1. **Always create issues first** - Agents work on existing issues
2. **Use labels** - `type:feature`, `type:bug`, etc. for clarity
3. **Run doctor after init** - Validate setup
4. **Use collab for workflows** - More efficient than individual commands
5. **Review outputs** - Always review generated documents before using

## Next Steps

- [Configuration Guide](configuration.md) - Customize agents
- [Agents Guide](agents.md) - Learn about each agent
- [Workflows](workflows.md) - Multi-agent patterns
- [GitHub Actions](github-actions.md) - Automate with CI/CD

---

**Need help?** Run `squad <command> --help` or [open an issue](https://github.com/jnPiyush/AI-Squad/issues).

