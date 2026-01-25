# Autonomous Mode Guide

## Overview

Autonomous Mode (`squad auto`) enables true autonomous app development by accepting your requirements and handling the entire workflow from issue creation to execution.

**No more manual issue creation!** Just describe what you want, and Squad takes care of everything.

---

## Quick Start

### Basic Usage

```bash
# Inline mission brief (DEPLOYS TO CAPTAIN - full orchestration)
squad auto -p "Create a REST API for user management"

# From mission brief file
squad auto -f mission-brief.txt

# Interactive mission briefing
squad auto -i

# Create mission brief only (manual Captain deployment)
squad auto -p "Add authentication system" --plan-only
# Then deploy manually:
squad captain <mission-issue-number>
```

---

## How It Works

### Workflow (🎖️ SQUAD MISSION - CAPTAIN DEPLOYMENT)

```
1. High Command provides mission brief (inline, file, or interactive)
   ↓
2. PM validates mission type (epic vs feature)
   ↓
3. Creates Mission Brief in GitHub
   ↓
4. Breaks down into Mission Objectives (stories)
   ↓
5. 🎖️ DEPLOYS TO CAPTAIN for orchestration:
   - Captain analyzes mission
   - Selects appropriate Battle Plan
   - Creates Work Items for tracking
   - Organizes into Convoys (parallel batches)
   - **EXECUTES agents via collaboration**:
     * PM: Creates PRD
     * Architect: Creates ADR and specs
     * Engineer: Implements with tests
     * UX: Creates designs (if UI)
     * Reviewer: Reviews and creates PRs
   ↓
6. Multi-agent team completes mission with Captain coordination
```

### What Gets Created

**Epic Issue:**
- `[Epic] Your Requirement Title`
- Contains full description
- Lists all user stories
- Tagged with `type:epic` and `ai-squad:auto`

**Story Issues:**
- `[Story] User Story Description`
- Linked to epic
- Acceptance criteria included
- Tagged with `type:story` and `ai-squad:auto`

---

## Command Options

### Input Methods (choose ONE)

| Option | Description | Example |
|--------|-------------|---------|
| `--prompt` / `-p` | Inline requirement text | `squad auto -p "Create user auth"` |
| `--file` / `-f` | Requirements from file | `squad auto -f requirements.txt` |
| `--interactive` / `-i` | Interactive input mode | `squad auto -i` |

### Execution Options

| Option | Description |
|--------|-------------|
| `--auto-execute` | Automatically run agents after creating issues |

---

## Examples

### Example 1: Simple Feature

```bash
squad auto -p "Create a health check endpoint that returns server status"
```

**Creates:**
- Epic: `[Epic] Create a health check endpoint`
- Story: `[Story] Create health check endpoint that returns server status`

### Example 2: Complex Feature from File

**requirements.txt:**
```
User Management System

As a user, I want to register an account
As a user, I want to login with email/password
As a user, I want to reset my forgotten password
As an admin, I want to manage user roles
```

```bash
squad auto -f requirements.txt --auto-execute
```

**Creates:**
- Epic: `[Epic] User Management System`
- Story 1: `[Story] User registration`
- Story 2: `[Story] User login`
- Story 3: `[Story] Password reset`
- Story 4: `[Story] Admin role management`
- **Automatically runs agents to implement!**

### Example 3: Interactive Mode

```bash
squad auto -i
```

**You type:**
```
Payment Integration

- Integrate Stripe payment gateway
- Support credit cards and ACH
- Handle webhooks for payment events
- Add payment history page
```

**Press Ctrl+D (Linux/Mac) or Ctrl+Z (Windows) to submit**

---

## Requirements File Format

### Basic Format

```
Title of Feature

Description paragraph...

As a <user>, I want <goal>
As a <user>, I want <another goal>

- Additional requirement
- Another requirement
```

### Example

```
REST API for Blog

A complete REST API for a blogging platform with authentication,
post management, and commenting features.

As a blogger, I want to create and publish posts
As a blogger, I want to manage my drafts
As a reader, I want to comment on posts
As a reader, I want to follow my favorite bloggers

- API should follow REST best practices
- Authentication using JWT
- Rate limiting on all endpoints
- OpenAPI/Swagger documentation
```

---

## Autonomous vs Traditional Flow

### Traditional Flow (Manual)

```bash
# Step 1: Manually create issue in GitHub
gh issue create --title "Feature X" --label "type:story"
# Issue #123 created

# Step 2: Run agents one by one
squad pm 123
squad architect 123
squad engineer 123
squad review <pr>
```

**Drawbacks:**
- ❌ Manual issue creation
- ❌ Need to track issue numbers
- ❌ Run each agent separately
- ❌ Manual orchestration

### Autonomous Flow (New)

```bash
# One command does everything!
squad auto -p "Implement Feature X" --auto-execute
```

**Benefits:**
- ✅ Issues created automatically
- ✅ Epic + Stories organized
- ✅ Agents orchestrated automatically
- ✅ True autonomous development

---

## Best Practices

### Writing Good Requirements

**DO:**
- ✅ Be specific and clear
- ✅ Include user stories ("As a user...")
- ✅ Mention acceptance criteria
- ✅ Specify technical constraints
- ✅ Break down complex features

**DON'T:**
- ❌ Be too vague ("make it better")
- ❌ Mix multiple unrelated features
- ❌ Skip important context
- ❌ Assume technical details

### When to Use Auto-Execute

**Use `--auto-execute`:**
- ✅ Well-defined requirements
- ✅ Standard features
- ✅ Trust Squad's decision-making
- ✅ Want full automation

**Don't use `--auto-execute`:**
- ⚠️ Complex/ambiguous requirements
- ⚠️ Need to review issues first
- ⚠️ Want manual control
- ⚠️ Prototype/experiment phase

---

## Monitoring Progress

### View Created Issues

```bash
# List all auto-created issues
gh issue list --label "ai-squad:auto"

# View specific epic
gh issue view <epic-number>
```

### Dashboard Tracking

```bash
squad dashboard
# View progress in web UI at http://127.0.0.1:5050
```

---

## Troubleshooting

### "Requirements cannot be empty"

**Cause:** Empty input or file

**Fix:**
```bash
# Check file content
cat requirements.txt

# Provide non-empty prompt
squad auto -p "Your requirement here"
```

### "Must provide requirements via --prompt, --file, or --interactive"

**Cause:** No input method specified

**Fix:** Choose ONE input method:
```bash
squad auto -p "..."     # Inline
squad auto -f file.txt  # File
squad auto -i           # Interactive
```

### "Use only ONE input method"

**Cause:** Multiple flags used together

**Fix:** Use only one:
```bash
# WRONG
squad auto -p "..." -f file.txt

# CORRECT
squad auto -p "..."
```

---

## Migration from Traditional Flow

### If you're used to manual issues:

**Before:**
```bash
gh issue create --title "Feature" --body "Description"
squad pm 123
squad architect 123
```

**After:**
```bash
squad auto -p "Feature: Description" --auto-execute
```

### If you have existing requirements docs:

```bash
# Convert your docs to requirements.txt format
# Then run:
squad auto -f requirements.txt --auto-execute
```

---

## Advanced Usage

### Combining with Other Commands

```bash
# Create issues, then review before executing
squad auto -f requirements.txt
# Review issues in GitHub
gh issue list --label "ai-squad:auto"
# Manually run captain if satisfied
squad captain <epic-number>
```

### Custom Labels

Edit created issues to add project-specific labels:
```bash
gh issue edit <issue> --add-label "sprint-1"
gh issue edit <issue> --add-label "priority:high"
```

---

## Next Steps

- Try `squad auto -i` for interactive requirements gathering
- Use `--auto-execute` for full autonomous development
- Monitor progress with `squad dashboard`
- Review output issues in GitHub

**Welcome to true autonomous app development!** 🚀
