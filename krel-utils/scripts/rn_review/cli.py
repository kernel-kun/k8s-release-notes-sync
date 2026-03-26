"""CLI entry point for the release notes review utility.

Provides subcommands for extracting PRs, checking status,
and generating map files.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .config import (
    DEFAULT_GITHUB_OWNER,
    DEFAULT_GITHUB_REPO,
    build_maps_dir,
    build_notes_json_path,
    build_notes_md_path,
    get_github_token,
)
from .extractors.diff_extractor import (
    extract_diff_prs,
    extract_full_prs,
    extract_prs_from_file,
)
from .extractors.github_extractor import GitHubExtractor, RateLimitExhausted
from .extractors.json_extractor import DraftJSONData
from .map_generator import generate_map_files
from .models import PREntry
from .review_file import ReviewFileManager

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the CLI.

    Args:
        verbose: If True, set log level to DEBUG.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with all subcommands.

    Returns:
        Configured ArgumentParser.
    """
    parser = argparse.ArgumentParser(
        prog="rn-review",
        description="Kubernetes Release Notes Review Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract all PRs from local file
  rn-review extract --version 1.36 --sig-release-dir ./sig-release

  # Extract PRs from git diff
  rn-review extract --version 1.36 --sig-release-dir ./sig-release \\
      --mode diff --old-ref HEAD~3 --new-ref HEAD

  # Extract and fetch GitHub PR descriptions
  rn-review extract --version 1.36 --sig-release-dir ./sig-release \\
      --fetch-github

  # Check review progress
  rn-review status --review-file review-1.36.json

  # Generate map files for reviewed PRs
  rn-review generate-maps --review-file review-1.36.json \\
      --version 1.36 --sig-release-dir ./sig-release
        """,
    )
    parser.add_argument(
        "--version-info",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- extract subcommand ---
    extract_parser = subparsers.add_parser(
        "extract",
        help="Extract PRs and create review JSON file",
        description="Extract PR entries from release-notes-draft.md and "
                    "enrich with data from the JSON file and GitHub API.",
    )
    extract_parser.add_argument(
        "--version", "-V",
        required=True,
        dest="release_version",
        help="Kubernetes release version (e.g., 1.36)",
    )
    extract_parser.add_argument(
        "--sig-release-dir",
        required=True,
        help="Path to the sig-release repository directory",
    )
    extract_parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output path for the review JSON file "
             "(default: review-<version>.json in current directory)",
    )
    extract_parser.add_argument(
        "--mode",
        choices=["full", "diff"],
        default="full",
        help="Extraction mode: 'full' for all PRs, 'diff' for git diff "
             "(default: full)",
    )
    extract_parser.add_argument(
        "--old-ref",
        default="HEAD~",
        help="Old git ref for diff mode (default: HEAD~)",
    )
    extract_parser.add_argument(
        "--new-ref",
        default="HEAD",
        help="New git ref for diff mode (default: HEAD)",
    )
    extract_parser.add_argument(
        "--fetch-github",
        action="store_true",
        help="Fetch PR descriptions from GitHub API",
    )
    extract_parser.add_argument(
        "--github-owner",
        default=DEFAULT_GITHUB_OWNER,
        help=f"GitHub repo owner (default: {DEFAULT_GITHUB_OWNER})",
    )
    extract_parser.add_argument(
        "--github-repo",
        default=DEFAULT_GITHUB_REPO,
        help=f"GitHub repo name (default: {DEFAULT_GITHUB_REPO})",
    )
    extract_parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge new PRs into an existing review file instead of "
             "creating a new one",
    )
    extract_parser.add_argument(
        "--cache-dir",
        default=None,
        help="Directory for GitHub API disk cache "
             "(default: .rn_review_cache/ in current directory)",
    )

    # --- status subcommand ---
    status_parser = subparsers.add_parser(
        "status",
        help="Show review progress",
        description="Display review progress statistics from a review JSON file.",
    )
    status_parser.add_argument(
        "--review-file", "-f",
        required=True,
        help="Path to the review JSON file",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output status as JSON",
    )

    # --- generate-maps subcommand ---
    maps_parser = subparsers.add_parser(
        "generate-maps",
        help="Generate YAML map files for modified PRs",
        description="Generate krel-compatible map YAML files for PRs "
                    "where the note was modified during review.",
    )
    maps_parser.add_argument(
        "--review-file", "-f",
        required=True,
        help="Path to the review JSON file",
    )
    maps_parser.add_argument(
        "--version", "-V",
        dest="release_version",
        default=None,
        help="Kubernetes release version (used to determine output dir)",
    )
    maps_parser.add_argument(
        "--sig-release-dir",
        default=None,
        help="Path to the sig-release repository directory",
    )
    maps_parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory for map files (overrides auto-detection)",
    )
    maps_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing map files",
    )
    maps_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )
    maps_parser.add_argument(
        "--include-unreviewed",
        action="store_true",
        help="Include unreviewed PRs in map generation",
    )

    return parser


def cmd_extract(args: argparse.Namespace) -> int:
    """Execute the extract subcommand.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    sig_release_dir = args.sig_release_dir
    version = args.release_version
    output_path = args.output or f"review-{version}.json"

    # Build paths
    md_path = build_notes_md_path(sig_release_dir, version)
    json_path = build_notes_json_path(sig_release_dir, version)

    logger.info("Release version: %s", version)
    logger.info("Markdown path: %s", md_path)
    logger.info("JSON path: %s", json_path)

    # Step 1: Extract PR entries from markdown
    logger.info("Extracting PRs (mode: %s)...", args.mode)

    if args.mode == "diff":
        # For diff mode, we need the relative path within the repo
        rel_md_path = str(
            Path(md_path).relative_to(Path(sig_release_dir))
        )
        md_entries = extract_diff_prs(
            repo_dir=sig_release_dir,
            notes_path=rel_md_path,
            old_ref=args.old_ref,
            new_ref=args.new_ref,
        )
    else:
        md_entries = extract_prs_from_file(md_path)

    if not md_entries:
        logger.warning("No PR entries found. Nothing to extract.")
        return 0

    logger.info("Extracted %d PR entries from markdown", len(md_entries))

    # Step 2: Enrich with JSON data
    logger.info("Loading JSON data from %s...", json_path)
    try:
        json_data = DraftJSONData.from_file(json_path)
    except FileNotFoundError:
        logger.warning(
            "JSON file not found at %s. Proceeding without JSON enrichment.",
            json_path,
        )
        json_data = None

    # Step 3: Optionally fetch GitHub PR descriptions
    github_descriptions = {}
    rate_limited = False
    if args.fetch_github:
        token = get_github_token()
        cache_dir = args.cache_dir or ".rn_review_cache"
        cache_path = Path(cache_dir) / f"github-prs-{version}.json"

        extractor = GitHubExtractor(
            token=token,
            owner=args.github_owner,
            repo=args.github_repo,
            cache_path=cache_path,
        )

        pr_numbers = list(md_entries.keys())
        logger.info("Fetching %d PR descriptions from GitHub...", len(pr_numbers))
        logger.info("Disk cache: %s (%d entries)", cache_path, extractor.cache_size)

        def progress(current: int, total: int) -> None:
            if current % 10 == 0 or current == total:
                logger.info("  Progress: %d/%d", current, total)

        try:
            github_descriptions = extractor.fetch_prs(
                pr_numbers, progress_callback=progress
            )
        except RateLimitExhausted as e:
            logger.warning("%s", e)
            logger.warning(
                "Partial results will be saved. Re-run the same command "
                "to resume (cached PRs will be skipped)."
            )
            rate_limited = True
            # Use whatever we got from cache before the limit
            for pr_number in pr_numbers:
                if pr_number not in github_descriptions:
                    cached = extractor._disk_cache.get(pr_number) if extractor._disk_cache else None
                    if cached:
                        github_descriptions[pr_number] = cached

    # Step 4: Build PREntry objects
    #
    # Data source logic:
    #   - originalNote: The author's original release note text (immutable
    #     baseline). When --fetch-github is used, this comes from the
    #     GitHub PR body's ```release-note block. Without --fetch-github,
    #     falls back to the JSON text from krel.
    #   - currentDraftNote: The note as it currently appears in the
    #     markdown draft (what krel generated, possibly with map overrides).
    #     This is the field that gets edited during review.
    #
    pr_entries: list[PREntry] = []
    for pr_number, md_entry in md_entries.items():
        # Get JSON/metadata enrichment
        json_note = ""
        sigs: list[str] = []
        kinds: list[str] = []
        areas: list[str] = []
        author = ""
        pr_url = ""

        if json_data:
            json_note = json_data.get_text(pr_number)
            sigs = json_data.get_sigs(pr_number)
            kinds = json_data.get_kinds(pr_number)
            areas = json_data.get_areas(pr_number)
            author = json_data.get_author(pr_number)
            pr_url = json_data.get_pr_url(pr_number)

        # Use markdown text as the current draft note
        current_draft = md_entry.note_text

        # Get GitHub data (author's original release-note text)
        github_note = ""
        if pr_number in github_descriptions:
            gh_desc = github_descriptions[pr_number]
            github_note = gh_desc.user_facing_change
            if not author:
                author = gh_desc.author
            if not pr_url:
                pr_url = f"https://github.com/{args.github_owner}/{args.github_repo}/pull/{pr_number}"

        # Determine originalNote:
        # - If we have GitHub data, use the author's release-note text
        #   (this is the true "original" before krel/team modifications)
        # - Otherwise fall back to JSON text (krel's generated note)
        # - Last resort: use the markdown text
        if github_note:
            original_note = github_note
        elif json_note:
            original_note = json_note
        else:
            original_note = current_draft

        entry = PREntry(
            pr_number=pr_number,
            pr_url=pr_url or f"https://github.com/{args.github_owner}/{args.github_repo}/pull/{pr_number}",
            author=author,
            sigs=sigs,
            kinds=kinds,
            areas=areas,
            original_note=original_note,
            current_draft_note=current_draft,
        )
        pr_entries.append(entry)

    # Step 5: Create or merge review file
    manager = ReviewFileManager(output_path)

    if args.merge and Path(output_path).exists():
        logger.info("Merging into existing review file: %s", output_path)
        manager.load()
        added = manager.merge_new_prs(pr_entries)
        logger.info("Added %d new PRs", added)
    else:
        manager.create(
            pr_entries=pr_entries,
            release_version=version,
            extraction_mode=args.mode,
            old_ref=args.old_ref if args.mode == "diff" else "",
            new_ref=args.new_ref if args.mode == "diff" else "",
        )

    manager.save(backup=Path(output_path).exists())

    progress = manager.get_progress()
    logger.info(
        "Review file saved: %s (%d PRs)",
        output_path,
        progress["total"],
    )

    if rate_limited:
        logger.warning(
            "⚠ GitHub API rate limit was hit. Some PRs may have "
            "originalNote sourced from JSON instead of GitHub. Re-run "
            "the same extract command to resume fetching (cached PRs "
            "will be skipped automatically)."
        )
        return 2  # Partial success exit code

    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Execute the status subcommand.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    manager = ReviewFileManager(args.review_file)
    manager.load()

    progress = manager.get_progress()

    if args.json_output:
        print(json.dumps(progress, indent=2))
    else:
        total = progress["total"]
        reviewed = progress["reviewed"]
        pct = (reviewed / total * 100) if total > 0 else 0

        print(f"\n{'='*50}")
        print(f"  Release Notes Review Progress")
        print(f"{'='*50}")
        print(f"  Total PRs:        {total}")
        print(f"  Reviewed:         {reviewed} ({pct:.1f}%)")
        print(f"  Unreviewed:       {progress['unreviewed']}")
        print(f"  Modified:         {progress['modified']}")
        print(f"  Map candidates:   {progress['mapCandidates']}")
        print(f"{'='*50}\n")

    return 0


def cmd_generate_maps(args: argparse.Namespace) -> int:
    """Execute the generate-maps subcommand.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success).
    """
    manager = ReviewFileManager(args.review_file)
    manager.load()

    # Determine output directory
    if args.output_dir:
        output_dir = args.output_dir
    elif args.release_version and args.sig_release_dir:
        output_dir = build_maps_dir(args.sig_release_dir, args.release_version)
    else:
        logger.error(
            "Must specify either --output-dir or both --version and "
            "--sig-release-dir"
        )
        return 1

    data = manager.get_data()
    only_reviewed = not args.include_unreviewed

    logger.info("Generating map files in: %s", output_dir)
    if args.dry_run:
        logger.info("[DRY RUN MODE]")

    generated = generate_map_files(
        pr_entries=data["prs"],
        output_dir=output_dir,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        only_reviewed=only_reviewed,
    )

    if not args.dry_run:
        logger.info("Generated %d map files", len(generated))
    else:
        # In dry run, count candidates manually
        from .map_generator import pr_entry_to_map_data
        candidates = manager.get_map_candidates() if only_reviewed else manager.get_modified_prs()
        logger.info("Would generate %d map files", len(candidates))

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    setup_logging(verbose=args.verbose)

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "extract": cmd_extract,
        "status": cmd_status,
        "generate-maps": cmd_generate_maps,
    }

    handler = commands.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    try:
        return handler(args)
    except FileNotFoundError as e:
        logger.error("File not found: %s", e)
        return 1
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
