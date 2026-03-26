"""YAML map file generation for krel compatibility.

Generates map files in the format expected by krel's ReleaseNotesMap
parser. Only creates maps for PRs where the note was modified from
the original and review is complete.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .models import MapFileData, PRReviewEntry

logger = logging.getLogger(__name__)


def pr_entry_to_map_data(pr: PRReviewEntry) -> MapFileData:
    """Convert a PRReviewEntry to MapFileData for YAML generation.

    Args:
        pr: The PR review entry.

    Returns:
        MapFileData ready for YAML serialization.
    """
    return MapFileData(
        pr_number=pr["prNumber"],
        text=pr.get("currentDraftNote", ""),
        sigs=pr.get("sigs", []),
        kinds=pr.get("kinds", []),
        areas=pr.get("areas", []),
        pr_body="",
    )


def format_map_yaml(data: MapFileData) -> str:
    """Format a MapFileData object as YAML string.

    Produces YAML compatible with krel's ReleaseNotesMap parser.
    Uses block scalar style (|-) for multi-line text and explicit
    list format for sigs/kinds/areas.

    The output format matches existing map files in the repository:
        pr: <number>
        releasenote:
          text: |-
            <content>
          sigs:
          - <sig>
          kinds:
          - <kind>
          areas:
          - <area>
        pr_body: ""

    Args:
        data: The map file data.

    Returns:
        Formatted YAML string.
    """
    lines: list[str] = []

    # PR number
    lines.append(f"pr: {data.pr_number}")

    # Release note block
    lines.append("releasenote:")

    # Text field — use block scalar (|-) for clean multi-line support
    text = data.text.rstrip()
    if "\n" in text:
        lines.append("  text: |-")
        for text_line in text.split("\n"):
            lines.append(f"    {text_line}")
    else:
        # Single line — still use block scalar for consistency
        lines.append("  text: |-")
        lines.append(f"    {text}")

    # SIGs
    if data.sigs:
        lines.append("  sigs:")
        for sig in data.sigs:
            lines.append(f"  - {sig}")
    else:
        lines.append("  sigs: []")

    # Kinds
    if data.kinds:
        lines.append("  kinds:")
        for kind in data.kinds:
            lines.append(f"  - {kind}")
    else:
        lines.append("  kinds: []")

    # Areas
    if data.areas:
        lines.append("  areas:")
        for area in data.areas:
            lines.append(f"  - {area}")
    else:
        lines.append("  areas: []")

    # PR body — always empty per convention
    lines.append('pr_body: ""')

    return "\n".join(lines) + "\n"


def generate_map_file(
    data: MapFileData,
    output_dir: str | Path,
    overwrite: bool = False,
    dry_run: bool = False,
) -> Path | None:
    """Generate a single map YAML file.

    Args:
        data: The map file data.
        output_dir: Directory to write the map file to.
        overwrite: If True, overwrite existing map files.
        dry_run: If True, don't actually write files.

    Returns:
        Path to the written file, or None if skipped/dry-run.
    """
    output_path = Path(output_dir)
    file_name = f"pr-{data.pr_number}-map.yaml"
    file_path = output_path / file_name

    yaml_content = format_map_yaml(data)

    if dry_run:
        logger.info("[DRY RUN] Would write %s", file_path)
        logger.debug("Content:\n%s", yaml_content)
        return None

    if file_path.exists() and not overwrite:
        logger.warning(
            "Map file already exists: %s (use --overwrite to replace)",
            file_path,
        )
        return None

    output_path.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(yaml_content)

    logger.info("Generated map file: %s", file_path)
    return file_path


def generate_map_files(
    pr_entries: list[PRReviewEntry],
    output_dir: str | Path,
    overwrite: bool = False,
    dry_run: bool = False,
    only_reviewed: bool = True,
) -> list[Path]:
    """Generate map files for all modified PRs.

    Only generates maps for PRs where currentDraftNote differs from
    originalNote. Optionally filters to only reviewed PRs.

    Args:
        pr_entries: List of PR review entries.
        output_dir: Directory to write map files to.
        overwrite: If True, overwrite existing map files.
        dry_run: If True, don't actually write files.
        only_reviewed: If True, only generate maps for reviewed PRs.

    Returns:
        List of paths to generated map files.
    """
    generated: list[Path] = []
    skipped = 0
    unchanged = 0

    for pr in pr_entries:
        # Skip if note wasn't modified
        original = pr.get("originalNote", "")
        current = pr.get("currentDraftNote", "")
        if original == current:
            unchanged += 1
            continue

        # Skip if not reviewed (when only_reviewed is True)
        if only_reviewed and not pr.get("reviewDone", False):
            skipped += 1
            logger.debug(
                "Skipping PR #%d: not yet reviewed", pr["prNumber"]
            )
            continue

        map_data = pr_entry_to_map_data(pr)
        result = generate_map_file(
            map_data,
            output_dir,
            overwrite=overwrite,
            dry_run=dry_run,
        )

        if result is not None:
            generated.append(result)

    logger.info(
        "Map generation complete: %d generated, %d unchanged, %d skipped (unreviewed)",
        len(generated),
        unchanged,
        skipped,
    )

    return generated
