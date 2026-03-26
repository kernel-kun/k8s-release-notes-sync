# Release Notes Review Utility (`rn_review`)

A Python utility for the Kubernetes Release Team to extract, review, and manage release notes from PRs. It integrates with the `krel` toolchain by reading its generated `release-notes-draft.md` and `release-notes-draft.json` files, and producing krel-compatible YAML map files for note overrides.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Commands](#commands)
  - [`extract`](#extract)
  - [`status`](#status)
  - [`generate-maps`](#generate-maps)
- [Workflow](#workflow)
- [Review JSON Schema](#review-json-schema)
- [Map File Format](#map-file-format)
- [Data Sources](#data-sources)
- [AI-Assisted Review](#ai-assisted-review)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Overview

During each Kubernetes release cycle, the Release Notes subteam:

1. Runs `krel release-notes` to generate `release-notes-draft.md` and `release-notes-draft.json`
2. Reviews each PR's release note for clarity, accuracy, and formatting
3. Creates YAML "map" files to override notes that need modification
4. Re-runs `krel` with `--maps-from` to apply the overrides

This utility automates steps 2–3 by:

- **Extracting** all PR entries from the markdown/JSON files
- **Fetching** the original author-written release note from each PR's GitHub description
- **Producing** an intermediate review JSON file where notes can be reviewed and edited
- **Generating** krel-compatible map files for all modified notes

---

## Prerequisites

- **Python 3.10+** (uses `from __future__ import annotations`, `dict | None` syntax)
- **Git** (for diff-based extraction mode)
- **GitHub Token** (optional but recommended — set `GITHUB_TOKEN` env var for API access)
- No external Python dependencies — uses only the standard library

---

## Quick Start

```bash
# Navigate to the scripts directory
cd krel-utils/scripts

# 1. Extract all PRs from release-notes-draft.md for release 1.36
python3 -m rn_review extract \
    --version 1.36 \
    --sig-release-dir /path/to/sig-release

# 2. Check review progress
python3 -m rn_review status \
    --review-file review-1.36.json

# 3. (Review and edit the JSON file — manually or with AI)

# 4. Generate map files for reviewed + modified PRs
python3 -m rn_review generate-maps \
    --review-file review-1.36.json \
    --version 1.36 \
    --sig-release-dir /path/to/sig-release
```

---

## Commands

### `extract`

Extracts PR entries from `release-notes-draft.md`, enriches them with metadata from `release-notes-draft.json`, and optionally fetches the author's original release note from the GitHub API.

```bash
python3 -m rn_review extract \
    --version <release-version> \
    --sig-release-dir <path-to-sig-release-repo> \
    [--output <output-file>] \
    [--mode full|diff] \
    [--old-ref <git-ref>] \
    [--new-ref <git-ref>] \
    [--fetch-github] \
    [--github-owner <owner>] \
    [--github-repo <repo>] \
    [--merge]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--version`, `-V` | *(required)* | Release version, e.g., `1.36` |
| `--sig-release-dir` | *(required)* | Path to the `sig-release` repository root |
| `--output`, `-o` | `review-<version>.json` | Output path for the review JSON file |
| `--mode` | `full` | `full` = all PRs from file; `diff` = only new/modified PRs between git refs |
| `--old-ref` | `HEAD~` | Old git ref for diff mode |
| `--new-ref` | `HEAD` | New git ref for diff mode |
| `--fetch-github` | `false` | Fetch PR descriptions from GitHub API |
| `--github-owner` | `kubernetes` | GitHub repository owner |
| `--github-repo` | `kubernetes` | GitHub repository name |
| `--merge` | `false` | Merge new PRs into an existing review file instead of overwriting |

**Examples:**

```bash
# Full extraction (all PRs)
python3 -m rn_review extract --version 1.36 --sig-release-dir ./sig-release

# Diff extraction (only PRs changed in last 3 commits)
python3 -m rn_review extract --version 1.36 --sig-release-dir ./sig-release \
    --mode diff --old-ref HEAD~3 --new-ref HEAD

# Full extraction with GitHub API enrichment
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
python3 -m rn_review extract --version 1.36 --sig-release-dir ./sig-release \
    --fetch-github

# Merge new PRs into existing review file (after krel regeneration)
python3 -m rn_review extract --version 1.36 --sig-release-dir ./sig-release \
    --merge --output review-1.36.json
```

### `status`

Displays review progress statistics from a review JSON file.

```bash
python3 -m rn_review status \
    --review-file <path-to-review-json> \
    [--json]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--review-file`, `-f` | *(required)* | Path to the review JSON file |
| `--json` | `false` | Output as JSON instead of human-readable table |

**Example output:**

```
==================================================
  Release Notes Review Progress
==================================================
  Total PRs:        330
  Reviewed:         280 (84.8%)
  Unreviewed:       50
  Modified:         51
  Map candidates:   45
==================================================
```

### `generate-maps`

Generates krel-compatible YAML map files for PRs where the note was modified during review.

```bash
python3 -m rn_review generate-maps \
    --review-file <path-to-review-json> \
    [--version <release-version>] \
    [--sig-release-dir <path>] \
    [--output-dir <path>] \
    [--overwrite] \
    [--dry-run] \
    [--include-unreviewed]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--review-file`, `-f` | *(required)* | Path to the review JSON file |
| `--version`, `-V` | *(optional)* | Release version (for auto-detecting output dir) |
| `--sig-release-dir` | *(optional)* | Path to sig-release repo (for auto-detecting output dir) |
| `--output-dir` | *(auto)* | Explicit output directory for map files |
| `--overwrite` | `false` | Overwrite existing map files |
| `--dry-run` | `false` | Preview what would be generated without writing |
| `--include-unreviewed` | `false` | Include unreviewed PRs in map generation |

**Output directory** is determined by either:
- `--output-dir /explicit/path` (takes precedence), or
- `--version` + `--sig-release-dir` → `sig-release/releases/release-<version>/release-notes/maps/`

**Examples:**

```bash
# Dry run — see what would be generated
python3 -m rn_review generate-maps \
    --review-file review-1.36.json \
    --output-dir ./test-maps \
    --dry-run

# Generate into the sig-release maps directory
python3 -m rn_review generate-maps \
    --review-file review-1.36.json \
    --version 1.36 \
    --sig-release-dir ./sig-release

# Overwrite existing map files
python3 -m rn_review generate-maps \
    --review-file review-1.36.json \
    --version 1.36 \
    --sig-release-dir ./sig-release \
    --overwrite
```

---

## Workflow

### Standard Release Notes Review Cycle

```
┌─────────────────────────────────────────────────────────────┐
│  1. krel generates release-notes-draft.md + .json           │
│     └─> sig-release/releases/release-X.Y/release-notes/     │
├─────────────────────────────────────────────────────────────┤
│  2. rn_review extract                                       │
│     └─> Creates review-X.Y.json with all PR entries         │
│         - originalNote (from GitHub API or JSON, immutable) │
│         - currentDraftNote (from markdown, editable)        │
├─────────────────────────────────────────────────────────────┤
│  3. Review Phase (manual or AI-assisted)                    │
│     └─> Edit currentDraftNote in the JSON file              │
│         Set reviewDone = true for each reviewed PR          │
├─────────────────────────────────────────────────────────────┤
│  4. rn_review generate-maps                                 │
│     └─> Creates pr-XXXXX-map.yaml for modified PRs          │
│         Only for PRs where reviewDone=true AND              │
│         originalNote ≠ currentDraftNote                     │
├─────────────────────────────────────────────────────────────┤
│  5. krel release-notes --maps-from=maps/                    │
│     └─> Applies map overrides to regenerate final notes     │
└─────────────────────────────────────────────────────────────┘
```

### Incremental Updates (after krel regeneration)

When `krel` regenerates the draft files mid-cycle:

```bash
# Extract only new/changed PRs and merge into existing review file
python3 -m rn_review extract \
    --version 1.36 \
    --sig-release-dir ./sig-release \
    --mode diff \
    --old-ref HEAD~1 \
    --new-ref HEAD \
    --merge \
    --output review-1.36.json
```

This preserves all existing review progress and only adds new PRs.

---

## Review JSON Schema

The review JSON file has this structure:

```json
{
  "metadata": {
    "releaseVersion": "1.36",
    "createdAt": "2026-03-26T08:52:40.973853+00:00",
    "updatedAt": "2026-03-26T09:15:00.000000+00:00",
    "extractionMode": "full",
    "oldRef": "",
    "newRef": "",
    "totalPRs": 330,
    "reviewedPRs": 280
  },
  "prs": [
    {
      "prNumber": 135393,
      "prUrl": "https://github.com/kubernetes/kubernetes/pull/135393",
      "author": "tosi3k",
      "sigs": ["node", "scheduling", "storage", "testing"],
      "kinds": ["feature"],
      "areas": ["test"],
      "originalNote": "The author's original release note (from GitHub API or JSON, immutable)",
      "currentDraftNote": "The editable note text — modify this during review",
      "reviewDone": false,
      "reviewNotes": "Optional reviewer comments"
    }
  ]
}
```

### Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `prNumber` | `int` | The PR number in kubernetes/kubernetes |
| `prUrl` | `string` | Full URL to the PR |
| `author` | `string` | GitHub username of the PR author |
| `sigs` | `string[]` | SIG labels from the PR |
| `kinds` | `string[]` | Kind labels (feature, bug, cleanup, etc.) |
| `areas` | `string[]` | Area labels (apiserver, kubelet, etc.) |
| `originalNote` | `string` | **Immutable** — the author's original release note. With `--fetch-github`, sourced from the PR body's `` ```release-note `` `` block. Without it, falls back to the text from `release-notes-draft.json`. |
| `currentDraftNote` | `string` | **Editable** — the note as it appears in the markdown draft. Modify this field during review. |
| `reviewDone` | `bool` | Set to `true` when review is complete |
| `reviewNotes` | `string` | Optional notes about the review decision |

---

## Map File Format

Generated map files follow the krel `ReleaseNotesMap` format:

```yaml
pr: 135393
releasenote:
  text: |-
    The modified release note content goes here.
    Can be multi-line.
  sigs:
  - node
  - scheduling
  kinds:
  - feature
  areas:
  - test
pr_body: ""
```

**Key points:**
- `pr_body` is always `""` (empty string) — krel logs a warning if it differs from the actual PR body
- `text` uses YAML block scalar style (`|-`) for clean multi-line support
- `sigs`, `kinds`, `areas` are included to re-assert the correct values
- Files are named `pr-<number>-map.yaml` and placed in the `maps/` directory

---

## Data Sources

The `originalNote` and `currentDraftNote` fields come from different sources depending on how you run the tool:

| Field | With `--fetch-github` | Without `--fetch-github` |
|-------|----------------------|--------------------------|
| `originalNote` | Author's text from the PR body's `` ```release-note `` `` block (GitHub API) | Text from `release-notes-draft.json` (krel's generated note) |
| `currentDraftNote` | Text from `release-notes-draft.md` (always) | Text from `release-notes-draft.md` (always) |

**Fallback chain for `originalNote`:**
1. GitHub API release-note block (if `--fetch-github` and data available)
2. Text from `release-notes-draft.json` (krel's generated note)
3. Text from `release-notes-draft.md` (same as `currentDraftNote`)

This means when `--fetch-github` is used, `originalNote` reflects what the PR author actually wrote, while `currentDraftNote` reflects what krel generated (possibly modified by existing map overrides). The difference between these two is what the review process aims to evaluate and refine.

---

## AI-Assisted Review

The review JSON file is designed to work with AI assistants. Here's a recommended workflow:

1. **Extract** PRs with `--fetch-github` to populate `originalNote` from the author's PR body
2. **Pass the JSON** to an AI with instructions like:
    ```
    Review each PR entry in this JSON file. For each PR:
    - Compare `originalNote` (what the author wrote) with `currentDraftNote` (current draft)
    - Ensure `currentDraftNote` follows these guidelines: @krel-utils/AIPrompts/release-notes-review-guidelines.md
    - Edit `currentDraftNote` if improvements are needed
    - Set `reviewDone` to `true` for each reviewed PR
    - Add any notes to `reviewNotes`
    ```
3. **Check progress** with `rn_review status`
4. **Generate maps** once review is complete

---

## Architecture

```
rn_review/
├── __init__.py              # Package version
├── __main__.py              # python -m rn_review entry point
├── cli.py                   # Argument parsing and command dispatch
├── config.py                # Constants, path builders, env config
├── models.py                # TypedDicts (PRReviewEntry, ReviewFile, etc.)
│                            # Dataclasses (PREntry, MapFileData)
├── review_file.py           # ReviewFileManager — CRUD for review JSON
├── map_generator.py         # YAML map file generation
├── README.md                # This file
└── extractors/
    ├── __init__.py
    ├── markdown_extractor.py  # Parse PRs from release-notes-draft.md
    ├── json_extractor.py      # Parse data from release-notes-draft.json
    ├── diff_extractor.py      # Git diff-based PR extraction
    └── github_extractor.py    # GitHub API — fetch PR descriptions
```

### Module Responsibilities

| Module | Purpose |
|--------|---------|
| [`cli.py`](cli.py) | Argument parsing, command routing, orchestration |
| [`config.py`](config.py) | Path construction (`build_notes_md_path`, etc.), constants |
| [`models.py`](models.py) | `PRReviewEntry` TypedDict, `PREntry` dataclass, `MapFileData` |
| [`review_file.py`](review_file.py) | `ReviewFileManager` — create, load, save, merge, query |
| [`map_generator.py`](map_generator.py) | `format_map_yaml()`, `generate_map_files()` |
| [`markdown_extractor.py`](extractors/markdown_extractor.py) | Regex-based markdown parsing |
| [`json_extractor.py`](extractors/json_extractor.py) | `DraftJSONData` — lookup by PR number |
| [`diff_extractor.py`](extractors/diff_extractor.py) | `git show` based file comparison |
| [`github_extractor.py`](extractors/github_extractor.py) | `GitHubExtractor` — API client with caching and retry |

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_TOKEN` | No (recommended) | GitHub personal access token for API access. Without it, rate limit is 60 requests/hour. With it, 5000/hour. |

### Expected File Layout

The utility expects the standard sig-release repository structure:

```
sig-release/
└── releases/
    └── release-<version>/
        └── release-notes/
            ├── release-notes-draft.md    # Generated by krel
            ├── release-notes-draft.json  # Generated by krel
            └── maps/                     # Map files go here
                ├── pr-12345-map.yaml
                └── pr-67890-map.yaml
```

---

## Troubleshooting

### "No PR entries found"

- Verify the markdown file exists at the expected path
- Check that the release version matches the directory name (e.g., `1.36` → `release-1.36`)
- Use `--verbose` flag for detailed logging

### GitHub API rate limiting

- **Set `GITHUB_TOKEN` environment variable** — this is the most important step. Without it, you're limited to 60 requests/hour. With it, 5,000/hour.
- The tool uses a **persistent disk cache** (`.rn_review_cache/github-prs-<version>.json`) so if you hit the rate limit, re-running the same command will skip already-fetched PRs.
- When rate-limited, the tool **saves partial progress** (both the cache and the review JSON) and exits with code 2. Simply re-run the same command to continue.
- Use `--cache-dir` to customize the cache location.

```bash
# First run — fetches 55 PRs, hits rate limit, saves cache + partial review JSON
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
python3 -m rn_review extract --version 1.36 --sig-release-dir ./sig-release --fetch-github

# Second run — skips the 55 cached PRs, fetches remaining 103
python3 -m rn_review extract --version 1.36 --sig-release-dir ./sig-release --fetch-github
```

### Map files not generated

- Ensure PRs are marked as `reviewDone: true` in the review JSON
- Ensure `currentDraftNote` differs from `originalNote`
- Use `--include-unreviewed` to generate maps for all modified PRs regardless of review status
- Use `--dry-run` to preview what would be generated

### Merge conflicts with existing review file

- Use `--merge` flag to add new PRs without overwriting existing reviews
- The tool automatically backs up the existing file as `.json.bak` before saving
