# AI-Squad Skills Reference

> **Master Index**: Quick reference for all production development skills.  
> **Audience**: AI agents and developers.  
> **Standard**: Follows [agentskills.io](https://agentskills.io) specification.

---

## Quick Reference by Task

| Task Type | Load These Skills |
|-----------|-------------------|
| **API Implementation** | `#09 api-design`, `#04 database`, `#02 error-handling`, `#11 security` |
| **New Feature** | `#01 core-principles`, `#05 testing`, `#03 code-organization`, `#08 type-safety` |
| **Performance Issue** | `#10 performance`, `#04 database`, `#13 logging-monitoring` |
| **Security Audit** | `#11 security`, `#14 code-review-and-audit`, `#12 configuration` |
| **Database Work** | `#04 database`, `#19 postgresql`, `#20 sql-server` |
| **Frontend UI** | `#16 react`, `#17 frontend-ui`, `#18 blazor`, `#01 core-principles` |
| **Deployment** | `#12 configuration`, `#07 dependency-management`, `#13 logging-monitoring` |
| **Code Review** | `#14 code-review-and-audit`, `#05 testing`, `#11 security`, `#10 performance` |
| **AI Agent Development** | `#21 ai-agent-development`, `#01 core-principles`, `#02 error-handling` |

---

## Skills Index

### 🏗️ Architecture (7 skills)

| # | Skill | Purpose |
|---|-------|---------|
| 01 | [core-principles](.github/skills/architecture/core-principles/SKILL.md) | SOLID, DRY, KISS, design patterns |
| 02 | [error-handling](.github/skills/architecture/error-handling/SKILL.md) | Exception handling, retry logic, circuit breaker |
| 03 | [code-organization](.github/skills/architecture/code-organization/SKILL.md) | Project structure, clean architecture |
| 04 | [database](.github/skills/architecture/database/SKILL.md) | EF Core, migrations, indexing |
| 09 | [api-design](.github/skills/architecture/api-design/SKILL.md) | REST, versioning, pagination |
| 10 | [performance](.github/skills/architecture/performance/SKILL.md) | Async patterns, caching, optimization |
| 22 | [scalability](.github/skills/architecture/scalability/SKILL.md) | Horizontal scaling, load balancing |

### 💻 Development (13 skills)

| # | Skill | Purpose |
|---|-------|---------|
| 05 | [testing](.github/skills/development/testing/SKILL.md) | Test pyramid, xUnit, ≥80% coverage |
| 06 | [documentation](.github/skills/development/documentation/SKILL.md) | XML docs, README, OpenAPI |
| 07 | [dependency-management](.github/skills/development/dependency-management/SKILL.md) | NuGet, npm, pip security |
| 08 | [type-safety](.github/skills/development/type-safety/SKILL.md) | Nullable refs, static analysis |
| 12 | [configuration](.github/skills/development/configuration/SKILL.md) | Environment vars, Key Vault, feature flags |
| 13 | [logging-monitoring](.github/skills/development/logging-monitoring/SKILL.md) | Serilog, OpenTelemetry, metrics |
| 14 | [code-review-and-audit](.github/skills/development/code-review-and-audit/SKILL.md) | Review checklists, security audits |
| 15 | [python](.github/skills/development/python/SKILL.md) | Python development best practices |
| 23 | [csharp](.github/skills/development/csharp/SKILL.md) | C# development best practices |
| 16 | [react](.github/skills/development/react/SKILL.md) | React hooks, state, performance |
| 17 | [frontend-ui](.github/skills/development/frontend-ui/SKILL.md) | CSS, accessibility, responsive design |
| 18 | [blazor](.github/skills/development/blazor/SKILL.md) | Blazor components, JS interop |
| 19 | [postgresql](.github/skills/development/postgresql/SKILL.md) | PostgreSQL JSONB, full-text search |
| 20 | [sql-server](.github/skills/development/sql-server/SKILL.md) | SQL Server T-SQL, JSON, MERGE |

### ⚙️ Operations (3 skills)

| # | Skill | Purpose |
|---|-------|---------|
| 11 | [security](.github/skills/operations/security/SKILL.md) | OWASP, input validation, secrets |
| 24 | [version-control](.github/skills/operations/version-control/SKILL.md) | Git workflows, commit conventions |
| 25 | [remote-git-operations](.github/skills/operations/remote-git-operations/SKILL.md) | GitHub, PRs, CI/CD |

### 🤖 AI Systems (1 skill)

| # | Skill | Purpose |
|---|-------|---------|
| 21 | [ai-agent-development](.github/skills/ai-systems/ai-agent-development/SKILL.md) | Agent architecture, evaluation, tracing |

---

## Critical Production Rules

### 🔴 ALWAYS

1. **Test coverage ≥80%** - Never ship untested code
2. **Input validation** - Validate ALL external input
3. **Error handling** - Never swallow exceptions silently
4. **Logging** - Log all errors with context
5. **Security scan** - Check for secrets and vulnerabilities
6. **Code review** - All changes require review

### 🟡 PREFER

1. **Async/await** - For I/O-bound operations
2. **Strong typing** - Avoid `dynamic` and `object`
3. **Dependency injection** - For testability
4. **Configuration** - Environment variables over hardcoded values
5. **Immutability** - Prefer `readonly` and `init`

### 🔵 AVOID

1. **Magic strings** - Use constants or enums
2. **God classes** - Keep classes focused (SRP)
3. **Deep nesting** - Early returns, guard clauses
4. **Premature optimization** - Profile first
5. **Comments explaining "what"** - Code should be self-documenting

---

## Agent Skill Mapping

| Agent | Primary Skills |
|-------|---------------|
| **PM** | `#01 core-principles`, `#06 documentation` |
| **Architect** | `#09 api-design`, `#04 database`, `#22 scalability`, `#11 security` |
| **Engineer** | `#05 testing`, `#02 error-handling`, `#03 code-organization`, `#08 type-safety` |
| **UX Designer** | `#06 documentation`, `#17 frontend-ui`, `#01 core-principles` |
| **Reviewer** | `#14 code-review-and-audit`, `#11 security`, `#10 performance`, `#05 testing` |

---

## Language-Specific Skills

### Backend Languages

| Language | Skills |
|----------|--------|
| **C#/.NET** | `#23 csharp`, `#04 database`, `#09 api-design` |
| **Python** | `#15 python`, `#21 ai-agent-development` |

### Frontend Frameworks

| Framework | Skills |
|-----------|--------|
| **React** | `#16 react`, `#17 frontend-ui` |
| **Blazor** | `#18 blazor`, `#23 csharp` |

### Databases

| Database | Skills |
|----------|--------|
| **PostgreSQL** | `#19 postgresql`, `#04 database` |
| **SQL Server** | `#20 sql-server`, `#04 database` |

---

## Skill Versioning

| Skill | Version | Last Updated |
|-------|---------|--------------|
| core-principles | 1.0 | Jan 2025 |
| testing | 1.0 | Jan 2025 |
| api-design | 1.0 | Jan 2025 |
| python | 1.0 | Jan 2025 |
| csharp | 1.0 | Jan 2025 |
| react | 1.0 | Jan 2025 |
| blazor | 1.0 | Jan 2025 |
| postgresql | 1.0 | Jan 2025 |
| sql-server | 1.0 | Jan 2025 |

---

## Adding New Skills

1. Create folder: `.github/skills/<category>/<skill-name>/`
2. Create `SKILL.md` with frontmatter:
   ```yaml
   ---
   name: skill-name
   description: 'Brief description'
   ---
   ```
3. Include: Quick Reference table, Version, Examples with ✅/❌, Best Practices
4. Update this index file
5. Update `.github/copilot-instructions.md` if needed

---

## See Also

- **[AGENTS.md](AGENTS.md)** - Agent roles and capabilities
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - How to contribute
- **[copilot-instructions.md](.github/copilot-instructions.md)** - Copilot integration

---

**Total Skills**: 25  
**Last Updated**: January 27, 2026
