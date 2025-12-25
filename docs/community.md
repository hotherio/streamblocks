# Community & Support

## Getting Help

### GitHub Issues

For bug reports and feature requests, please use [GitHub Issues](https://github.com/hotherio/streamblocks/issues).

When reporting a bug, please include:

- StreamBlocks version (`pip show streamblocks`)
- Python version
- Minimal reproducible example
- Expected vs actual behavior

### Discussions

For questions and general discussion, use [GitHub Discussions](https://github.com/hotherio/streamblocks/discussions).

## Contributing

We welcome contributions! See our [Contributing Guide](contributing.md) for details.

### Ways to Contribute

- **Report bugs**: Open an issue with a minimal reproducible example
- **Suggest features**: Open an issue describing the use case
- **Improve documentation**: Submit PRs for docs improvements
- **Add examples**: Share your StreamBlocks usage patterns
- **Write code**: Fix bugs or implement features

### Development Setup

```bash
# Clone the repository
git clone https://github.com/hotherio/streamblocks.git
cd streamblocks

# Install development dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linting
uv run lefthook run pre-commit --all-files
```

## Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please read our [Code of Conduct](https://github.com/hotherio/streamblocks/blob/main/.github/CODE_OF_CONDUCT.md).

## License

StreamBlocks is released under the MIT License. See [LICENSE](https://github.com/hotherio/streamblocks/blob/main/LICENSE) for details.
