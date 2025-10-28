#!/usr/bin/env python3
"""
Kubernetes Release Notes Sync Tool

A tool to synchronize release notes across YAML map files, JSON, and Markdown files.
"""

import argparse
import os
import sys

from release_notes_sync.constants import (OUTPUT_CSV, OUTPUT_JSON,
                                          OUTPUT_TABLE, get_release_dir)
from release_notes_sync.formatter import (colorize, format_diff_section,
                                          format_pr_sync_header,
                                          format_sync_summary,
                                          format_validation_csv,
                                          format_validation_json,
                                          format_validation_table)
from release_notes_sync.git_helper import (get_changed_pr_numbers, is_git_repo,
                                           validate_commit_reference)
from release_notes_sync.sync_engine import sync_pr
from release_notes_sync.validator import (has_validation_issues,
                                          validate_all_prs)


def display_validation_results(results: dict, output_format: str):
    """
    Display validation results in the specified format.

    Args:
        results: Validation results dictionary
        output_format: Output format (table, json, csv)
    """
    if output_format == OUTPUT_JSON:
        print(format_validation_json(results))
    elif output_format == OUTPUT_CSV:
        print(format_validation_csv(results))
    else:  # table (default)
        print(format_validation_table(results))


def interactive_sync_approval(pr_number: str, diffs: list) -> bool:
    """
    Show diffs to user and get approval for syncing.

    Args:
        pr_number: PR number being synced
        diffs: List of diff dictionaries

    Returns:
        True if user approves, False otherwise
    """
    # Show all diffs
    for i, diff_info in enumerate(diffs, 1):
        print(format_diff_section(i, len(diffs), diff_info["type"], diff_info["diff"]))

    # Prompt for approval
    while True:
        response = (
            input(colorize(f"Apply changes for PR #{pr_number}? [y/n/q]: ", "cyan"))
            .lower()
            .strip()
        )

        if response == "y":
            return True
        elif response == "n":
            return False
        elif response == "q":
            print(colorize("\nSync cancelled by user", "yellow"))
            sys.exit(0)
        else:
            print("Please enter 'y' for yes, 'n' for no, or 'q' to quit")


def handle_validate_command(args):
    """
    Handle the validate command.

    Args:
        args: Parsed command line arguments
    """
    release_version = args.release
    repo_root = getattr(args, "repo_root", None)

    # Check if release directory exists
    release_dir = get_release_dir(release_version, repo_root)
    if not os.path.exists(release_dir):
        print(colorize(f"Error: Release directory not found: {release_dir}", "red"))
        sys.exit(1)

    # Determine which PRs to validate
    pr_numbers = None

    if hasattr(args, "prs") and args.prs:
        # Specific PRs provided
        pr_numbers = args.prs.split(",")
        print(f"Validating {len(pr_numbers)} specific PRs...")
    elif hasattr(args, "since_commit") and args.since_commit:
        # Get PRs changed since commit
        if not is_git_repo(repo_root):
            print(colorize("Error: Not a git repository", "red"))
            sys.exit(1)

        if not validate_commit_reference(args.since_commit, repo_root):
            print(
                colorize(f"Error: Invalid commit reference: {args.since_commit}", "red")
            )
            sys.exit(1)

        pr_numbers = get_changed_pr_numbers(
            args.since_commit, release_version, repo_root
        )
        print(
            f"Found {len(pr_numbers)} changed map files since commit {args.since_commit}"
        )

        if not pr_numbers:
            print(colorize("No changed map files found", "yellow"))
            return
    elif args.global_mode:
        # Validate all PRs
        print(f"Validating all PRs in release {release_version}...")
    else:
        print(colorize("Error: Must specify --since-commit, --prs, or --global", "red"))
        sys.exit(1)

    # Run validation
    results = validate_all_prs(release_version, pr_numbers, repo_root)

    # Display results
    output_format = getattr(args, "output", OUTPUT_TABLE)
    display_validation_results(results, output_format)

    # Exit with error code if issues found
    if has_validation_issues(results):
        sys.exit(1)


def handle_sync_command(args):
    """
    Handle the sync command.

    Args:
        args: Parsed command line arguments
    """
    release_version = args.release
    repo_root = getattr(args, "repo_root", None)
    auto_approve = getattr(args, "auto_yes", False)
    dry_run = getattr(args, "dry_run", False)

    # Check if release directory exists
    release_dir = get_release_dir(release_version, repo_root)
    if not os.path.exists(release_dir):
        print(colorize(f"Error: Release directory not found: {release_dir}", "red"))
        sys.exit(1)

    # Skip uncommitted changes check for large repos (can be slow)
    # Users should manage their git state manually
    # if not dry_run and has_uncommitted_changes(repo_root):
    #     print(colorize("Warning: You have uncommitted changes", 'yellow'))
    #     response = input("Continue anyway? [y/n]: ").lower().strip()
    #     if response != 'y':
    #         print("Sync cancelled")
    #         return

    # Determine which PRs to sync
    pr_numbers = None

    if hasattr(args, "prs") and args.prs:
        # Specific PRs provided
        pr_numbers = args.prs.split(",")
        print(f"Syncing {len(pr_numbers)} specific PRs...")
    elif hasattr(args, "since_commit") and args.since_commit:
        # Get PRs changed since commit
        if not is_git_repo(repo_root):
            print(colorize("Error: Not a git repository", "red"))
            sys.exit(1)

        if not validate_commit_reference(args.since_commit, repo_root):
            print(
                colorize(f"Error: Invalid commit reference: {args.since_commit}", "red")
            )
            sys.exit(1)

        pr_numbers = get_changed_pr_numbers(
            args.since_commit, release_version, repo_root
        )
        print(
            f"Found {len(pr_numbers)} changed map files since commit {args.since_commit}"
        )

        if not pr_numbers:
            print(colorize("No changed map files found", "yellow"))
            return
    elif args.global_mode:
        # Get all PRs that need syncing
        from release_notes_sync.constants import get_maps_dir
        from release_notes_sync.file_loader import (
            extract_pr_number_from_filename, get_all_map_files)

        maps_dir = get_maps_dir(release_version, repo_root)
        map_files = get_all_map_files(maps_dir)
        pr_numbers = [
            extract_pr_number_from_filename(os.path.basename(f)) for f in map_files
        ]
        pr_numbers = [pr for pr in pr_numbers if pr]

        print(f"Syncing all PRs in release {release_version}...")
        print(colorize("Warning: This will process all map files", "yellow"))
        if not auto_approve and not dry_run:
            response = input("Continue? [y/n]: ").lower().strip()
            if response != "y":
                print("Sync cancelled")
                return
    else:
        print(colorize("Error: Must specify --since-commit, --prs, or --global", "red"))
        sys.exit(1)

    if dry_run:
        print(
            colorize("\n=== DRY RUN MODE - No changes will be applied ===\n", "yellow")
        )

    # Sync PRs
    sync_results = []

    for pr_num in pr_numbers:
        try:
            # First, get the sync details
            result = sync_pr(
                pr_num,
                release_version,
                auto_approve=False,
                dry_run=True,
                repo_root=repo_root,
            )

            # If there's an error, report it
            if result.get("error"):
                print(colorize(f"Error with PR #{pr_num}: {result['error']}", "red"))
                sync_results.append(result)
                continue

            # If no changes needed, skip
            if not result["changes_needed"]:
                print(f"PR #{pr_num}: No changes needed")
                sync_results.append(result)
                continue

            # Show the sync header and diffs
            from release_notes_sync.constants import get_map_file

            map_file = get_map_file(pr_num, release_version, repo_root)
            print(format_pr_sync_header(pr_num, map_file))

            # Get approval (if needed)
            approved = True
            if not auto_approve and not dry_run:
                approved = interactive_sync_approval(pr_num, result["diffs"])

            if not approved:
                result["user_approved"] = False
                print(colorize(f"Skipped PR #{pr_num}", "yellow"))
                sync_results.append(result)
                continue

            # Apply changes (if not dry-run)
            if not dry_run:
                result = sync_pr(
                    pr_num,
                    release_version,
                    auto_approve=True,
                    dry_run=False,
                    repo_root=repo_root,
                )

                if result["changes_made"]:
                    print(colorize(f"✓ Changes applied for PR #{pr_num}", "green"))
                else:
                    print(
                        colorize(f"✗ Failed to apply changes for PR #{pr_num}", "red")
                    )
            else:
                # In dry-run, just show what would happen
                for diff_info in result["diffs"]:
                    print(
                        format_diff_section(
                            result["diffs"].index(diff_info) + 1,
                            len(result["diffs"]),
                            diff_info["type"],
                            diff_info["diff"],
                        )
                    )

            sync_results.append(result)

        except KeyboardInterrupt:
            print(colorize("\n\nSync interrupted by user", "yellow"))
            break
        except Exception as e:
            print(colorize(f"Error syncing PR #{pr_num}: {e}", "red"))
            sync_results.append(
                {"pr_number": pr_num, "error": str(e), "changes_made": False}
            )

    # Display summary
    print(format_sync_summary(sync_results))


def main():
    """Main entry point for the CLI tool."""
    parser = argparse.ArgumentParser(
        description="Kubernetes Release Notes Sync Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate changes since last commit
  %(prog)s validate --since-commit HEAD~1 --release 1.35

  # Sync changes interactively
  %(prog)s sync --since-commit HEAD~1 --release 1.35

  # Validate specific PRs
  %(prog)s validate --prs 133540,132549 --release 1.35

  # Validate entire release
  %(prog)s validate --global --release 1.35

  # Dry-run sync to see what would change
  %(prog)s sync --since-commit HEAD~1 --release 1.35 --dry-run
""",
    )

    # Common arguments
    parser.add_argument(
        "--repo-root",
        help="Repository root path (default: current directory)",
        default=None,
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Validate command
    validate_parser = subparsers.add_parser(
        "validate", help="Validate consistency across map files, JSON, and Markdown"
    )
    validate_parser.add_argument(
        "--release", required=True, help="Release version (e.g., 1.35)"
    )
    validate_parser.add_argument(
        "--since-commit", help="Validate files changed since this commit"
    )
    validate_parser.add_argument(
        "--prs", help="Comma-separated list of PR numbers to validate"
    )
    validate_parser.add_argument(
        "--global",
        action="store_true",
        dest="global_mode",
        help="Validate all map files in the release",
    )
    validate_parser.add_argument(
        "--output",
        choices=[OUTPUT_TABLE, OUTPUT_JSON, OUTPUT_CSV],
        default=OUTPUT_TABLE,
        help="Output format (default: table)",
    )

    # Sync command
    sync_parser = subparsers.add_parser(
        "sync", help="Synchronize changes from map files to JSON and Markdown"
    )
    sync_parser.add_argument(
        "--release", required=True, help="Release version (e.g., 1.35)"
    )
    sync_parser.add_argument(
        "--since-commit", help="Sync files changed since this commit"
    )
    sync_parser.add_argument("--prs", help="Comma-separated list of PR numbers to sync")
    sync_parser.add_argument(
        "--global",
        action="store_true",
        dest="global_mode",
        help="Sync all map files in the release",
    )
    sync_parser.add_argument(
        "--auto-yes", action="store_true", help="Skip all confirmations (dangerous!)"
    )
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without applying changes",
    )

    # Parse arguments
    args = parser.parse_args()

    # Execute command
    try:
        if args.command == "validate":
            handle_validate_command(args)
        elif args.command == "sync":
            handle_sync_command(args)
    except KeyboardInterrupt:
        print(colorize("\n\nOperation cancelled by user", "yellow"))
        sys.exit(130)
    except Exception as e:
        print(colorize(f"\nError: {e}", "red"))
        sys.exit(1)


if __name__ == "__main__":
    main()
