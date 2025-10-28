# Kubernetes Release Notes Sync Tool

A simple, effective Python tool to synchronize Kubernetes release notes across YAML map files, JSON, and Markdown files.

## Problem

When reviewers suggest changes to release note map files during PR review, authors must manually update:

1. `releases/release-x.xx/release-notes/maps/pr-XXXXX-map.yaml` (edited by reviewers)
2. `releases/release-x.xx/release-notes/release-notes-draft.json` (needs manual sync)
3. `releases/release-x.xx/release-notes/release-notes-draft.md` (needs manual sync)

This manual process is time-consuming and error-prone.

## Solution

This tool automates the synchronization with two modes:

- **Validate Mode**: Check consistency across all files without making changes
- **Sync Mode**: Apply changes from map files to JSON and Markdown with interactive diffs

## Quick Start

> [!Note]
> Refer – [Quickstart.md](docs/QUICKSTART.md)

### Installation

This project uses [`uv`](https://github.com/astral-sh/uv) for fast, reliable Python package management.

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Navigate to tools directory
cd releases/tools

# Install dependencies (uv will create a virtual environment automatically)
uv sync

# OR if pyproject.toml doesn't exist yet, install dependencies directly
uv pip install pyyaml colorama tabulate gitpython
```

### Basic Usage

```bash
# Validate files changed in your recent commit
python sync_tool.py validate --since-commit HEAD~1 --release 1.35

# Sync those changes interactively
python sync_tool.py sync --since-commit HEAD~1 --release 1.35

# Validate entire release (pre-release check)
python sync_tool.py validate --global --release 1.35
```

## Architecture

The tool follows a simple, functional design:

```
Map File (Source of Truth)
    ↓
JSON text field (sync from map)
    ↓
JSON markdown field (update text portion, preserve metadata)
    ↓
Markdown file (render from JSON markdown)
```

### Key Principles

1. **Map files are always the source of truth**
2. **Simple Python** - No OOP, no heavy frameworks, just functions
3. **User-friendly** - Clear diffs, interactive prompts, colored output
4. **Safe by default** - Validate before sync, confirm each change

## Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Complete system design, data flow, and component specifications
- **[IMPLEMENTATION_GUIDE.md](docs/IMPLEMENTATION_GUIDE.md)** - Detailed algorithms, pseudocode, flowcharts, and edge cases
- **[README.md](README.md)** - This file - quick start and overview

## Command Reference

### Validate Command

Check consistency without making changes.

```bash
# Validate changes since a commit
python sync_tool.py validate --since-commit <commit-hash> --release 1.35

# Validate specific PRs
python sync_tool.py validate --prs 133540,132549 --release 1.35

# Validate entire release
python sync_tool.py validate --global --release 1.35

# Output formats
python sync_tool.py validate --global --release 1.35 --output table  # default
python sync_tool.py validate --global --release 1.35 --output json
python sync_tool.py validate --global --release 1.35 --output csv
```

**Output Example**:

```
Validation Results:
===================

✓ CORRECT (45 entries)

✗ INCORRECT (2 entries)
  PR #133540:
    - JSON text: MISMATCH
    - JSON markdown: MISMATCH
    - MD content: MISMATCH

⚠ MISSING (1 entry)
  PR #999999: Exists in maps but not in JSON
```

### Sync Command

Apply changes from map files to JSON and Markdown.

```bash
# Sync changes since a commit (interactive)
python sync_tool.py sync --since-commit <commit-hash> --release 1.35

# Sync specific PRs
python sync_tool.py sync --prs 133540,132549 --release 1.35

# Dry run (see what would change)
python sync_tool.py sync --since-commit HEAD~1 --release 1.35 --dry-run

# Auto-approve all changes (dangerous!)
python sync_tool.py sync --since-commit HEAD~1 --release 1.35 --auto-yes
```

**Interactive Flow**:

```
Syncing PR #133540
===================

[DIFF 1/3] JSON text field:
--- OLD
+++ NEW
@@ -1 +1 @@
-Added validation to ensure log-flush-frequency is a positive value.
+Added validation to ensure `log-flush-frequency` is a positive value, returning an error instead of causing a panic.

[DIFF 2/3] JSON markdown field:
[... similar diff ...]

[DIFF 3/3] Markdown file:
[... similar diff ...]

Apply changes for PR #133540? [y/n/q]: y
✓ Changes applied successfully!

Syncing PR #132549
===================
[... next PR ...]
```

## Workflow Examples

### Scenario 1: After PR Review Comments

You've updated map files based on reviewer feedback:

```bash
# 1. Check what changed
git diff HEAD~1 releases/release-1.35/release-notes/maps/

# 2. Validate those changes
python sync_tool.py validate --since-commit HEAD~1 --release 1.35

# 3. Sync the changes
python sync_tool.py sync --since-commit HEAD~1 --release 1.35

# 4. Review and commit
git diff
git add releases/release-1.35/release-notes/
git commit -m "sync: Update release notes for PRs 133540, 132549"
```

### Scenario 2: Pre-Release Validation

Before cutting a release, validate everything:

```bash
# Check entire release for consistency
python sync_tool.py validate --global --release 1.35

# If issues found, review them
python sync_tool.py validate --global --release 1.35 --output json > validation.json

# Fix issues and sync
python sync_tool.py sync --global --release 1.35
```

### Scenario 3: Fixing a Specific PR

Fix one specific PR's release notes:

```bash
# 1. Edit the map file
vim releases/release-1.35/release-notes/maps/pr-133540-map.yaml

# 2. Validate just that PR
python sync_tool.py validate --prs 133540 --release 1.35

# 3. Sync just that PR
python sync_tool.py sync --prs 133540 --release 1.35
```

## How It Works

### Text Synchronization

1. **Map → JSON text field**: Direct copy with normalization

   - Multi-line YAML collapsed to single line (unless explicit `\n`)
   - Whitespace normalized

2. **JSON text → JSON markdown field**: Update text portion only

   - Extract text before `([#PR...` pattern
   - Replace with new text
   - Preserve PR link, author, and SIG metadata

3. **JSON markdown → Markdown file**: Direct replacement
   - Find old markdown line in file
   - Replace with new markdown line

### Newline Handling

**In map file (YAML)**:

```yaml
text: Line one
  and line two
```

Becomes: `"Line one and line two"`

**With explicit newlines**:

```yaml
text: Line one\nLine two
```

Stays: `"Line one\nLine two"` (rendered as line break in markdown)

## Safety Features

1. **Validation before sync**: Run validate first to see what needs fixing
2. **Interactive approval**: Confirm each change individually
3. **Dry-run mode**: See what would change without applying
4. **Clear diffs**: See exact old→new changes before approving
5. **Git awareness**: Optionally detect uncommitted changes
6. **Backup option**: Save JSON/MD before modifications

## Error Handling

The tool handles common issues gracefully:

- **Missing map file**: Reports in validation, skips in sync
- **Missing JSON entry**: Error - cannot sync without base entry
- **Corrupted YAML**: Skips with clear error message
- **File permission errors**: Aborts with helpful message
- **User cancellation**: Clean exit, no partial changes
