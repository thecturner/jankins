# Contributing to jankins

Thank you for considering contributing to jankins! This document outlines the process and guidelines.

## Development Setup

1. Clone the repository:
```bash
git clone https://github.com/your-org/jankins.git
cd jankins
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Run tests:
```bash
pytest
```

## Code Style

- Use Black for formatting: `black src/ tests/`
- Use Ruff for linting: `ruff check src/ tests/`
- Use mypy for type checking: `mypy src/`
- Follow PEP 8 conventions
- Add type hints to all functions
- Write docstrings for public APIs

## Testing

- Write tests for all new features
- Maintain or improve code coverage
- Use pytest fixtures for common setup
- Mock external dependencies (Jenkins API)

Run tests with:
```bash
pytest -v
```

Run with coverage:
```bash
pytest --cov=jankins --cov-report=html
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests and linting
5. Commit with clear messages
6. Push to your fork
7. Open a pull request

### PR Guidelines

- Describe what the PR does
- Reference any related issues
- Include examples if adding new tools
- Update documentation as needed
- Add tests for new functionality

## Adding New Tools

When adding a new MCP tool:

1. Add implementation to appropriate module in `src/jankins/tools/`
2. Register the tool in the module's `register_*_tools()` function
3. Add tests in `tests/test_tools_*.py`
4. Document the tool in README.md
5. Consider adding a related prompt template

Example tool structure:
```python
async def my_tool_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    correlation_id = str(uuid.uuid4())
    start_time = time.time()

    with RequestLogger(logger, "my_tool", correlation_id):
        # Tool implementation
        result = {"status": "success"}

        took_ms = int((time.time() - start_time) * 1000)
        return TokenAwareFormatter.add_metadata(
            result, correlation_id, took_ms, OutputFormat.SUMMARY
        )

mcp_server.register_tool(Tool(
    name="my_tool",
    description="What this tool does",
    parameters=[
        ToolParameter("arg1", ToolParameterType.STRING, "Description", required=True),
    ],
    handler=my_tool_handler
))
```

## Documentation

- Keep README.md up to date
- Add docstrings to new modules and functions
- Include usage examples
- Document configuration options

## Release Process

1. Update version in `pyproject.toml` and `src/jankins/__init__.py`
2. Update CHANGELOG.md
3. Create a git tag: `git tag v0.2.0`
4. Push tag: `git push origin v0.2.0`
5. Create GitHub release with notes

## Questions?

Open an issue or start a discussion on GitHub.
