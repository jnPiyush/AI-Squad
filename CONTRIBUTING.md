# CONTRIBUTING to AI-Squad

Thank you for considering contributing to AI-Squad! This guide will help you get started.

## Code of Conduct

Be respectful, inclusive, and collaborative. We're all here to build great tools together.

## How Can I Contribute?

### 1. Reporting Bugs

**Before submitting:**
- Check [existing issues](https://github.com/jnPiyush/AI-Squad/issues)
- Run `squad doctor` to validate setup
- Collect error messages and logs

**Submit bug report:**
```bash
gh issue create --title "[Bug] Description" --label "bug"
```

**Include:**
- AI-Squad version (`squad --version`)
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages / stack traces

### 2. Suggesting Features

**Before suggesting:**
- Check [existing issues](https://github.com/jnPiyush/AI-Squad/issues?q=is%3Aissue+label%3Aenhancement)
- Consider if it fits AI-Squad's goals

**Submit feature request:**
```bash
gh issue create --title "[Feature] Description" --label "enhancement"
```

**Include:**
- Use case / problem it solves
- Proposed solution
- Alternatives considered
- Impact on existing features

### 3. Contributing Code

**Workflow:**

```bash
# 1. Fork the repository
gh repo fork jnPiyush/AI-Squad --clone

# 2. Create branch
cd AI-Squad
git checkout -b feature/my-feature

# 3. Make changes
# ... edit code ...

# 4. Run tests
pytest tests/

# 5. Run linting
black ai_squad/
ruff check ai_squad/

# 6. Commit
git commit -m "feat: add my feature"

# 7. Push
git push origin feature/my-feature

# 8. Create PR
gh pr create --fill
```

## Development Setup

### Prerequisites

- Python 3.11+
- Git
- GitHub CLI (`gh`)

### Install for Development

```bash
# Clone
git clone https://github.com/jnPiyush/AI-Squad.git
cd AI-Squad

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Project Structure

```
AI-Squad/
├── ai_squad/           # Main package
│   ├── __init__.py
│   ├── cli.py          # CLI entry point
│   ├── agents/         # Agent implementations
│   ├── core/           # Core modules
│   ├── tools/          # GitHub, templates, etc.
│   ├── skills/         # 18 production skills
│   └── templates/      # Document templates
├── tests/              # Test suite
├── docs/               # Documentation
├── examples/           # Example projects
├── setup.py            # Package setup
├── pyproject.toml      # Modern config
└── README.md
```

## Coding Standards

### Python Style

- **Formatter:** Black (line length 100)
- **Linter:** Ruff
- **Type Checker:** mypy
- **Docstrings:** Google style

**Run formatters:**
```bash
black ai_squad/
ruff check ai_squad/ --fix
mypy ai_squad/
```

### Code Quality

- ✅ Type hints for all functions
- ✅ Docstrings for public APIs
- ✅ Unit tests for new features
- ✅ Integration tests for workflows
- ✅ ≥80% code coverage

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
type(scope): description

[optional body]

[optional footer]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `test` - Tests
- `refactor` - Code restructuring
- `perf` - Performance
- `chore` - Maintenance

**Examples:**
```bash
git commit -m "feat(agents): add collaborative planning mode"
git commit -m "fix(cli): handle missing config file gracefully"
git commit -m "docs(readme): add installation troubleshooting"
```

## Testing

### Run Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=ai_squad --cov-report=html

# Specific test
pytest tests/test_cli.py::test_init_command

# Watch mode
pytest-watch
```

### Writing Tests

**Location:** `tests/test_<module>.py`

**Structure:**
```python
import pytest
from ai_squad.module import function


class TestFunction:
    """Test function behavior"""
    
    def test_basic_case(self):
        """Test basic functionality"""
        result = function("input")
        assert result == "expected"
    
    def test_error_case(self):
        """Test error handling"""
        with pytest.raises(ValueError):
            function(None)
```

**Fixtures:**
```python
@pytest.fixture
def mock_config():
    """Mock configuration"""
    return Config({"project": {"name": "Test"}})
```

### Test Coverage

Maintain ≥80% coverage:
```bash
pytest --cov=ai_squad --cov-report=term-missing
```

## Documentation

### Adding Documentation

- **User guides:** `docs/*.md`
- **API docs:** Docstrings in code
- **Examples:** `examples/*/README.md`

### Building Docs

```bash
# Install docs dependencies
pip install -e ".[docs]"

# Build docs
mkdocs build

# Serve locally
mkdocs serve
```

### Docstring Format

```python
def function(param1: str, param2: int) -> bool:
    """
    Short description.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
    
    Returns:
        Description of return value
    
    Raises:
        ValueError: When param1 is empty
    
    Example:
        >>> function("test", 42)
        True
    """
    pass
```

## Pull Request Process

### Before Submitting

- [ ] Tests pass (`pytest`)
- [ ] Linting passes (`black`, `ruff`)
- [ ] Type checking passes (`mypy`)
- [ ] Documentation updated
- [ ] Changelog updated (if applicable)
- [ ] Commit messages follow convention

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation

## Testing
How has this been tested?

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Passes linting
- [ ] Passes type checking
```

### Review Process

1. **Automated checks** run (tests, linting)
2. **Maintainer review** (usually within 48 hours)
3. **Address feedback** if needed
4. **Approval** from maintainer
5. **Merge** (squash and merge)

## Release Process

(For maintainers)

1. Update version in `ai_squad/__version__.py`
2. Update CHANGELOG.md
3. Commit: `git commit -m "chore: release v0.x.0"`
4. Tag: `git tag v0.x.0`
5. Push: `git push origin master --tags`
6. GitHub Actions builds and publishes to PyPI

## Community

### Getting Help

- **Questions:** [GitHub Discussions](https://github.com/jnPiyush/AI-Squad/discussions)
- **Bugs:** [GitHub Issues](https://github.com/jnPiyush/AI-Squad/issues)
- **Chat:** [Discord](https://discord.gg/ai-squad) (if available)

### Stay Updated

- **Watch** the repository
- **Star** if you find it useful
- **Follow** [@jnPiyush](https://github.com/jnPiyush)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing!** 🎉

Every contribution, no matter how small, makes AI-Squad better for everyone.
