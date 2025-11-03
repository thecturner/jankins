# Contributing to jankins

Thank you for your interest in contributing to jankins! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Code Style](#code-style)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code. Please be respectful and constructive in all interactions.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git
- Jenkins instance (for integration testing)

### Finding an Issue

- Check the [issue tracker](https://github.com/thecturner/jankins/issues)
- Look for issues labeled `good first issue` or `help wanted`
- Comment on the issue to let others know you're working on it

## Development Setup

1. **Fork and clone the repository**

```bash
git clone git@github-thecturner:YOUR_USERNAME/jankins.git
cd jankins
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**

```bash
pip install -e ".[dev]"
```

4. **Install pre-commit hooks**

```bash
pre-commit install
```

5. **Verify setup**

```bash
pytest
ruff check src tests
mypy src
```

## Development Workflow

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

2. **Make your changes**

- Write code following our style guidelines
- Add tests for new functionality
- Update documentation as needed

3. **Run tests and checks**

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=jankins --cov-report=term-missing

# Lint and format
ruff check src tests
ruff format src tests

# Type checking
mypy src

# Security checks
bandit -r src
```

4. **Run pre-commit hooks**

```bash
pre-commit run --all-files
```

5. **Commit your changes**

```bash
git add .
git commit -m "feat: add new feature"
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_cache.py

# Run specific test
pytest tests/test_cache.py::TestResponseCache::test_cache_expiration

# Run with markers
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Run in parallel
pytest -n auto
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names: `test_<function>_<scenario>_<expected>`
- Use fixtures from `conftest.py`
- Mark tests appropriately:
  - `@pytest.mark.unit` - Unit tests
  - `@pytest.mark.integration` - Integration tests
  - `@pytest.mark.slow` - Slow running tests
  - `@pytest.mark.security` - Security tests

Example:

```python
import pytest
from jankins.cache import ResponseCache

@pytest.mark.unit
class TestResponseCache:
    def test_cache_expiration(self):
        cache = ResponseCache(ttl_seconds=1)
        cache.set("key", "value")
        time.sleep(1.1)
        assert cache.get("key") is None
```

### Test Coverage

We aim for >90% test coverage. Check coverage with:

```bash
pytest --cov=jankins --cov-report=html
open htmlcov/index.html
```

## Code Style

We use Ruff for linting and formatting (replacing Black and Flake8):

### Formatting

```bash
# Check formatting
ruff format --check src tests

# Auto-format
ruff format src tests
```

### Linting

```bash
# Check linting
ruff check src tests

# Auto-fix issues
ruff check --fix src tests
```

### Type Hints

- All functions must have type hints
- Use `mypy` for type checking
- Follow PEP 484

```python
def get_build(name: str, number: int) -> Dict[str, Any]:
    """Get build information."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def example_function(param1: str, param2: int) -> bool:
    """Short description.

    Longer description if needed.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param2 is negative
    """
    ...
```

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, missing semicolons, etc.)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes
- `security`: Security fixes

### Examples

```bash
feat(tools): add retry_flaky_build tool

Adds new MCP tool for automatically retrying flaky builds
with configurable max retries and delay.

Closes #123
```

```bash
fix(cache): fix cache expiration logic

Cache entries were not expiring correctly due to
timestamp comparison bug.

Fixes #456
```

## Pull Request Process

1. **Update CHANGELOG.md**

Add your changes under the `[Unreleased]` section following the existing format.

2. **Ensure all checks pass**

- All tests pass
- Code coverage is maintained or improved
- Linting passes
- Type checking passes
- Pre-commit hooks pass

3. **Submit PR**

- Use the PR template
- Link related issues
- Provide clear description
- Add screenshots/logs if applicable

4. **Code Review**

- Address reviewer feedback
- Keep discussion constructive
- Update PR as needed

5. **Merge**

- PRs require approval from maintainer
- Squash and merge is preferred
- Delete branch after merge

## Release Process

Releases are automated via GitHub Actions:

1. **Update version**

```bash
# Update version in pyproject.toml
version = "0.3.0"
```

2. **Update CHANGELOG.md**

Move changes from `[Unreleased]` to new version section:

```markdown
## [0.3.0] - 2025-01-15

### Added
- New feature...
```

3. **Commit and tag**

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.3.0"
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin master --tags
```

4. **GitHub Actions**

Automated release workflow:
- Builds distributions
- Generates SLSA provenance
- Signs with Sigstore
- Creates GitHub release
- Publishes to PyPI

## Project Structure

```
jankins/
├── .github/              # GitHub workflows and templates
├── src/jankins/          # Source code
│   ├── analyzers/       # Build log analyzers
│   ├── jenkins/         # Jenkins API integration
│   ├── mcp/             # MCP protocol implementation
│   ├── tools/           # MCP tools
│   ├── prompts/         # MCP prompts
│   ├── middleware/      # Rate limiting, etc.
│   ├── cache.py         # Response caching
│   ├── config.py        # Configuration
│   ├── errors.py        # Error handling
│   ├── metrics.py       # Prometheus metrics
│   └── server.py        # Main server
├── tests/               # Test suite
├── docs/                # Documentation
├── .pre-commit-config.yaml
├── pyproject.toml       # Project configuration
├── tox.ini              # Tox configuration
└── README.md
```

## Adding New Features

### Adding a New MCP Tool

1. Create tool in `src/jankins/tools/`
2. Add tests in `tests/test_<tool>.py`
3. Register tool in MCP server
4. Update documentation
5. Add to CHANGELOG.md

Example:

```python
# src/jankins/tools/custom.py
from typing import Dict, Any

async def my_new_tool(
    adapter: JenkinsAdapter,
    name: str,
    **kwargs
) -> Dict[str, Any]:
    """Tool description.

    Args:
        adapter: Jenkins adapter
        name: Job name
        **kwargs: Additional arguments

    Returns:
        Tool result
    """
    result = adapter.some_operation(name)
    return {"status": "ok", "data": result}
```

### Adding a New Analyzer

1. Create analyzer in `src/jankins/analyzers/`
2. Inherit from `LogAnalyzer`
3. Implement `can_analyze()` and `analyze()`
4. Add tests
5. Register in analyzer registry

## Documentation

- Update README.md for user-facing changes
- Update inline documentation (docstrings)
- Add examples for new features
- Update CHANGELOG.md

## Getting Help

- Open a [GitHub Discussion](https://github.com/thecturner/jankins/discussions)
- Ask in pull request comments
- Check existing issues and PRs

## Recognition

Contributors are recognized in:
- CHANGELOG.md
- GitHub contributors page
- Release notes

Thank you for contributing to jankins! 🎉
