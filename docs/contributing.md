# Contributing

Thank you for your interest in contributing to StreamBlocks!

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/hotherio/streamblocks.git
   cd streamblocks
   ```

2. **Install dependencies**:
   ```bash
   uv sync --all-extras
   ```

3. **Install pre-commit hooks**:
   ```bash
   uv run lefthook install
   ```

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_processor.py
```

### Running Examples

```bash
# Run all examples
uv run python examples/run_examples.py --skip-api

# Run specific category
uv run python examples/run_examples.py --category 01_basics
```

### Code Quality

```bash
# Run all pre-commit checks
uv run lefthook run pre-commit --all-files -- --no-stash

# Format code
uv run ruff format

# Lint code
uv run ruff check --fix

# Type check
uv run basedpyright
```

## Pull Request Guidelines

### Before Submitting

1. **Create a branch**:
   ```bash
   git checkout -b feat/my-feature
   ```

2. **Make your changes**:
   - Write tests for new functionality
   - Update documentation if needed
   - Follow existing code style

3. **Run checks**:
   ```bash
   uv run lefthook run pre-commit --all-files -- --no-stash
   uv run pytest
   ```

4. **Commit with conventional commits**:
   ```bash
   git commit -m "feat: add new feature"
   ```

### Conventional Commits

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test changes
- `refactor:` - Code refactoring
- `perf:` - Performance improvements
- `chore:` - Maintenance tasks

### PR Title

PR titles must follow conventional commit format:

```
feat: add Anthropic adapter support
fix: handle empty stream correctly
docs: update getting started guide
```

## Code Style

- **Line length**: 120 characters
- **Quotes**: Double quotes
- **Type hints**: Required for all public APIs
- **Docstrings**: Google style

## Adding Examples

When adding new examples:

1. Place in the appropriate category folder (e.g., `examples/03_adapters/`)
2. Use numbered prefix (e.g., `14_new_feature.py`)
3. Include a docstring explaining the example
4. Add `if __name__ == "__main__":` block
5. Test with the example runner

## Documentation

- Documentation is in `docs/`
- Uses MkDocs with Material theme
- Build locally: `uv run mkdocs serve`

## Questions?

Open a [GitHub Discussion](https://github.com/hotherio/streamblocks/discussions) for questions.
