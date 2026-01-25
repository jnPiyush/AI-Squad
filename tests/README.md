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
**Coverage**: All 28 features with real execution (no mocks)

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

### Coverage (28 Features)
- ✅ 5 Agent Types (PM, Architect, Engineer, UX, Reviewer)
- ✅ 9 Orchestration Features (Battle Plans, Captain, Work State, etc.)
- ✅ 5 Communication Features (Collab, Signal, Clarify, etc.)
- ✅ 6 Monitoring Features (Health, Patrol, Recon, etc.)
- ✅ 3 Additional Systems (Reporting, GitHub, File Generation)

See full documentation in the test script comments.
