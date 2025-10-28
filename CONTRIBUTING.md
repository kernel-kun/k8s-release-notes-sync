# Contributing to Kubernetes Release Notes Sync Tool

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- [`uv`](https://github.com/astral-sh/uv) package manager
- Git

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd releases/tools
   ```

2. **Install dependencies**
   ```bash
   uv sync --native-tls
   ```

3. **Activate virtual environment**
   ```bash
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

## Project Structure

```
releases/tools/
├── release_notes_sync/      # Main package
│   ├── __init__.py
│   ├── constants.py         # Configuration
│   ├── file_loader.py       # File I/O
│   ├── comparator.py        # Text comparison
│   ├── formatter.py         # Output formatting
│   ├── validator.py         # Validation logic
│   ├── sync_engine.py       # Sync operations
│   └── git_helper.py        # Git integration
├── tests/                   # Test suite
├── docs/                    # Documentation
├── sync_tool.py             # CLI entry point
├── README.md                # User guide
├── CONTRIBUTING.md          # This file
└── pyproject.toml           # Project config
```

## Development Guidelines

### Code Style

- Follow PEP 8 style guide
- Use type hints for function parameters and returns
- Maximum line length: 88 characters (Black default)
- Write descriptive docstrings for all functions

### Code Organization

- **Simple over clever**: Write readable code
- **Functional over OOP**: Use pure functions where possible
- **Explicit over implicit**: Clear naming, no magic
- **Safe over fast**: Correctness first, optimize later

### Testing

Run tests before submitting:

```bash
uv run pytest
```

Add tests for new features:
- Unit tests in `tests/test_<module>.py`
- Integration tests for end-to-end workflows

### Documentation

- Update docs when changing functionality
- Include examples for new features
- Keep README.md up to date

## Making Changes

### Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes**
   - Write code
   - Add tests
   - Update documentation

3. **Test your changes**
   ```bash
   uv run pytest
   uv run ruff check .
   uv run black --check .
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat: add feature description"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

Use conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `test:` Test additions/changes
- `refactor:` Code refactoring
- `chore:` Maintenance tasks

Examples:
```
feat: add support for multi-release sync
fix: handle missing JSON entries correctly
docs: update README with new examples
```

## Code Review

### Before Requesting Review

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No unnecessary changes included

### Review Process

1. Maintainer reviews code
2. Address feedback
3. Re-request review if needed
4. Merge after approval

## Reporting Issues

### Bug Reports

Include:
- Python version
- uv version
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs

### Feature Requests

Include:
- Use case description
- Proposed solution
- Alternative approaches considered

## Questions?

For questions about:
- **Usage**: See [README.md](README.md)
- **Architecture**: See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Implementation**: See [docs/IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
