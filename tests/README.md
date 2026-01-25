# AI-Squad Test Suite

Run tests with pytest.

## Running Tests

### All Tests
```bash
pytest
```

### With Coverage
```bash
pytest --cov=ai_squad --cov-report=html
```

### Specific Test File
```bash
pytest tests/test_cli.py
```

### Specific Test
```bash
pytest tests/test_cli.py::TestCLI::test_version
```

### Verbose Output
```bash
pytest -v
```

## Test Structure

```
tests/
├── conftest.py          # Shared fixtures
├── test_cli.py          # CLI tests
├── test_agents.py       # Agent tests
├── test_core.py         # Core module tests
└── test_tools.py        # Tools tests
```

## Fixtures

### `temp_project_dir`
Creates a temporary project directory for tests.

### `mock_github_token`
Mocks the GITHUB_TOKEN environment variable.

### `mock_config`
Provides a mock AI-Squad configuration.

### `mock_issue`
Provides a mock GitHub issue.

### `mock_pr`
Provides a mock GitHub pull request.

## Writing Tests

### Test Class Structure
```python
class TestMyFeature:
    """Test my feature"""
    
    @pytest.fixture
    def setup(self):
        """Setup for tests"""
        yield
    
    def test_basic_case(self, setup):
        """Test basic functionality"""
        assert True
```

### Using Mocks
```python
from unittest.mock import Mock, patch

@patch("module.function")
def test_with_mock(mock_func):
    mock_func.return_value = "mocked"
    result = function_under_test()
    assert result == "expected"
```

## Test Coverage

Current coverage: ~60% (target: ≥80%)

Run coverage report:
```bash
pytest --cov=ai_squad --cov-report=term-missing
```

View HTML report:
```bash
pytest --cov=ai_squad --cov-report=html
open htmlcov/index.html
```

## CI/CD

Tests run automatically on:
- Pull requests
- Pushes to main
- Releases

See `.github/workflows/test.yml` for CI configuration.

## Troubleshooting

### Tests Fail Due to Missing Dependencies
```bash
pip install -e ".[dev]"
```

### Tests Fail Due to GitHub Token
Set mock token:
```bash
export GITHUB_TOKEN=ghp_mock_token
```

### Tests Fail Due to SDK
Install SDK:
```bash
pip install github-copilot-sdk>=0.1.16
```

## Contributing

When adding features:
1. Write tests first (TDD)
2. Ensure tests pass
3. Maintain ≥80% coverage
4. Update documentation

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details.


# End-to-End Live Testing

## e2e-live-test.ps1

**Purpose**: Complete production simulation with customizable test application  
**Coverage**: All 35 tests including full autonomous lifecycle validation  
**Key Feature**: Tests both individual commands AND complete end-to-end orchestration

### What Makes This Different

This E2E test validates **two critical dimensions**:

1. **Component Testing (Tests 1-34)**: Individual CLI commands work correctly
2. **🎯 Autonomous Lifecycle (Test 35)**: The REAL value proposition - create a feature request and let AI-Squad orchestrate everything from PM → Architect → UX → Engineer autonomously

### Usage

```powershell
# Run with default test app (Idea Management System)
.\tests\e2e-live-test.ps1

# Run with custom test application requirements
.\tests\e2e-live-test.ps1 -TestAppRequirement "Build an e-commerce platform with shopping cart, payment processing, and order tracking..."

# With verbose output
.\tests\e2e-live-test.ps1 -Verbose

# Skip cleanup (keep generated artifacts)
.\tests\e2e-live-test.ps1 -SkipCleanup

# Custom repository
.\tests\e2e-live-test.ps1 -Repo "your-org/your-repo"

# Combined options
.\tests\e2e-live-test.ps1 -TestAppRequirement "Your custom requirements" -Verbose -SkipCleanup
```

### Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `-TestAppRequirement` | String | Custom application requirements for testing | Idea Management System |
| `-Verbose` | Switch | Show detailed output during test execution | False |
| `-SkipCleanup` | Switch | Keep generated artifacts for inspection | False |
| `-Repo` | String | GitHub repository for issue creation | "jnPiyush/AI-Squad" |

### Default Test Application: Idea Management System
- Centralized platform for capturing innovative ideas
- Business case with ROI, effort, and risk assessment
- Multi-stage approval workflow (Submitted → In Review → Approved → In Dev → In Production)
- Impact measurement and analytics

### Custom Test Applications
You can test AI-Squad with any application by providing custom requirements:

```powershell
$CustomRequirements = @"
# Feature: Customer Support Portal

## Overview
Build a comprehensive customer support portal with ticket management, knowledge base, and live chat.

## Core Features
- Ticket creation and tracking
- Knowledge base search
- Live chat with agent routing
- Customer satisfaction surveys
- Analytics dashboard
"@

.\tests\e2e-live-test.ps1 -TestAppRequirement $CustomRequirements
```

### Test Coverage (35 Tests)

#### PART 1-5: Component Testing (34 tests)
- ✅ 8 Agent & Setup Tests (PM, Architect, Engineer, Reviewer, UX, Doctor, Init, File Validation)
- ✅ 11 Orchestration Tests (Battle Plans, Captain, Work State, Dashboard, Run-Plan, Convoy, Handoff, Capabilities, Delegation, Graph)
- ✅ 5 Communication Tests (Collab, Signal, Clarify, Chat, Infrastructure)
- ✅ 6 Monitoring Tests (Health, Patrol, Recon, Scout, Theater, Watch)
- ✅ 4 Additional Tests (Init, Update, Report, GitHub Integration)

#### 🎯 PART 6: Full Autonomous Lifecycle (1 comprehensive test)

**Test 35: End-to-End Autonomous Development Workflow**

This is the **MOST IMPORTANT TEST** - it validates AI-Squad's core value:

**What it does:**
1. Creates realistic feature request (User Authentication & Authorization)
2. **Lets AI-Squad take over completely** - no manual intervention
3. Executes full workflow:
   - **Phase 1**: Captain breaks down feature into coordinated work items
   - **Phase 2**: PM generates Product Requirements Document (PRD)
   - **Phase 3**: Architect creates ADR + Technical Specifications
   - **Phase 4**: UX Designer creates user flows and wireframes
   - **Phase 5**: Engineer implements code with tests
   - **Phase 6**: Verifies work state tracking
   - **Phase 7**: Validates operational graph (agent coordination trace)
   - **Phase 8**: Comprehensive completion validation

**Success Criteria:**
- ✅ All 8 validation checks pass (≥75% required)
- ✅ PRD, ADR, SPEC, UX documents generated
- ✅ Engineer execution completed
- ✅ Work items tracked in system
- ✅ Operational graph captured agent coordination
- ✅ Full execution trace from start to finish

**Why this matters:**
This test proves AI-Squad works **as advertised** - you give it a feature request, and it autonomously delivers a complete solution with requirements, architecture, design, implementation, and tests. This is what makes AI-Squad different from individual AI coding assistants.

### Coverage Summary
- **Component Tests**: 34 tests (individual CLI commands)
- **Integration Test**: 1 test (full autonomous lifecycle)
- **Total**: 35 tests covering 100% of AI-Squad functionality

See full documentation in the test script comments.
