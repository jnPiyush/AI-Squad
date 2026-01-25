# AI-Squad Agents

This guide provides detailed information about each of the five specialized AI agents in AI-Squad.

## Overview

AI-Squad includes five expert agents that work together to deliver complete features:

| Agent | Role | Primary Output | When to Use |
|-------|------|----------------|-------------|
| 🎨 **Product Manager** | Requirements & Planning | PRD Documents | New features, epics, requirements gathering |
| 🧩 **Architect** | Technical Design | ADRs & Specifications | Architecture decisions, technical design |
| 🔧 **Engineer** | Implementation | Code & Tests | Feature implementation, bug fixes |
| 🎭 **UX Designer** | User Experience | Wireframes & Flows | HTML prototypes, wireframes, user flows | UI features, user-facing designs |
| 🛡️ **Reviewer** | Quality Assurance | Review Reports | Code review, quality checks |

---

## 🎖️ Squad Mission Mode

**The fastest way to build features** - Provide requirements and let Squad handle EVERYTHING!

### Quick Start

```bash
# Provide mission brief - Captain orchestrates the entire team!
squad mission -p "Create a REST API for task management with CRUD operations"
```

### What Happens:

1. **📋 PM Validates Mission**
   - Analyzes requirements
   - Classifies as EPIC or FEATURE
   - Extracts objectives

2. **📝 GitHub Issues Created**
   - Mission Brief issue (#123)
   - Mission Objective issues (#124, #125, #126)

3. **🎖️ Captain Takes Command**
   - Analyzes mission complexity
   - Selects Battle Plan (feature/epic workflow)
   - Creates operations for tracking
   - Organizes into Convoys (parallel execution)

4. **🤝 Multi-Agent Collaboration Executes**
   - **PM**: Creates comprehensive PRD
   - **Architect**: Designs solution with ADR and specs
   - **Engineer**: Implements with comprehensive tests (≥80% coverage)
   - **UX**: Creates wireframes and prototypes (if UI)
   - **Reviewer**: Reviews code and creates PR

5. **✅ Complete Feature Delivered!**

### Example Mission

```bash
squad auto -p "
Create an Idea Management System with:
- User authentication and authorization
- CRUD operations for ideas
- Voting and commenting system
- Search and filtering
- Real-time notifications
"
```

**Result:**
- Mission Brief (Epic) created in GitHub
- 5 Mission Objectives (stories) created
- Captain coordinates all agents
- Complete implementation with tests
- Pull request ready for review
- All in one command! 🚀

---

## 🎨 Product Manager Agent

### Role

The Product Manager agent analyzes business requirements and creates comprehensive Product Requirements Documents (PRDs). It breaks down large epics into manageable features and user stories.

### Capabilities

- **Requirements Analysis** - Understands user needs and business goals
- **Epic Breakdown** - Decomposes large initiatives into features and stories
- **Acceptance Criteria** - Defines clear success criteria for requirements
- **Prioritization** - Recommends feature priority based on business value
- **User Story Mapping** - Creates structured user stories with context
- **Self-Review & Quality Assurance** - Reviews own PRD outputs for completeness, clarity, and alignment with business goals

### What It Produces

1. **PRD Document** - `docs/prd/PRD-{issue}.md`
   - Executive Summary
   - Problem Statement
   - Goals & Success Metrics
   - User Stories
   - Functional Requirements
   - Non-Functional Requirements
   - Dependencies & Risks

2. **GitHub Issues** (for epics)
   - Feature breakdown
   - User stories with acceptance criteria
   - Labeled and prioritized

### Command

```bash
squad pm <issue-number>
```

### Example

```bash
squad pm 123
```

### When to Use

- ✅ Starting new features
- ✅ Planning large epics
- ✅ Requirements gathering phase
- ✅ Clarifying ambiguous requests
- ✅ Before technical design begins

### Configuration

```yaml
agents:
  pm:
    model: "claude-sonnet-4.5"
    temperature: 0.7
    skills:
      - core-principles
      - documentation
```

---

## 🧩 Architect Agent

### Role

The Architect agent designs scalable, maintainable solutions and documents technical decisions through Architecture Decision Records (ADRs) and detailed specifications.

### Capabilities

- **Solution Design** - Creates scalable, maintainable architectures
- **Technology Evaluation** - Assesses and recommends technology choices
- **ADR Creation** - Documents architectural decisions with context
- **API Design** - Defines contracts, endpoints, and data models
- **Diagram Generation** - Creates architecture diagrams (Mermaid format)
- **Pattern Application** - Applies appropriate design patterns
- **Self-Review & Quality Assurance** - Reviews own ADRs and specifications for technical soundness, scalability considerations, and completeness

### What It Produces

1. **ADR Document** - `docs/adr/ADR-{issue}.md`
   - Title & Status
   - Context & Problem
   - Decision & Rationale
   - Consequences
   - Alternatives Considered

2. **Technical Specification** - `docs/specs/SPEC-{issue}.md`
   - System Overview
   - Architecture Diagrams
   - Component Design
   - API Contracts
   - Data Models
   - Security Considerations
   - Performance Requirements

### Command

```bash
squad architect <issue-number>
```

### Example

```bash
squad architect 456
```

### When to Use

- ✅ After PRD is complete
- ✅ Technical design phase
- ✅ Major architectural changes
- ✅ Technology selection decisions
- ✅ API contract definition
- ✅ System integration planning

### Configuration

```yaml
agents:
  architect:
    model: "claude-sonnet-4.5"
    temperature: 0.5
    skills:
      - api-design
      - database
      - scalability
      - security
```

---

## � Engineer Agent

### Role

The Engineer agent implements features following specifications, writes comprehensive tests, and ensures code quality through best practices.

### Capabilities

- **Feature Implementation** - Writes clean, maintainable code
- **Test-Driven Development** - Creates comprehensive test suites
- **Code Documentation** - Adds XML docs/docstrings
- **Design Patterns** - Applies SOLID principles
- **Test Coverage** - Ensures ≥80% coverage
- **Best Practices** - Follows language-specific conventions
- **Self-Review & Quality Assurance** - Reviews own code for SOLID principles, test coverage, security vulnerabilities, and documentation completeness before submission

### What It Produces

1. **Implementation Code**
   - Feature code in appropriate locations
   - Proper project structure
   - Following existing patterns

2. **Test Suite**
   - Unit tests (70% of suite)
   - Integration tests (20% of suite)
   - E2E tests (10% of suite)
   - ≥80% code coverage

3. **Documentation**
   - Code comments
   - XML docs/docstrings
   - Updated README sections
   - API documentation

4. **Pull Request**
   - Detailed description
   - Screenshots/demos (if UI)
   - Testing instructions
   - Links to related issues

### Command

```bash
squad engineer <issue-number>
```

### Example

```bash
squad engineer 789
```

### When to Use

- ✅ After technical spec is ready
- ✅ Feature implementation
- ✅ Bug fixes
- ✅ Refactoring tasks
- ✅ Performance optimization
- ✅ Technical debt resolution

### Code Quality Standards

- **SOLID Principles** - Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
- **DRY** - Don't Repeat Yourself
- **Clean Code** - Clear naming, small functions, minimal complexity
- **Error Handling** - Proper exception handling and logging
- **Performance** - Optimized algorithms and resource usage

### Configuration

```yaml
agents:
  engineer:
    model: "claude-sonnet-4.5"
    temperature: 0.3
    skills:
      - testing
      - error-handling
      - code-organization
      - type-safety
    coverage_threshold: 80
```

---

## 🎭 UX Designer Agent

### Role

The UX Designer agent creates user-centered designs, wireframes, and ensures accessibility standards are met across all user interfaces.

### Capabilities

- **User Flow Design** - Maps user journeys and interactions
- **Wireframe Creation** - Designs screens and components
- **Accessibility** - Ensures WCAG 2.1 AA compliance
- **Responsive Design** - Plans mobile-first, responsive layouts
- **Interaction Design** - Defines UI behaviors and animations
- **Design Systems** - Applies consistent patterns
- **Self-Review & Quality Assurance** - Reviews own designs for WCAG 2.1 AA compliance, user flow clarity, responsive design completeness, and consistency with design patterns

### What It Produces

1. **UX Design Document** - `docs/ux/UX-{issue}.md`
   - User Flows (Mermaid diagrams)
   - Wireframes (ASCII art or diagrams)
   - Component Specifications
   - Interaction Patterns
   - Accessibility Checklist
   - Responsive Breakpoints

2. **Professional HTML Click-through Prototype** - `docs/ux/prototypes/prototype-{issue}.html`
   - Self-contained, single-file HTML
   - Realistic styling with inline CSS
   - Interactive navigation between screens
   - Responsive design implementation
   - Accessibility features built-in
   - Ready to test in browser

3. **Design Assets**
   - Flow diagrams
   - Screen layouts
   - Component documentation
   - Color/typography guidelines

### Command

```bash
squad ux <issue-number>
```

### Example

```bash
squad ux 101
```

### When to Use

- ✅ UI/Frontend features
- ✅ After PRD is complete
- ✅ Before implementation starts
- ✅ User experience improvements
- ✅ Accessibility audits
- ✅ Design system updates

### Design Principles

- **User-Centered** - Focus on user needs and goals
- **Accessibility First** - WCAG 2.1 AA compliance minimum
- **Mobile-First** - Design for smallest screens first
- **Consistency** - Follow established design patterns
- **Performance** - Optimize for fast load times
- **Inclusivity** - Design for diverse users

### Configuration

```yaml
agents:
  ux:
    model: "claude-sonnet-4.5"
    temperature: 0.6
    skills:
      - documentation
      - core-principles
    accessibility_standard: "WCAG 2.1 AA"
```

---

## 🛡️ Reviewer Agent

### Role

The Reviewer agent performs comprehensive code reviews, checking for quality, security, performance, and standards compliance.

### Capabilities

- **Code Quality Review** - Checks SOLID principles, clean code
- **Security Analysis** - Identifies vulnerabilities and risks
- **Test Coverage Review** - Verifies ≥80% coverage
- **Performance Assessment** - Evaluates efficiency and scalability
- **Documentation Check** - Ensures completeness
- **Standards Compliance** - Validates coding standards
- **Self-Review & Quality Assurance** - Reviews own review reports for thoroughness, actionable feedback, balanced critique, and constructive recommendations

### What It Produces

1. **Review Document** - `docs/reviews/REVIEW-{pr}.md`
   - Executive Summary
   - Code Quality Assessment
   - Security Analysis
   - Test Coverage Report
   - Performance Review
   - Documentation Check
   - Recommendations
   - Approval Status

### Command

```bash
squad review <pr-number>
```

### Example

```bash
squad review 202
```

### When to Use

- ✅ Before merging pull requests
- ✅ After Engineer completes feature
- ✅ Security audits
- ✅ Code quality checks
- ✅ Pre-release reviews
- ✅ Technical debt assessment

### Review Checklist

#### Code Quality
- [ ] Follows SOLID principles
- [ ] DRY - no code duplication
- [ ] Clear naming conventions
- [ ] Proper error handling
- [ ] No compiler warnings
- [ ] Linter rules followed

#### Testing
- [ ] Test coverage ≥80%
- [ ] Unit tests present and passing
- [ ] Integration tests included
- [ ] Edge cases covered
- [ ] Mocks used appropriately

#### Security
- [ ] No hardcoded credentials
- [ ] Input validation present
- [ ] SQL injection prevention
- [ ] XSS protection (if applicable)
- [ ] Authentication/authorization correct
- [ ] Dependencies up to date

#### Performance
- [ ] Efficient algorithms used
- [ ] No N+1 queries
- [ ] Proper indexing (database)
- [ ] Resource cleanup
- [ ] Memory leaks checked

#### Documentation
- [ ] Code comments present
- [ ] XML docs/docstrings complete
- [ ] README updated
- [ ] API docs updated
- [ ] Breaking changes noted

### Configuration

```yaml
agents:
  reviewer:
    model: "claude-sonnet-4.5"
    temperature: 0.4
    skills:
      - code-review-and-audit
      - security
      - performance
      - testing
    coverage_threshold: 80
    strict_mode: true
```

---

## Multi-Agent Workflows

Agents can work together in coordinated sequences:

### Standard Feature Workflow

```bash
# 1. Requirements
squad pm 123

# 2. Design
squad architect 123

# 3. UX (if UI)
squad ux 123

# 4. Implementation
squad engineer 123

# 5. Review
squad review <pr-number>
```

### Quick Collaboration

```bash
# Run multiple agents in sequence
squad joint-op 123 pm architect engineer

# Or use automatic watch mode
squad patrol
```

See [Workflows](workflows.md) for more multi-agent patterns.

---

## Agent Skills

All agents have access to specialized skills from the `ai_squad/skills/` directory:

### Available Skills (18 total)

| Skill | Directory | Used By |
|-------|-----------|---------|
| `ai-agent-development` | AI/ML patterns | All |
| `api-design` | REST/GraphQL design | Architect |
| `code-organization` | Project structure | Engineer |
| `code-review-and-audit` | Review checklists | Reviewer |
| `configuration` | Config management | All |
| `core-principles` | SOLID, DRY, KISS | All |
| `database` | Database design | Architect |
| `dependency-management` | Package management | Engineer |
| `documentation` | Doc standards | PM, UX |
| `error-handling` | Error patterns | Engineer |
| `logging-monitoring` | Observability | Engineer |
| `performance` | Optimization | Reviewer, Architect |
| `remote-git-operations` | Git workflows | All |
| `scalability` | Scaling patterns | Architect |
| `security` | Security practices | Architect, Reviewer |
| `testing` | Testing strategies | Engineer, Reviewer |
| `type-safety` | Type systems | Engineer |
| `version-control` | Git best practices | All |

### Agent-Specific Skills
- **PM**: `core-principles`, `documentation`
- **Architect**: `api-design`, `database`, `scalability`, `security`
- **Engineer**: `testing`, `error-handling`, `code-organization`, `type-safety`
- **UX**: `documentation`, `core-principles`
- **Reviewer**: `code-review-and-audit`, `security`, `performance`, `testing`

---

## Configuration

### Global Agent Configuration

Edit `squad.yaml`:

```yaml
agents:
  # Default model for all agents
  default_model: "claude-sonnet-4.5"
  default_temperature: 0.5
  
  # Per-agent overrides
  pm:
    model: "claude-sonnet-4.5"
    temperature: 0.7
    
  architect:
    model: "claude-sonnet-4.5"
    temperature: 0.5
    
  engineer:
    model: "claude-sonnet-4.5"
    temperature: 0.3
    coverage_threshold: 80
    
  ux:
    model: "claude-sonnet-4.5"
    temperature: 0.6
    accessibility_standard: "WCAG 2.1 AA"
    
  reviewer:
    model: "claude-sonnet-4.5"
    temperature: 0.4
    coverage_threshold: 80
    strict_mode: true
```

### Environment Variables

```bash
# GitHub token (required)
export GITHUB_TOKEN="ghp_your_token"

# Optional: Custom model
export AI_SQUAD_MODEL="claude-sonnet-4.5"

# Optional: Temperature override
export AI_SQUAD_TEMPERATURE="0.5"
```

---

## Tips & Best Practices

### For Product Manager
- Provide clear, detailed issue descriptions
- Include user personas and use cases
- Specify business goals and metrics
- Use labels for better categorization
- **Self-Review**: Verify PRD has clear acceptance criteria, measurable success metrics, and addresses all business requirements before submission

### For Architect
- Review existing codebase patterns first
- Consider scalability and maintainability
- Document decisions with clear rationale
- Include diagrams for complex systems
- **Self-Review**: Ensure ADR includes all alternatives considered, consequences are documented, and technical decisions align with existing architecture patterns

### For Engineer
- Follow the technical specification
- Write tests before implementation (TDD)
- Commit frequently with clear messages
- Update documentation as you go
- **Self-Review**: Run all tests locally, check code coverage ≥80%, verify SOLID principles, scan for security issues, and ensure documentation is complete before creating PR

### For UX Designer
- Reference existing design systems
- Consider accessibility from the start
- Test designs with real users when possible
- Document interaction patterns clearly
- **Self-Review**: Validate WCAG 2.1 AA compliance using accessibility checklist, test responsive breakpoints, ensure color contrast ratios meet standards, and verify navigation flows are intuitive

### For Reviewer
- Review with constructive feedback
- Suggest improvements, don't just criticize
- Consider context and constraints
- Approve when quality standards are met
- **Self-Review**: Ensure review covers all checklist items (code quality, testing, security, performance, documentation), feedback is actionable and specific, and approval decision is justified

---

## Troubleshooting

### Agent Not Producing Expected Output

1. Check issue description is clear and detailed
2. Verify prerequisite documents exist (PRD, spec, etc.)
3. Review agent logs for errors
4. Try increasing temperature for more creative output

### Agent Missing Context

1. Ensure previous agent outputs are committed
2. Check `squad.yaml` skills configuration
3. Verify GitHub token has repository access
4. Run `squad sitrep` to diagnose issues

### Low Quality Output

1. Adjust temperature in configuration
2. Provide more detailed requirements
3. Use more specific issue labels
4. Review and refine agent skills

---

## Next Steps

- **[Commands Reference](commands.md)** - All available commands
- **[Workflows](workflows.md)** - Multi-agent collaboration patterns
- **[Configuration](configuration.md)** - Customize AI-Squad
- **[Troubleshooting](troubleshooting.md)** - Common issues and solutions

---

**Need Help?**

- 📖 [Documentation](README.md)
- 🐛 [Report Issues](https://github.com/your-org/ai-squad/issues)
- 💬 [Discussions](https://github.com/your-org/ai-squad/discussions)

