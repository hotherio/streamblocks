# Governance

This document describes the governance model for the Streamblocks project.

## Overview

Streamblocks is a small, focused project maintained by a single lead maintainer with potential for community contributions. We follow a **Benevolent Dictator For Life (BDFL)** model adapted for a small project.

## Roles

### Lead Maintainer (BDFL)

- Has final decision-making authority
- Responsible for project direction and releases
- Reviews and merges contributions
- Maintains project infrastructure

### Contributors

Anyone who contributes to the project through:
- Code contributions (pull requests)
- Documentation improvements
- Bug reports and feature requests
- Helping others in discussions

## Decision Making

### Day-to-Day Decisions

- Bug fixes and minor improvements: Merged after review
- Documentation updates: Merged after review
- Dependency updates: Handled by Renovate with maintainer oversight

### Significant Decisions

For larger changes (new features, API changes, architectural decisions):

1. **Proposal**: Open an issue or discussion describing the change
2. **Discussion**: Community feedback is welcomed
3. **Decision**: Lead maintainer makes the final call
4. **Implementation**: Via pull request with standard review

### Breaking Changes

Breaking changes require:
- Clear justification in the proposal
- Migration path documentation
- Appropriate version bump (semver)
- Changelog entry

## Contributions

We welcome contributions! Please see [CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines.

### Code Review

- All changes require review before merging
- The lead maintainer reviews all contributions
- We aim to respond to PRs within a week

## Releases

- Releases follow [Semantic Versioning](https://semver.org/)
- Changelogs are generated automatically via git-cliff
- The lead maintainer has release authority

## Code of Conduct

All participants must follow our [Code of Conduct](.github/CODE_OF_CONDUCT.md).

## Changes to Governance

This governance document may be updated by the lead maintainer. Significant changes will be communicated to the community.

## Contact

- **GitHub**: [@aquemy](https://github.com/aquemy)
- **Email**: contact@hother.io
