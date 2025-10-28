# Quick Start Guide

Get up and running with the Kubernetes Release Notes Sync Tool in 5 minutes.

## Prerequisites

- Python 3.11+
- Git
- [`uv`](https://github.com/astral-sh/uv) package manager

## Installation

```bash
# 1. Navigate to the tools directory
cd releases/tools

# 2. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Install dependencies
uv sync --native-tls

# 4. Activate virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
```

## Basic Usage

### Validate Release Notes

Check consistency across all files:

```bash
# Validate files changed in your last commit
python sync_tool.py validate --since-commit HEAD~1 --release 1.35

# Validate specific PRs
python sync_tool.py validate --prs 133540,132549 --release 1.35

# Validate entire release
python sync_tool.py validate --global --release 1.35
```

### Sync Changes

Apply changes from map files to JSON and Markdown:

```bash
# Sync changes from recent commit (interactive)
python sync_tool.py sync --since-commit HEAD~1 --release 1.35

# Sync specific PRs
python sync_tool.py sync --prs 133540 --release 1.35

# Dry-run to preview changes
python sync_tool.py sync --since-commit HEAD~1 --release 1.35 --dry-run
```

## Common Workflows

### After PR Review

```bash
# 1. Update map files based on feedback
vim releases/release-1.35/release-notes/maps/pr-133540-map.yaml

# 2. Validate the changes
python sync_tool.py validate --prs 133540 --release 1.35

# 3. Sync the changes
python sync_tool.py sync --prs 133540 --release 1.35

# 4. Review and commit
git diff
git add .
git commit -m "sync: Update release notes for PR 133540"
```

### Pre-Release Check

```bash
# Validate all release notes
python sync_tool.py validate --global --release 1.35

# If issues found, fix them
python sync_tool.py sync --global --release 1.35
```

## Output Formats

### Table (Default)
```bash
python sync_tool.py validate --release 1.35 --prs 133540
```

### JSON
```bash
python sync_tool.py validate --release 1.35 --prs 133540 --output json
```

### CSV
```bash
python sync_tool.py validate --release 1.35 --prs 133540 --output csv
```

## Help

```bash
# General help
python sync_tool.py --help

# Command-specific help
python sync_tool.py validate --help
python sync_tool.py sync --help
```

## Troubleshooting

### Dependencies Not Found

```bash
# Reinstall dependencies
uv sync --native-tls
```

### Module Import Errors

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Or run with uv directly
uv run python sync_tool.py validate --release 1.35 --prs 133540
```

### Git Not Found

```bash
# Install git
sudo apt-get install git  # Ubuntu/Debian
brew install git          # macOS
```

## Next Steps

- Read the [full README](../README.md) for detailed information
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- See [CONTRIBUTING.md](../CONTRIBUTING.md) to contribute

## Support

For issues or questions:
1. Check existing documentation
2. Search [GitHub Issues](https://github.com/kubernetes/sig-release/issues)
3. Ask in Kubernetes Slack #sig-release channel