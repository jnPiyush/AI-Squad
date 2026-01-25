# Basic AI-Squad Usage

This example shows basic AI-Squad usage in a new project.

## Setup

```bash
# Create project
mkdir my-app
cd my-app
git init

# Initialize AI-Squad
squad init

# Authenticate with GitHub (OAuth)
gh auth login
```

## Workflow

### 1. Create Issue

```bash
gh issue create --title "[Story] Add health check endpoint" --label "type:story"
# Issue #1 created
```

### 2. Run Product Manager

```bash
squad pm 1
```

**Output:** `docs/prd/PRD-1.md`

```markdown
# Product Requirements Document (PRD)

**Issue:** #1
**Title:** Add health check endpoint

## Executive Summary
Health check endpoint for monitoring service availability.

## User Stories
As an operations engineer
I want a health check endpoint
So that I can monitor service health

## Functional Requirements
- GET /health endpoint
- Returns 200 OK when healthy
- Returns service status (UP/DOWN)
- Checks database connectivity

## Technical Considerations
- Response time < 100ms
- No authentication required
- Logged for monitoring
```

### 3. Run Architect

```bash
squad architect 1
```

**Output:**
- `docs/adr/ADR-1.md`
- `docs/specs/SPEC-1.md`

```markdown
# Architecture Decision Record: Health Check Endpoint

## Decision
Implement standard REST health check endpoint at GET /health

## Alternatives Considered
1. Custom endpoint
2. External monitoring service
3. Built-in framework endpoint

## Chosen Solution
Use ASP.NET Core Health Checks with custom checks

## Implementation
- Add Microsoft.Extensions.Diagnostics.HealthChecks
- Configure in Program.cs
- Add database health check
- Return JSON response
```

### 4. Run Engineer

```bash
squad engineer 1
```

**Output:**
- Implementation code (or guide)
- Tests
- Documentation

**Generated Implementation:**

```csharp
// Program.cs
builder.Services.AddHealthChecks()
    .AddNpgSql(connectionString, name: "database");

app.MapHealthChecks("/health");
```

```csharp
// HealthCheckTests.cs
[Fact]
public async Task HealthEndpoint_Returns200_WhenHealthy()
{
    var response = await _client.GetAsync("/health");
    
    Assert.Equal(HttpStatusCode.OK, response.StatusCode);
}
```

### 5. Create PR

```bash
git add .
git commit -m "feat: add health check endpoint (#1)"
git push origin main
gh pr create --title "Add health check endpoint" --body "Closes #1"
```

### 6. Review PR

```bash
squad review 1
```

**Output:** `docs/reviews/REVIEW-1.md`

```markdown
# Code Review: Add health check endpoint

## Summary
✅ Approve

## Checklist
✅ Code quality: Follows SOLID principles
✅ Testing: 85% coverage
✅ Security: No issues
✅ Performance: Response time < 50ms
✅ Documentation: XML docs present

## Recommendation
Ready to merge
```

## Project Structure

After running all commands:

```
my-app/
├── squad.yaml
├── docs/
│   ├── prd/
│   │   └── PRD-1.md
│   ├── adr/
│   │   └── ADR-1.md
│   ├── specs/
│   │   └── SPEC-1.md
│   └── reviews/
│       └── REVIEW-1.md
├── src/
│   └── (implementation files)
└── tests/
    └── (test files)
```

## Key Points

1. **Always create issue first** - Agents work on existing issues
2. **Sequential workflow** - PM → Architect → Engineer → Reviewer
3. **Review outputs** - Check generated documents before implementation
4. **Customize as needed** - Edit generated files if needed
5. **Commit references** - Always reference issue in commit message

## Next Steps

- Try [multi-agent collaboration](../multi-agent-collab/)
- Learn about [GitHub Actions integration](../github-actions/)
- Explore [custom configuration](../custom-config/)
