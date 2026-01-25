# Changelog

All notable changes to AI-Squad will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **🎖️ Squad Mission Mode**: New `squad auto` command with military-themed autonomous workflow!
  - Accept mission brief via `--prompt`, `--file`, or `--interactive`
  - PM validates mission as **EPIC** or **FEATURE**
  - Creates **Mission Brief** and **Mission Objectives** in GitHub
  - **🎖️ DEPLOYS TO CAPTAIN** for orchestration using Battle Plans
  - Captain coordinates agents via handoffs and Convoys
  - Maintains military theme: Captain, Battle Plans, Work Items, Convoys
  - Respects existing orchestration architecture
  - Optional `--plan-only` flag to create mission brief without Captain deployment
  - Examples:
    - `squad auto -p "Create REST API"` (full Captain deployment!)
    - `squad auto -f mission-brief.txt` (mission from file)
    - `squad auto -i` (interactive mission briefing)
    - `squad auto -p "..." --plan-only` (just create brief)

### Fixed
- **Import Issue**: Fixed incorrect import of GitHub Copilot SDK
  - Changed `from github_copilot_sdk import CopilotSDK` to `from copilot import CopilotSDK`
  - The PyPI package `github-copilot-sdk` provides the `copilot` module (not `github_copilot_sdk`)
  - Updated [agent_executor.py](ai_squad/core/agent_executor.py#L77) to use correct import
  - Updated [sdk_compat.py](ai_squad/core/sdk_compat.py#L58) compatibility check
  - This resolves installation errors where AI-Squad couldn't find the SDK module

- **Setup Experience**: Enhanced `squad init` with interactive GitHub configuration
  - Added automatic detection of GITHUB_TOKEN environment variable
  - Added detection of `gh` CLI authentication status
  - Provides clear instructions for both `gh auth login` (recommended) and manual token setup
  - Displays repo configuration status from squad.yaml
  - Shows platform-specific commands (Windows PowerShell vs Linux/Mac)
  - Added `--skip-setup` flag to skip interactive configuration
  - Improved "Next steps" guidance with dashboard command
  - Makes first-time setup more user-friendly and less error-prone

- **OAuth-Only Authentication**: Removed GITHUB_TOKEN support, OAuth is now the only authentication method
  - **BREAKING CHANGE**: GITHUB_TOKEN environment variable is no longer supported
  - Users must authenticate via `gh auth login` (GitHub CLI OAuth)
  - Simplified authentication: one method, one command to set up
  - More secure: no static tokens, automatic rotation, enterprise SSO/MFA support
  - CopilotSDK always uses OAuth (no token parameter)
  - Removed token checking and fallback logic
  - Updated all error messages to guide users to `gh auth login`
  - Interactive setup (`squad init`) only shows OAuth instructions
  - Documentation updated to remove all token references
  - If you were using GITHUB_TOKEN, run `gh auth login` to migrate

- **Packaging Issue**: Fixed missing files in package distribution
  - Added `MANIFEST.in` to properly include all necessary files
  - Created `ai_squad/agents_definitions/` with 5 agent definition files (pm, architect, engineer, ux, reviewer)
  - Copied `.github/copilot-instructions.md` to package as `ai_squad/copilot-instructions.md`
  - **Added `ai_squad/prompts/` directory** - 6 agent system prompt files (.md)
  - **Added `ai_squad/dashboard/templates/` files** - 7 HTML templates for web dashboard
  - **Added `ai_squad/dashboard/static/` files** - CSS and static assets
  - Updated `setup.py` to include all missing files in `package_data`:
    - `prompts/*.md` - Agent system prompts
    - `dashboard/templates/*.html` - Dashboard HTML files
    - `dashboard/static/**/*` - Dashboard CSS/JS/assets
    - `agents_definitions/*.md` - Agent definitions for GitHub Copilot
    - `copilot-instructions.md` - GitHub Copilot integration guide
  - Updated [init_project.py](ai_squad/core/init_project.py) to copy agent definitions and copilot instructions
  - After installation, `squad init` now properly creates:
    - `.github/agents/` with 5 agent definition files
    - `.github/skills/` with 18 skill files
    - `.github/templates/` with 7 template files
    - `.github/copilot-instructions.md` for GitHub Copilot integration

## [0.2.0] - 2026-01-22

### Added
- **Watch Mode**: `squad watch` command for automatic agent orchestration
  - Monitors GitHub for label changes (orch:* labels)
  - Automatically triggers agents in sequence: PM → Architect → Engineer → Reviewer
  - Real-time status display with statistics
  - Configurable polling interval (default: 30s)
  - Full test coverage (16 tests, 100% passing)
- New methods in `GitHubTool`:
  - `search_issues_by_labels()` - Search issues with include/exclude filters
  - `add_labels()` - Add labels to issues
- New module: `ai_squad/core/watch.py` - Watch daemon implementation
- Comprehensive test suite: `tests/test_watch.py`

### Changed
- Simplified orchestration flow: PM → Architect → Engineer → Reviewer
  - UX Designer is optional (run manually if needed)
  - Reduces unnecessary steps for technical workflows
- Updated documentation to reflect automatic orchestration

### Documentation
- Updated CLI help text for watch command
- Added usage examples in documentation

## [Unreleased]

## [0.4.0] - 2026-01-25
- Version bump to 0.4.0.

### Planned
- Interactive chat mode (`squad chat`)
- GitHub Actions workflow templates
- VSCode extension
- Web dashboard
- Custom model configuration

## [0.1.0] - 2026-01-22

### Added
- Initial release of AI-Squad
- Five AI agents: Product Manager, Architect, Engineer, UX Designer, Reviewer
- CLI commands: `init`, `pm`, `architect`, `engineer`, `ux`, `review`, `collab`, `doctor`, `update`
- Multi-agent collaboration support
- 18 production skills integrated
- Template-driven document generation (PRD, ADR, Spec, UX, Review)
- GitHub integration via GitHub CLI
- Configuration management via `squad.yaml`
- Comprehensive documentation
- Example projects
- Test suite with pytest

### Features
- **Product Manager Agent**
  - Creates comprehensive PRDs
  - Breaks down epics into features
  - Defines acceptance criteria

- **Architect Agent**
  - Writes Architecture Decision Records (ADRs)
  - Creates technical specifications
  - Designs system architecture

- **Engineer Agent**
  - Implements features with tests
  - Follows SOLID principles
  - Ensures ≥80% code coverage

- **UX Designer Agent**
  - Creates wireframes and user flows
  - Ensures WCAG 2.1 AA compliance
  - Designs responsive interfaces

- **Reviewer Agent**
  - Reviews code quality
  - Checks security vulnerabilities
  - Validates test coverage

### Documentation
- Quick start guide
- Commands reference
- Configuration guide
- Agents guide
- Workflows guide
- Contributing guide
- Example projects

### Testing
- Unit tests for all modules
- Integration tests for workflows
- CLI tests
- Test fixtures and mocks

## [0.0.1] - 2026-01-20

### Added
- Project inception
- Initial architecture design
- Proof of concept

---

**Legend:**
- `Added` - New features
- `Changed` - Changes to existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Security improvements
