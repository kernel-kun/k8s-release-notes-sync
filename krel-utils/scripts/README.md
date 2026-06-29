# Release-notes scripts

Helper scripts used during the Kubernetes release cycle to audit and sync the
release-notes map files, drafts, and PR coverage.

Each script is self-contained: it declares its own Python dependencies inline
([PEP 723](https://peps.python.org/pep-0723/)) and runs under
[`uv`](https://docs.astral.sh/uv/). There is no virtualenv to create and no
`requirements.txt` to install — `uv` builds a cached per-script environment the
first time you run a script, and reuses it after that.

## Prerequisites

- [**devbox**](https://www.jetify.com/devbox) — provides `uv`, `git`, and `gh`
  without installing them globally.
- [**direnv**](https://direnv.net/) — auto-enters the devbox shell when you
  `cd` into this directory (optional but recommended).

Everything else (`uv` itself, the Python interpreter, each script's libraries)
is handled for you.

## Bootstrap (once)

```bash
cd krel-utils/scripts

# Option A — direnv (auto-loads on every cd into this dir)
direnv allow

# Option B — manual devbox shell
devbox shell

# Warm the dependency caches so the first real run is instant (optional)
devbox run warmup
```

After this, the environment is set up for good. `gh` needs to be authenticated
once (`gh auth login`) for the PR-lookup scripts.

## Running a script

Either form works — they're identical:

```bash
./show_release_notes.py v1.37.0-alpha.1 v1.37.0-alpha.2
# or
uv run --script show_release_notes.py v1.37.0-alpha.1 v1.37.0-alpha.2
```

`uv` resolves the inline dependencies on the first run and caches them; later
runs start immediately. Pass `--help` to any script for full options.

## The scripts

| Script | Purpose | Deps |
| --- | --- | --- |
| `show_release_notes.py` | Lists the \`\`\`release-note \`\`\` block of every PR merged between two git refs, flagging ones krel may have missed. | `rich` |
| `review_release_notes_diff.py` | Diffs two versions of a `release-notes-draft.md` and reports removed/modified/reordered/added PRs plus style violations. | stdlib |
| `sync_map_fields.py` | Syncs `sigs`/`kinds`/`areas` from `release-notes-draft.json` back into the per-PR map YAML files. | `ruamel.yaml` |
| `sync_release_note_text.py` | Syncs changed `.text` fields from `release-notes-draft.json` between two git refs back to map files. | `pyyaml` |
| `compare_pr_numbers.py` | Cross-checks PR numbers across map files, the draft JSON/MD, and session files for a release. | stdlib |
| `compress_release_notes_json.py` | Strips a release-notes JSON down to PR number, text, and URL. | stdlib |

### Common usage

```bash
# Find PRs with a release note that krel didn't pick up, for a tag range:
./show_release_notes.py --live-dir \
    ../../sig-release/releases/release-1.37/release-notes \
    v1.37.0-alpha.1 v1.37.0-alpha.2

# Review what changed between successive draft branches:
./review_release_notes_diff.py --repo-dir /path/to/sig-release \
    --old-ref release-notes-draft-v1.37.0-alpha.1 \
    --new-ref release-notes-draft-v1.37.0-alpha.2

# Push edited sigs/kinds/areas from the draft JSON back into the map files:
./sync_map_fields.py 1.37            # add --dry-run to preview

# Push edited release-note text from the draft JSON back into the map files:
./sync_release_note_text.py HEAD~1 HEAD --dry-run

# Sanity-check PR coverage for a release:
./compare_pr_numbers.py 1.37

# Compress a release-notes JSON to the essential fields:
./compress_release_notes_json.py input.json compressed.json
```

> The `rn_review/` subfolder is managed separately and is not covered here.
