# Release Notes Sync Tool - Architecture Plan

## Problem Statement

The Release Docs team faces a workflow issue where PR reviewers suggest changes to map files (`releases/release-x.xx/release-notes/maps/*.yaml`), but authors must manually update two additional files:
1. `releases/release-x.xx/release-notes/release-notes-draft.json` - Update the `text` field
2. `releases/release-x.xx/release-notes/release-notes-draft.md` - Update the markdown content

This manual process is error-prone and time-consuming.

## Solution Overview

A Python-based CLI tool that synchronizes release note text across three file types:
- **Source of Truth**: YAML map files (`pr-<number>-map.yaml`)
- **Targets**: JSON file (`release-notes-draft.json`) and Markdown file (`release-notes-draft.md`)

## Key Understanding

### Data Flow
```
map.yaml (releasenote.text) 
    ↓
json (text field) 
    ↓
json (markdown field - text portion only, preserve metadata)
    ↓
markdown file (rendered from json markdown field)
```

### Newline Handling
- **YAML multi-line**: Treated as single paragraph unless explicit `\n` present
- **JSON text field**: Copied exactly as-is from YAML (including `\n` escape sequences)
- **JSON markdown field**: Text portion updated, but PR/author/SIG metadata preserved
- **Markdown file**: Renders actual newlines where `\n` appears in JSON markdown field

## Architecture Design

### Core Components

```
release-notes-sync/
├── sync_tool.py           # Main CLI entry point
├── file_loader.py         # File reading/parsing logic
├── comparator.py          # Text comparison logic
├── sync_engine.py         # Sync operation logic
├── validator.py           # Validation mode logic
├── git_helper.py          # Git operations
├── formatter.py           # Output formatting (tables, diffs)
└── constants.py           # Path patterns, constants
```

### Module Responsibilities

#### 1. `file_loader.py`
```python
Functions:
- load_map_file(path) -> dict
- load_json_file(path) -> dict
- load_markdown_file(path) -> str
- parse_yaml_text(yaml_text) -> str
- normalize_text(text) -> str  # Handle multi-line YAML vs \n
```

#### 2. `comparator.py`
```python
Functions:
- compare_texts(map_text, json_text) -> ComparisonResult
- extract_text_from_markdown(markdown_field) -> str
- are_texts_equivalent(text1, text2) -> bool
- generate_diff(old_text, new_text) -> str
```

#### 3. `sync_engine.py`
```python
Functions:
- sync_map_to_json(pr_number, map_text, json_data) -> dict
- sync_json_to_markdown(pr_number, json_entry, markdown_content) -> str
- update_json_markdown_field(old_markdown, new_text) -> str
- apply_sync(pr_numbers, release_dir) -> SyncResults
```

#### 4. `validator.py`
```python
Functions:
- validate_single_pr(pr_number, release_dir) -> ValidationResult
- validate_all_prs(release_dir) -> ValidationResults
- categorize_results() -> (correct, incorrect, missing)
- format_validation_table(results) -> str
```

#### 5. `git_helper.py`
```python
Functions:
- get_changed_files_since_commit(commit_id, directory) -> list
- filter_map_files(file_list) -> list
- extract_pr_numbers(map_files) -> list
```

#### 6. `formatter.py`
```python
Functions:
- format_diff_view(old, new) -> str
- format_validation_table(results) -> str
- format_sync_summary(results) -> str
- colorize_output(text, color) -> str
```

## Data Structures

### ComparisonResult
```python
{
    'pr_number': str,
    'map_text': str,
    'json_text': str,
    'json_markdown': str,
    'md_content': str,
    'map_json_match': bool,
    'json_md_match': bool,
    'status': 'correct' | 'incorrect' | 'missing_in_json' | 'missing_in_md'
}
```

### SyncOperation
```python
{
    'pr_number': str,
    'changes': {
        'json_text': {'old': str, 'new': str},
        'json_markdown': {'old': str, 'new': str},
        'md_content': {'old': str, 'new': str}
    },
    'applied': bool,
    'user_approved': bool
}
```

## Operation Modes

### 1. Validate Mode

**Purpose**: Check consistency without making changes

**Sub-modes**:
- **Incremental**: Validate only changed files since a commit
- **Global**: Validate all map files in release directory

**Algorithm**:
```
1. Load map files (filtered or all)
2. For each map file:
   a. Extract pr_number and text from map
   b. Load JSON, find entry by pr_number
   c. Compare map.text with json.text
   d. Extract text portion from json.markdown
   e. Compare with map.text (with newline rendering)
   f. Find entry in markdown file
   g. Compare with json.markdown field
3. Categorize results: Correct, Incorrect, Missing
4. Display results in table format
```

**Output Format**:
```
Validation Results:
===================

✓ CORRECT (45 entries)
  PR #117160: All fields match
  PR #122140: All fields match
  ...

✗ INCORRECT (3 entries)
  PR #133540:
    - JSON text: MISMATCH
    - JSON markdown: MISMATCH  
    - MD content: MISMATCH
    
  PR #132549:
    - JSON text: OK
    - JSON markdown: MISMATCH
    - MD content: MISMATCH

⚠ MISSING (1 entry)
  PR #999999: Exists in maps but not in JSON/MD
```

### 2. Sync Mode

**Purpose**: Synchronize changes from map files to JSON and markdown

**Algorithm**:
```
1. Load changed map files (or use validate results)
2. For each map requiring sync:
   a. Extract new text from map
   b. Load current JSON entry
   c. Generate diff: json.text (old → new)
   d. Update json.text with map.text
   e. Update json.markdown (text portion only)
   f. Generate diff: json.markdown (old → new)
   g. Find entry in markdown file
   h. Generate diff: markdown content (old → new)
   i. Show all diffs to user
   j. Prompt: "Apply these changes? [y/n]"
   k. If yes: Apply changes
   l. If no: Skip this PR
3. Save modified JSON and markdown files
4. Display summary
```

**Interactive Flow**:
```
Syncing PR #133540
===================

Map file: releases/release-1.35/release-notes/maps/pr-133540-map.yaml

[DIFF 1/3] JSON text field:
--- OLD
+++ NEW
@@ -1 +1 @@
-Added validation to ensure log-flush-frequency is a positive value.
+Added validation to ensure `log-flush-frequency` is a positive value, returning an error instead of causing a panic.

[DIFF 2/3] JSON markdown field:
--- OLD
+++ NEW
@@ -1 +1 @@
-Added validation to ensure log-flush-frequency is a positive value. ([#133540]...
+Added validation to ensure `log-flush-frequency` is a positive value, returning an error instead of causing a panic. ([#133540]...

[DIFF 3/3] Markdown file:
--- OLD
+++ NEW
@@ Line 6
-Added validation to ensure log-flush-frequency is a positive value. ([#133540]...
+Added validation to ensure `log-flush-frequency` is a positive value, returning an error instead of causing a panic. ([#133540]...

Apply changes for PR #133540? [y/n/q (quit)]: _
```

## CLI Interface

### Command Structure

```bash
# Validate changed files since commit
python sync_tool.py validate --since-commit <commit-id> --release 1.35

# Validate all files (global mode)
python sync_tool.py validate --global --release 1.35

# Sync changed files since commit (interactive)
python sync_tool.py sync --since-commit <commit-id> --release 1.35

# Sync specific PRs
python sync_tool.py sync --prs 133540,132549 --release 1.35

# Sync all (use with caution)
python sync_tool.py sync --global --release 1.35
```

### Arguments

**Common**:
- `--release X.XX` (required): Release version to work with
- `--repo-root PATH` (optional): Override repository root path

**Validate**:
- `--since-commit HASH` (optional): Only check files changed since commit
- `--global` (flag): Check all map files
- `--output {table|json|csv}` (default: table): Output format

**Sync**:
- `--since-commit HASH` (optional): Only sync files changed since commit
- `--prs 123,456` (optional): Sync specific PR numbers
- `--global` (flag): Sync all map files
- `--auto-yes` (flag): Skip confirmations (dangerous!)
- `--dry-run` (flag): Show what would be done without applying

## Text Comparison Logic

### Normalization Strategy

```python
def normalize_text(text: str) -> str:
    """Normalize text for comparison"""
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Normalize multiple spaces to single space
    text = ' '.join(text.split())
    
    # Keep \n escape sequences as-is for JSON
    # They represent intentional line breaks
    
    return text

def compare_map_to_json(map_text: str, json_text: str) -> bool:
    """Direct comparison - should be identical after normalization"""
    return normalize_text(map_text) == normalize_text(json_text)

def compare_json_to_markdown(json_text: str, markdown_field: str) -> bool:
    """Extract text portion from markdown field and compare"""
    # Extract text before PR link: "text ([#PR]..."
    match = re.match(r'^(.*?)\s*\(\[#\d+\]', markdown_field)
    if match:
        md_text = match.group(1).strip()
        return normalize_text(json_text) == normalize_text(md_text)
    return False
```

### Markdown Field Update

```python
def update_markdown_field(old_markdown: str, new_text: str) -> str:
    """Update text portion while preserving metadata"""
    # Pattern: "old_text ([#PR_NUM](url), [@author](url)) [SIG ...]"
    
    # Extract metadata (everything after first PR link)
    match = re.search(r'(\(\[#\d+\].*)', old_markdown)
    if match:
        metadata = match.group(1)
        return f"{new_text} {metadata}"
    
    # Fallback: just append if pattern not found
    return f"{new_text} {old_markdown}"
```

## Error Handling

### Validation Errors
- Missing map file → Report as "Missing in maps"
- Missing JSON entry → Report as "Missing in JSON"  
- Missing markdown entry → Report as "Missing in MD"
- Corrupted YAML → Skip with error message
- Corrupted JSON → Abort with clear error

### Sync Errors
- File write permission denied → Abort with error
- Git uncommitted changes → Warn user
- User cancellation → Clean exit
- Partial sync failure → Rollback or report

## Safety Features

1. **Dry-run mode**: Show changes without applying
2. **Interactive confirmation**: Ask before each change
3. **Backup before sync**: Optional JSON/MD backup
4. **Validation before sync**: Warn if validation finds issues
5. **Git integration**: Detect uncommitted changes

## Implementation Considerations

### Performance
- Cache parsed JSON to avoid repeated file reads
- Use generators for large file lists
- Minimal memory footprint (process one PR at a time)

### Testing Strategy
- Unit tests for each module
- Integration tests with sample release directory
- Edge case tests:
  - Multi-line YAML text
  - Text with explicit `\n`
  - Missing fields
  - Malformed files

### Code Style
- Simple, functional approach (no OOP)
- Type hints for clarity
- Docstrings for all functions
- Clear variable names
- Max 80 characters per line for readability

## Example Usage Workflow

### Scenario: PR Review Changes

1. **Reviewer comments on map files in PR**
2. **Author updates map files and commits**
3. **Author runs validation**:
   ```bash
   python sync_tool.py validate --since-commit HEAD~1 --release 1.35
   ```
4. **Tool shows mismatches**
5. **Author runs sync**:
   ```bash
   python sync_tool.py sync --since-commit HEAD~1 --release 1.35
   ```
6. **Tool shows diffs, author confirms each**
7. **Files updated, author commits**

### Scenario: Pre-release Global Check

```bash
# Check entire release for consistency
python sync_tool.py validate --global --release 1.35

# If issues found, review and fix
python sync_tool.py sync --global --release 1.35 --dry-run
```

## File Output Examples

### Validation Report (table format)

```
╔════════════╦═══════════╦═════════════╦═════════════╗
║ PR Number  ║ JSON Text ║ JSON MD     ║ MD File     ║
╠════════════╬═══════════╬═════════════╬═════════════╣
║ 117160     ║ ✓ OK      ║ ✓ OK        ║ ✓ OK        ║
║ 122140     ║ ✓ OK      ║ ✓ OK        ║ ✓ OK        ║
║ 133540     ║ ✗ DIFF    ║ ✗ DIFF      ║ ✗ DIFF      ║
║ 132549     ║ ✓ OK      ║ ✗ DIFF      ║ ✗ DIFF      ║
║ 999999     ║ ⚠ MISSING ║ ⚠ MISSING   ║ ⚠ MISSING   ║
╚════════════╩═══════════╩═════════════╩═════════════╝

Summary:
  ✓ Correct: 45
  ✗ Incorrect: 3
  ⚠ Missing: 1
```

### Sync Summary

```
Sync Complete!
==============

Changes Applied: 2 PRs
Skipped: 1 PR
Errors: 0

Modified Files:
  - releases/release-1.35/release-notes/release-notes-draft.json
  - releases/release-1.35/release-notes/release-notes-draft.md

Next Steps:
  1. Review changes: git diff
  2. Commit changes: git add . && git commit -m "sync: Update release notes from map changes"
```

## Future Enhancements

1. **Multi-release support**: Sync multiple releases at once
2. **Conflict detection**: Warn if JSON/MD have newer changes
3. **History tracking**: Log all sync operations
4. **Web UI**: Visual interface for validation/sync
5. **Pre-commit hook**: Auto-validate on git commit
6. **GitHub Actions**: Auto-sync on PR merge

## Dependencies

```
PyYAML>=6.0       # YAML parsing
colorama>=0.4     # Colored terminal output
tabulate>=0.9     # Table formatting
GitPython>=3.1    # Git operations (optional)
```

## Success Criteria

✓ Reduce manual sync time from 10+ minutes to <1 minute
✓ Eliminate human errors in text copying
✓ Clear validation reports for review process
✓ Interactive, safe sync process with diffs
✓ Simple, maintainable Python code (<500 lines total)