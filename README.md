# CHANGE-ME | Python Library Template


## Installation



## Documentation

To build and serve the documentation locally:

1. Install the dependencies:
```
uv sync --group doc
source .venv/bin/activate
```

2. Serve the documentation:
```
mkdocs serve
```

## Development

### Installation

The only command that should be necessary is:
```
uv sync --group dev
source .venv/bin/activate
lefthook install
```

It creates a virtual environment, install all dependencies required for development and install the library in editable mode.
It also installs the Lefthook git hooks manager.

### Git Hooks with Lefthook

This project uses Lefthook for managing git hooks. Hooks are automatically installed when you run `make install-dev`.

To run hooks manually:
```
# Run all pre-commit hooks
lefthook run pre-commit

# Run specific hook
lefthook run pre-commit --commands ruff-check

# Skip hooks for a single commit
git commit --no-verify -m "emergency fix"
```

For local customization, copy `.lefthook-local.yml.example` to `.lefthook-local.yml` and modify as needed.


### Tests

uv run -m pytest

### Coverage

uv run python -m pytest src --cov=hother

### Building the package

```
uv build
```

### Release process

This project uses Git tags for versioning with automatic semantic versioning based on conventional commits. Version numbers are automatically derived from Git tags using hatch-vcs.

#### Quick Release Commands

```bash
# Check current version
hatch version

# Create development release (v1.0.0 → v1.0.1-dev1)
hatch release dev

# Create release candidate (v1.0.1-dev1 → v1.0.1rc1)
hatch release rc

# Create final release (v1.0.1rc1 → v1.0.1)
hatch release final
```

#### Release from Specific Commit

You can optionally specify a commit SHA to create a release from:
```bash
# Release from a specific commit
hatch release dev abc123
hatch release rc def456
hatch release final 789xyz
```

The SHA must be:
- Reachable from HEAD (on current branch history)
- Not already included in a previous release

#### How it Works

- **Development releases** (`dev`): Increments patch version and adds `-dev` suffix
- **Release candidates** (`rc`): Removes `-dev` and adds `rc` suffix  
- **Final releases** (`final`): Uses git-cliff to analyze commits and automatically bumps major/minor/patch based on conventional commits

The release process:
1. Analyzes commit history (for final releases)
2. Calculates the next version number
3. Creates and pushes the git tag
4. GitHub Actions automatically builds and publishes the release

#### Manual Tagging (Advanced)

If needed, you can still create tags manually:
```bash
# Manual tag creation
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3
```

### Changelog Management

This project uses [git-cliff](https://git-cliff.org/) to automatically generate changelogs from conventional commits.

```
# Generate/update CHANGELOG.md
make changelog

# Preview unreleased changes
make changelog-unreleased

# Get changelog for latest tag (used in releases)
make changelog-tag
```

The changelog is automatically updated and included in GitHub releases when you push a version tag.

Generate the licenses:
```
uvx pip-licenses --from=mixed --order count -f md --output-file licenses.md
uvx pip-licenses --from=mixed --order count -f csv --output-file licenses.csv
```

Build the new documentation:
```
uv run mike deploy --push --update-aliases <version> latest
mike set-default latest
mike list
```
Checking the documentation locally
```
mike serve
```


## Development practices

### Branching & Pull-Requests

Each git branch should have the format `<tag>/item_<id>` with eventually a descriptive suffix.

We us a **Squash & Merge** approach.

### Conventional Commits

We use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

Format: `<type>(<scope>): <subject>`

`<scope>` is optional

#### Example

```
feat: add hat wobble
^--^  ^------------^
|     |
|     +-> Summary in present tense.
|
+-------> Type: chore, docs, feat, fix, refactor, style, or test.
```

More Examples:

- `feat`: (new feature for the user, not a new feature for build script)
- `fix`: (bug fix for the user, not a fix to a build script)
- `docs`: (changes to the documentation)
- `style`: (formatting, missing semi colons, etc; no production code change)
- `refactor`: (refactoring production code, eg. renaming a variable)
- `test`: (adding missing tests, refactoring tests; no production code change)
- `chore`: (updating grunt tasks etc; no production code change)
- `build`: (changes in the build system)
- `ci`: (changes in the CI/CD and deployment pipelines)
- `perf`: (significant performance improvement)
- `revert`: (revert a previous change)
