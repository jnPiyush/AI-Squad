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
