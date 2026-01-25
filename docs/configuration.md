# Configuration Guide

Customize AI-Squad for your project.

## Configuration File

AI-Squad uses `squad.yaml` in your project root.

**Create with:**
```bash
squad init
```

## Default Configuration

```yaml
project:
  name: My Project
  github_repo: null
  github_owner: null

agents:
  pm:
    enabled: true
    model: claude-sonnet-4.5
  architect:
    enabled: true
    model: claude-sonnet-4.5
  engineer:
    enabled: true
    model: claude-sonnet-4.5
  ux:
    enabled: true
    model: claude-sonnet-4.5
  reviewer:
    enabled: true
    model: claude-sonnet-4.5

output:
  prd_dir: docs/prd
  adr_dir: docs/adr
  specs_dir: docs/specs
  architecture_dir: docs/architecture
  ux_dir: docs/ux
  reviews_dir: docs/reviews

github:
  auto_create_issues: true
  auto_create_prs: false
  labels:
    epic: type:epic
    feature: type:feature
    story: type:story
    bug: type:bug

skills:
  - all

runtime:
  provider: copilot
  provider_order: [copilot, openai, azure_openai]
  command: null
  args: []
  prompt_mode: none
  base_dir: .squad

hooks:
  enabled: true
  use_git_worktree: false
  hooks_dir: .squad/hooks
```

## Configuration Options

### Project Settings

#### `project.name`

**Type:** String  
**Default:** Current directory name  
**Description:** Project name for documentation

```yaml
project:
  name: My Awesome Project
```

#### `project.github_repo`

**Type:** String  
**Default:** Auto-detected from git remote  
**Description:** GitHub repository name

```yaml
project:
  github_repo: my-repo
```

#### `project.github_owner`

**Type:** String  
**Default:** Auto-detected from git remote  
**Description:** GitHub username or organization

```yaml
project:
  github_owner: myusername
```

### Agent Settings

Configure each agent individually.

#### Agent Properties

- **`enabled`** - Enable/disable agent (boolean)
- **`model`** - AI model to use (string)

**Available Models:**
- `gpt-4` - Most capable (recommended)
- `gpt-3.5-turbo` - Faster, less expensive
- `claude-3-sonnet` - Alternative (if supported)

**Example:**

```yaml
agents:
  pm:
    enabled: true
    model: claude-sonnet-4.5
  
  architect:
    enabled: true
    model: claude-sonnet-4.5
  
  engineer:
    enabled: true
    model: gpt-3.5-turbo  # Faster for implementation
  
  ux:
    enabled: false  # Disable if no UI work
    model: claude-sonnet-4.5
  
  reviewer:
    enabled: true
    model: claude-sonnet-4.5
```

### Output Directories

Customize where agents save their outputs.

```yaml
output:
  prd_dir: docs/requirements  # PRDs
  adr_dir: architecture/decisions  # ADRs
  specs_dir: architecture/specs  # Specs
  architecture_dir: architecture/overview  # Architecture docs
  ux_dir: design/ux  # UX designs
  reviews_dir: reviews  # Code reviews
```

### Quality Settings

```yaml
quality:
  test_coverage_threshold: 80
  test_pyramid:
    unit: 70
    integration: 20
    e2e: 10
```

### Routing Settings

```yaml
routing:
  enforce_cli_routing: false
  trust_level: high
  data_sensitivity: internal
  max_data_sensitivity: restricted
  min_events: 5
```

### Accessibility Settings

```yaml
accessibility:
  wcag_version: "2.1"
  wcag_level: "AA"
  contrast_ratio: 4.5
```

**Relative Paths:** All paths are relative to project root.

### GitHub Integration

#### `github.auto_create_issues`

**Type:** Boolean  
**Default:** `true`  
**Description:** Automatically create feature issues from epics

```yaml
github:
  auto_create_issues: true
```

#### `github.auto_create_prs`

**Type:** Boolean  
**Default:** `false`  
**Description:** Automatically create PRs (experimental)

```yaml
github:
  auto_create_prs: false
```

#### `github.labels`

**Type:** Object  
**Description:** Label mappings for issue types

```yaml
github:
  labels:
    epic: type:epic
    feature: type:feature
    story: type:story
    bug: type:bug
    spike: type:spike
    docs: type:docs
```

### Skills Configuration

Control which production skills agents use.

#### Load All Skills

```yaml
skills:
  - all
```

#### Load Specific Skills

```yaml
skills:
  - testing
  - security
  - performance
  - api-design
  - documentation
```

**Available Skills:**
1. `core-principles` - SOLID, DRY, KISS
2. `testing` - Test strategies
3. `error-handling` - Exception patterns
4. `security` - OWASP, input validation
5. `performance` - Async, caching
6. `database` - Migrations, indexing
7. `scalability` - Load balancing, queues
8. `code-organization` - Project structure
9. `api-design` - REST, versioning
10. `configuration` - Env vars, secrets
11. `documentation` - XML docs, README
12. `version-control` - Git workflow
13. `type-safety` - Nullable types
14. `dependency-management` - Lock files
15. `logging-monitoring` - Structured logging
16. `remote-git-operations` - PRs, CI/CD
17. `ai-agent-development` - Agent patterns
18. `code-review-and-audit` - Review checklists

### Runtime Configuration

Control the AI provider order and runtime settings.

```yaml
runtime:
  provider: copilot
  provider_order: [copilot, openai, azure_openai]
  command: null
  args: []
  prompt_mode: none
```

### Hook Persistence

Enable hook persistence for Work Items.

```yaml
hooks:
  enabled: true
  use_git_worktree: false
  hooks_dir: .squad/hooks
```

## Environment-Specific Configuration

### Development

```yaml
project:
  name: My Project (Dev)

agents:
  engineer:
    model: gpt-3.5-turbo  # Faster for dev

output:
  prd_dir: docs/dev/prd
```

### Production

```yaml
project:
  name: My Project

agents:
  pm:
    model: claude-sonnet-4.5
  architect:
    model: claude-sonnet-4.5
  engineer:
    model: claude-sonnet-4.5  # Best quality
  reviewer:
    model: claude-sonnet-4.5

skills:
  - all  # All production skills
```

## Advanced Configuration

### Multiple Configurations

Use different configs for different projects:

```bash
# Project A
export SQUAD_CONFIG=./squad-projectA.yaml
squad pm 123

# Project B
export SQUAD_CONFIG=./squad-projectB.yaml
squad pm 456
```

### Template Customization

Override default templates:

1. Copy templates from `.github/templates/`
2. Modify as needed
3. AI-Squad uses your custom templates

**Example:**

```bash
# Copy template
cp .github/templates/prd.md .github/templates/prd-custom.md

# Edit template
nano .github/templates/prd-custom.md

# Use custom template (automatic if file exists)
```

### Skill Customization

Add your own skills:

1. Create `ai_squad/skills/custom-skill/SKILL.md`
2. Add to config:

```yaml
skills:
  - testing
  - security
  - custom-skill  # Your custom skill
```

## Configuration Validation

Check if configuration is valid:

```bash
squad doctor
```

**Validates:**
- ✅ File exists
- ✅ Valid YAML syntax
- ✅ Required fields present
- ✅ GitHub connection works
- ✅ Output directories exist

## Example Configurations

### Minimal (Small Project)

```yaml
project:
  name: Small App
  github_repo: small-app
  github_owner: myusername

agents:
  engineer:
    enabled: true
    model: gpt-3.5-turbo
  reviewer:
    enabled: true
    model: gpt-3.5-turbo

output:
  prd_dir: docs
  reviews_dir: docs/reviews

skills:
  - testing
  - security
```

### Full-Featured (Enterprise)

```yaml
project:
  name: Enterprise Platform
  github_repo: platform
  github_owner: myorg

agents:
  pm:
    enabled: true
    model: claude-sonnet-4.5
  architect:
    enabled: true
    model: claude-sonnet-4.5
  engineer:
    enabled: true
    model: claude-sonnet-4.5
  ux:
    enabled: true
    model: claude-sonnet-4.5
  reviewer:
    enabled: true
    model: claude-sonnet-4.5

output:
  prd_dir: docs/requirements/prd
  adr_dir: docs/architecture/adr
  specs_dir: docs/architecture/specs
  ux_dir: docs/design/ux
  reviews_dir: docs/quality/reviews

github:
  auto_create_issues: true
  auto_create_prs: false
  labels:
    epic: type:epic,priority:p1
    feature: type:feature
    story: type:story
    bug: type:bug

skills:
  - all
```

### Open Source Project

```yaml
project:
  name: Open Source Library
  github_repo: awesome-lib
  github_owner: opensource-org

agents:
  pm:
    enabled: true
    model: claude-sonnet-4.5
  architect:
    enabled: true
    model: claude-sonnet-4.5
  engineer:
    enabled: true
    model: claude-sonnet-4.5
  reviewer:
    enabled: true
    model: claude-sonnet-4.5
  ux:
    enabled: false  # No UI

output:
  prd_dir: docs/prd
  adr_dir: docs/adr
  specs_dir: docs/specs
  reviews_dir: .github/reviews

github:
  auto_create_issues: true
  labels:
    feature: enhancement
    bug: bug
    docs: documentation

skills:
  - core-principles
  - testing
  - security
  - performance
  - documentation
  - version-control
```

## Tips

1. **Start with defaults** - Modify as needed
2. **Use `squad doctor`** - Validate config
3. **Commit `squad.yaml`** - Share with team
4. **Different configs per environment** - Use `SQUAD_CONFIG` env var
5. **Document customizations** - Add comments in YAML

## Next Steps

- [Agents Guide](agents.md) - Learn about each agent
- [Workflows](workflows.md) - Multi-agent patterns
- [GitHub Actions](github-actions.md) - CI/CD integration

---

**Need help?** [Open an issue](https://github.com/jnPiyush/AI-Squad/issues)
