# Commit Message Convention

This repository uses [Conventional Commits](https://www.conventionalcommits.org/) for automated versioning and changelog generation.

## Format

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

## Types

- **feat**: New feature (triggers MINOR version bump)
- **fix**: Bug fix (triggers PATCH version bump)
- **perf**: Performance improvement (triggers PATCH version bump)
- **docs**: Documentation changes
- **style**: Code style changes (formatting, missing semi-colons, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **build**: Changes to build system or dependencies
- **ci**: Changes to CI/CD configuration
- **chore**: Other changes that don't modify src or test files

## Breaking Changes

Add `BREAKING CHANGE:` in the footer or append `!` after type to trigger MAJOR version bump:

```
feat!: remove deprecated API endpoint

BREAKING CHANGE: The /api/v1/old endpoint has been removed. Use /api/v2/new instead.
```

## Examples

### Feature (MINOR bump)
```
feat(jenkins): add Blue Ocean pipeline graph support

Adds support for parsing and visualizing Jenkins Blue Ocean pipeline
execution graphs with parallel stage detection.
```

### Bug Fix (PATCH bump)
```
fix(metrics): resolve deadlock in percentile calculation

Previously get_summary() would deadlock when calling get_percentile()
due to nested lock acquisition. Added _calculate_percentile() helper.
```

### Performance (PATCH bump)
```
perf(cache): improve response cache lookup speed

Switched from linear search to hash-based lookup for cache keys,
reducing average lookup time from O(n) to O(1).
```

### Breaking Change (MAJOR bump)
```
feat(api)!: redesign rate limiter API

BREAKING CHANGE: RateLimiter.allow_request() has been replaced with
check_rate_limit() which returns a tuple (allowed, retry_after).

Migration:
- Old: limiter.allow_request(user_id)
- New: allowed, retry_after = limiter.check_rate_limit(user_id)
```

## Scopes

Common scopes in this project:
- `jenkins`: Jenkins API integration
- `mcp`: MCP protocol implementation
- `cache`: Response caching
- `metrics`: Metrics collection
- `api`: Public API
- `ci`: CI/CD workflows
- `deps`: Dependencies
- `docker`: Docker configuration

## Automated Releases

When you push to `master`:
1. Semantic Release analyzes commit messages
2. Determines version bump (MAJOR.MINOR.PATCH)
3. Updates version in `pyproject.toml` and `__init__.py`
4. Generates/updates CHANGELOG.md
5. Creates git tag (e.g., `v0.3.0`)
6. Pushes release commit and tag
7. Triggers release workflow to publish to PyPI

## What Gets Released

- **MAJOR**: Breaking changes (`feat!:`, `fix!:`, or `BREAKING CHANGE:` in footer)
- **MINOR**: New features (`feat:`)
- **PATCH**: Bug fixes and performance improvements (`fix:`, `perf:`)

## Commits That DON'T Trigger Releases

These commit types do not trigger a new release:
- `docs:` - Documentation only changes
- `style:` - Code formatting
- `test:` - Test updates
- `chore:` - Maintenance tasks
- `ci:` - CI/CD configuration
- `build:` - Build system changes
- `refactor:` - Code refactoring without behavior changes

## Tips

1. **Keep commits atomic**: One logical change per commit
2. **Write clear subjects**: Be specific about what changed
3. **Use imperative mood**: "add feature" not "added feature"
4. **Reference issues**: Include issue numbers in footer (e.g., `Fixes #123`)
5. **Test before committing**: All tests should pass

## Enforcement

A pre-commit hook validates commit messages. To install:

```bash
pip install -e ".[dev]"
pre-commit install
```

The CI pipeline also validates commit messages on pull requests.
