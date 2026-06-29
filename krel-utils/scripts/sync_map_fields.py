#!/usr/bin/env python3
"""
Sync sigs, kinds, and areas fields from release-notes-draft.json back into
individual PR map YAML files.

Usage:
    python sync_map_fields.py 1.36
    python sync_map_fields.py 1.36 --dry-run
    python sync_map_fields.py 1.36 --repo-root /path/to/repo

Dependencies: ruamel.yaml (preferred) or PyYAML (fallback, may alter formatting)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Try ruamel.yaml first for round-trip fidelity, fall back to PyYAML
try:
    from ruamel.yaml import YAML

    _YAML_ENGINE = "ruamel"
except ImportError:
    try:
        import yaml

        _YAML_ENGINE = "pyyaml"
    except ImportError:
        print(
            "❌ Neither ruamel.yaml nor PyYAML is installed.\n"
            "   Install one with: pip install ruamel.yaml   (recommended)\n"
            "                 or: pip install pyyaml"
        )
        sys.exit(1)

SYNC_FIELDS = ("sigs", "kinds", "areas")
MAP_PATTERN = re.compile(r"^pr-(\d+)-map\.ya?ml$")


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def _load_yaml(path: Path):
    """Load a YAML file and return the parsed data."""
    if _YAML_ENGINE == "ruamel":
        yml = YAML()
        yml.preserve_quotes = True
        with open(path, "r", encoding="utf-8") as f:
            return yml.load(f)
    else:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)


def _dump_yaml(data, path: Path):
    """Write data back to a YAML file."""
    if _YAML_ENGINE == "ruamel":
        yml = YAML()
        yml.preserve_quotes = True
        yml.default_flow_style = False
        with open(path, "w", encoding="utf-8") as f:
            yml.dump(data, f)
    else:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(
                data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def detect_repo_root() -> Path:
    """Auto-detect the git repo root."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Could not detect repo root via git. Use --repo-root to specify it.")
        sys.exit(1)


def discover_map_files(maps_dir: Path) -> list[tuple[Path, int]]:
    """Return a sorted list of (path, pr_number) for all map files."""
    results = []
    for entry in sorted(maps_dir.iterdir()):
        m = MAP_PATTERN.match(entry.name)
        if m:
            results.append((entry, int(m.group(1))))
    return results


def compute_field_diff(
    map_releasenote: dict,
    json_entry: dict,
) -> dict[str, dict]:
    """Compute per-field diff between map and JSON for SYNC_FIELDS.

    Returns a dict of field -> {"old": list, "new": list} for fields that differ.
    Empty dict means no changes needed.
    """
    changes: dict[str, dict] = {}
    for field in SYNC_FIELDS:
        old = sorted(map_releasenote.get(field) or [])
        new = sorted(json_entry.get(field) or [])
        if old != new:
            changes[field] = {"old": old, "new": new}
    return changes


def apply_changes(map_data: dict, json_entry: dict) -> None:
    """Mutate map_data's releasenote section to match JSON fields."""
    rn = map_data.get("releasenote", {})
    for field in SYNC_FIELDS:
        json_val = json_entry.get(field) or []
        if json_val:
            rn[field] = list(json_val)
        else:
            rn.pop(field, None)


def format_diff(field: str, diff: dict) -> str:
    """Format a single field diff for display."""
    added = set(diff["new"]) - set(diff["old"])
    removed = set(diff["old"]) - set(diff["new"])
    parts = []
    if added:
        parts.append(f"+[{', '.join(sorted(added))}]")
    if removed:
        parts.append(f"-[{', '.join(sorted(removed))}]")
    if not parts:
        # Order changed only
        parts.append("reordered")
    return f"  {field}: {' '.join(parts)}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sync sigs/kinds/areas from release-notes-draft.json into map files.",
    )
    parser.add_argument(
        "release_version",
        help="Release version, e.g. 1.36",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files",
    )
    parser.add_argument(
        "--clear-pr-body",
        action="store_true",
        help='Also set the top-level pr_body field to "" in each map file',
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (auto-detected if omitted)",
    )
    args = parser.parse_args()

    if _YAML_ENGINE == "pyyaml":
        print("⚠️  Using PyYAML fallback — file formatting may change. Install ruamel.yaml for round-trip fidelity.")

    repo_root = args.repo_root or detect_repo_root()
    release_dir = repo_root / "releases" / f"release-{args.release_version}" / "release-notes"
    maps_dir = release_dir / "maps"
    json_file = release_dir / "release-notes-draft.json"

    # Validate paths
    if not release_dir.is_dir():
        print(f"❌ Release directory not found: {release_dir}")
        sys.exit(1)
    if not maps_dir.is_dir():
        print(f"❌ Maps directory not found: {maps_dir}")
        sys.exit(1)
    if not json_file.is_file():
        print(f"❌ JSON file not found: {json_file}")
        sys.exit(1)

    # Load JSON
    with open(json_file, "r", encoding="utf-8") as f:
        draft_json: dict = json.load(f)

    # Discover map files
    map_files = discover_map_files(maps_dir)

    mode = "DRY RUN" if args.dry_run else "SYNC"
    print(f"🔄 [{mode}] Syncing map fields for release-{args.release_version}")
    print(f"   Maps: {maps_dir} ({len(map_files)} files)")
    print(f"   JSON: {json_file}")
    print()

    updated = 0
    unchanged = 0
    warnings = 0

    for map_path, pr_number in map_files:
        pr_key = str(pr_number)

        if pr_key not in draft_json:
            print(f"⚠️  PR #{pr_number}: not found in JSON — skipping")
            warnings += 1
            continue

        json_entry = draft_json[pr_key]
        map_data = _load_yaml(map_path)

        if map_data is None:
            print(f"⚠️  PR #{pr_number}: could not parse {map_path.name} — skipping")
            warnings += 1
            continue

        rn = map_data.get("releasenote", {})
        diff = compute_field_diff(rn, json_entry)
        clear_body = args.clear_pr_body and map_data.get("pr_body") != ""

        if not diff and not clear_body:
            unchanged += 1
            continue

        # Report changes
        print(f"📝 PR #{pr_number} ({map_path.name}):")
        for field, field_diff in diff.items():
            print(format_diff(field, field_diff))
        if clear_body:
            print('  pr_body: -> ""')

        if not args.dry_run:
            apply_changes(map_data, json_entry)
            if clear_body:
                map_data["pr_body"] = ""
            _dump_yaml(map_data, map_path)

        updated += 1

    # Summary
    print()
    label = "Would update" if args.dry_run else "Updated"
    print(
        f"✅ Processed {len(map_files)} maps: "
        f"{updated} {label.lower()}, {unchanged} unchanged, {warnings} warnings"
    )


if __name__ == "__main__":
    main()
