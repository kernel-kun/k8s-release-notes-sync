# Project Structure

This document describes the organization of the Kubernetes Release Notes Sync Tool.

## Directory Layout

```
releases/tools/
├── release_notes_sync/          # Main Python package
│   ├── __init__.py              # Package initialization
│   ├── constants.py             # Configuration constants and path helpers
│   ├── file_loader.py           # File I/O operations (YAML, JSON, MD)
│   ├── comparator.py            # Text comparison and diff generation
│   ├── formatter.py             # Output formatting (tables, colors)
│   ├── validator.py             # Validation mode implementation
│   ├── sync_engine.py           # Sync operations logic
│   └── git_helper.py            # Git integration utilities
│
├── tests/                       # Test suite (to be implemented)
│   ├── __init__.py
│   ├── test_file_loader.py
│   ├── test_comparator.py
│   ├── test_validator.py
│   ├── test_sync_engine.py
│   └── fixtures/                # Test data
│
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md          # System design and specifications
│   ├── IMPLEMENTATION_GUIDE.md  # Detailed algorithms and pseudocode
│   ├── UV_SETUP.md              # UV package manager guide
│   └── PROJECT_STRUCTURE.md     # This file
│
├── sync_tool.py                 # CLI entry point
├── pyproject.toml               # Project configuration (uv/pip)
├── uv.lock                      # Dependency lock file (auto-generated)
├── .python-version              # Python version specification (3.11)
├── .gitignore                   # Git ignore patterns
├── LICENSE                      # MIT License
├── CONTRIBUTING.md              # Contribution guidelines
└── README.md                    # User guide and quick start
```

## Module Descriptions

### Core Package (`release_notes_sync/`)

#### `constants.py`
- Configuration constants (file patterns, paths, statuses)
- Path helper functions for release directories
- Color codes and symbols for output formatting

#### `file_loader.py`
- Load/save YAML map files
- Load/save JSON release notes
- Load/save Markdown files
- Text normalization for comparison
- PR number extraction utilities

#### `comparator.py`
- Text comparison with normalization
- Diff generation (unified format)
- Markdown field text extraction
- ComparisonResult data class

#### `formatter.py`
- Validation results table formatting
- Sync summary display
- Colored terminal output
- CSV and JSON output formats

#### `validator.py`
- Single PR validation
- Batch PR validation (all/incremental)
- Result categorization (correct/incorrect/missing)
- Validation summary generation

#### `sync_engine.py`
- Sync single PR from map to JSON/MD
- Batch sync with approval workflow
- Markdown metadata preservation
- Diff preparation and display

#### `git_helper.py`
- Git diff operations
- Changed file detection
- PR number extraction from git history
- Repository validation

### CLI Tool

#### `sync_tool.py`
- Command-line interface
- Argument parsing
- Command handlers (validate, sync)
- Interactive approval workflow

## File Relationships

```
sync_tool.py
    ↓
validator.py / sync_engine.py
    ↓
comparator.py
    ↓
file_loader.py
    ↓
constants.py

formatter.py ← (used by sync_tool.py for display)
git_helper.py ← (used by sync_tool.py for --since-commit)
```

## Data Flow

### Validation Mode
```
1. sync_tool.py parses args
2. git_helper.py gets changed files (if --since-commit)
3. validator.py loads files via file_loader.py
4. comparator.py checks text equivalence
5. formatter.py displays results
```

### Sync Mode
```
1. sync_tool.py parses args
2. git_helper.py gets changed files (if --since-commit)
3. sync_engine.py prepares changes
4. comparator.py generates diffs
5. formatter.py shows diffs to user
6. User approves → sync_engine.py applies changes
7. file_loader.py saves updated files
```

## Configuration Files

### `pyproject.toml`
- Project metadata
- Dependencies
- Development dependencies
- Build configuration
- Tool settings (ruff, black, pytest)

### `.python-version`
- Specifies Python 3.11
- Used by `uv` and `pyenv`

### `.gitignore`
- Excludes `.venv/`, `__pycache__/`, etc.
- Generated files (`.pyc`, `uv.lock`)

## Documentation Structure

### User Documentation
- **README.md**: Quick start, basic usage, examples
- **docs/UV_SETUP.md**: Installation and setup guide

### Developer Documentation
- **CONTRIBUTING.md**: How to contribute
- **docs/ARCHITECTURE.md**: System design
- **docs/IMPLEMENTATION_GUIDE.md**: Detailed algorithms
- **docs/PROJECT_STRUCTURE.md**: This file

## Testing Strategy

Tests should be organized by module:
- Unit tests for each module
- Integration tests for end-to-end workflows
- Fixtures for sample release data

## Development Workflow

1. **Setup**: `uv sync --native-tls`
2. **Activate**: `source .venv/bin/activate`
3. **Develop**: Edit files in `release_notes_sync/`
4. **Test**: `uv run pytest`
5. **Format**: `uv run black .`
6. **Lint**: `uv run ruff check .`
7. **Run**: `python sync_tool.py <command>`

## Future Enhancements

Potential additions to the structure:
- `examples/`: Example usage scripts
- `.github/`: GitHub Actions workflows
- `scripts/`: Development/deployment scripts
- `benchmarks/`: Performance testing
- `docker/`: Container configuration

## Notes

- All Python files follow PEP 8 style
- Type hints used throughout
- Docstrings in Google/NumPy style
- Maximum line length: 88 characters (Black default)
- Imports organized: stdlib, third-party, local