# Changelog

All notable changes to AI-Squad will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
