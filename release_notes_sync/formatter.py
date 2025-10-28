"""
Output formatting utilities for validation and sync results.
"""

import csv
import io
import json
import os
import subprocess
import tempfile
from typing import Dict, List

from colorama import Fore, Style
from colorama import init as colorama_init

from .constants import SYMBOL_CHECK, SYMBOL_CROSS, SYMBOL_WARNING

# Initialize colorama for cross-platform colored output
colorama_init(autoreset=True)


def colorize(text: str, color: str) -> str:
    """
    Add ANSI color codes to text.

    Args:
        text: Text to colorize
        color: Color name (green, red, yellow, blue)

    Returns:
        Colored text string
    """
    color_map = {
        "green": Fore.GREEN,
        "red": Fore.RED,
        "yellow": Fore.YELLOW,
        "blue": Fore.BLUE,
        "cyan": Fore.CYAN,
        "magenta": Fore.MAGENTA,
    }

    color_code = color_map.get(color.lower(), "")
    return f"{color_code}{text}{Style.RESET_ALL}"


def format_validation_table(results: Dict[str, List]) -> str:
    """
    Format validation results as a table.

    Args:
        results: Dictionary with categorized validation results

    Returns:
        Formatted table string
    """
    output = []

    # Header
    output.append(colorize("=" * 70, "blue"))
    output.append(colorize("VALIDATION RESULTS", "blue"))
    output.append(colorize("=" * 70, "blue"))
    output.append("")

    # Summary counts
    correct_count = len(results.get("correct", []))
    incorrect_count = len(results.get("incorrect", []))
    missing_json_count = len(results.get("missing_json", []))
    missing_md_count = len(results.get("missing_md", []))
    error_count = len(results.get("errors", []))

    output.append("Summary:")
    output.append(f"  {colorize('✓ Correct:', 'green')} {correct_count}")
    output.append(f"  {colorize('✗ Incorrect:', 'red')} {incorrect_count}")
    output.append(f"  {colorize('⚠ Missing in JSON:', 'yellow')} {missing_json_count}")
    output.append(f"  {colorize('⚠ Missing in MD:', 'yellow')} {missing_md_count}")
    if error_count > 0:
        output.append(f"  {colorize('⚠ Errors:', 'yellow')} {error_count}")
    output.append("")

    # Correct entries (just list)
    if correct_count > 0:
        output.append(
            colorize(f"{SYMBOL_CHECK} CORRECT ({correct_count} entries)", "green")
        )
        for result in results["correct"][:10]:  # Show first 10
            output.append(f"  PR #{result.pr_number}: All fields match")
        if correct_count > 10:
            output.append(f"  ... and {correct_count - 10} more")
        output.append("")

    # Incorrect entries (detailed)
    if incorrect_count > 0:
        output.append(
            colorize(f"{SYMBOL_CROSS} INCORRECT ({incorrect_count} entries)", "red")
        )
        for result in results["incorrect"]:
            output.append(f"  PR #{result.pr_number}:")
            if not result.map_json_match:
                output.append(f"    - JSON text: {colorize('MISMATCH', 'red')}")
            if not result.json_md_match:
                output.append(f"    - JSON markdown: {colorize('MISMATCH', 'red')}")
            if not result.md_file_match:
                output.append(f"    - MD file: {colorize('MISMATCH', 'red')}")
        output.append("")

    # Missing entries
    if missing_json_count > 0:
        output.append(
            colorize(
                f"{SYMBOL_WARNING} MISSING IN JSON ({missing_json_count} entries)",
                "yellow",
            )
        )
        for result in results["missing_json"]:
            output.append(f"  PR #{result.pr_number}: Exists in map but not in JSON")
        output.append("")

    if missing_md_count > 0:
        output.append(
            colorize(
                f"{SYMBOL_WARNING} MISSING IN MD ({missing_md_count} entries)", "yellow"
            )
        )
        for result in results["missing_md"]:
            output.append(
                f"  PR #{result.pr_number}: Exists in JSON but not in MD file"
            )
        output.append("")

    # Errors
    if error_count > 0:
        output.append(
            colorize(f"{SYMBOL_WARNING} ERRORS ({error_count} entries)", "yellow")
        )
        for error in results["errors"]:
            output.append(f"  PR #{error['pr_number']}: {error['error']}")
        output.append("")

    return "\n".join(output)


def format_validation_csv(results: Dict[str, List]) -> str:
    """
    Format validation results as CSV.

    Args:
        results: Dictionary with categorized validation results

    Returns:
        CSV formatted string
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(
        [
            "PR Number",
            "Map Exists",
            "JSON Exists",
            "MD Exists",
            "Map-JSON Match",
            "JSON-MD Match",
            "MD File Match",
            "Status",
        ]
    )

    # All results
    for category in ["correct", "incorrect", "missing_json", "missing_md"]:
        for result in results.get(category, []):
            writer.writerow(
                [
                    result.pr_number,
                    result.map_exists,
                    result.json_exists,
                    result.md_exists,
                    result.map_json_match,
                    result.json_md_match,
                    result.md_file_match,
                    result.status,
                ]
            )

    return output.getvalue()


def format_validation_json(results: Dict[str, List]) -> str:
    """
    Format validation results as JSON.

    Args:
        results: Dictionary with categorized validation results

    Returns:
        JSON formatted string
    """
    output = {
        "summary": {
            "correct": len(results.get("correct", [])),
            "incorrect": len(results.get("incorrect", [])),
            "missing_json": len(results.get("missing_json", [])),
            "missing_md": len(results.get("missing_md", [])),
            "errors": len(results.get("errors", [])),
        },
        "results": {},
    }

    for category in ["correct", "incorrect", "missing_json", "missing_md"]:
        output["results"][category] = [
            result.to_dict() for result in results.get(category, [])
        ]

    output["results"]["errors"] = results.get("errors", [])

    return json.dumps(output, indent=2)


def format_sync_summary(sync_results: List[Dict]) -> str:
    """
    Format sync operation summary.

    Args:
        sync_results: List of sync result dictionaries

    Returns:
        Formatted summary string
    """
    output = []

    output.append("")
    output.append(colorize("=" * 70, "blue"))
    output.append(colorize("SYNC COMPLETE", "blue"))
    output.append(colorize("=" * 70, "blue"))
    output.append("")

    applied = [
        r for r in sync_results if r.get("changes_made") and r.get("user_approved")
    ]
    skipped = [r for r in sync_results if not r.get("changes_made")]
    rejected = [
        r for r in sync_results if r.get("changes_made") and not r.get("user_approved")
    ]

    output.append(f"Changes Applied: {colorize(str(len(applied)), 'green')} PRs")
    output.append(f"No Changes Needed: {len(skipped)} PRs")
    output.append(f"Skipped by User: {len(rejected)} PRs")
    output.append("")

    if applied:
        output.append("Applied Changes:")
        for result in applied:
            output.append(f"  {colorize('✓', 'green')} PR #{result['pr_number']}")

    if rejected:
        output.append("")
        output.append("Skipped by User:")
        for result in rejected:
            output.append(f"  - PR #{result['pr_number']}")

    output.append("")
    output.append("Next Steps:")
    output.append("  1. Review changes: git diff")
    output.append(
        "  2. Commit changes: git add . && git commit -m 'sync: Update release notes'"
    )
    output.append("")

    return "\n".join(output)


def format_pr_sync_header(pr_number: str, map_file: str) -> str:
    """
    Format header for a PR sync operation.

    Args:
        pr_number: PR number
        map_file: Path to map file

    Returns:
        Formatted header string
    """
    output = []
    output.append("")
    output.append(colorize("=" * 70, "blue"))
    output.append(colorize(f"Syncing PR #{pr_number}", "blue"))
    output.append(colorize("=" * 70, "blue"))
    output.append("")
    output.append(f"Map file: {map_file}")
    output.append("")
    return "\n".join(output)


def format_diff_section(
    diff_num: int, total_diffs: int, diff_type: str, diff_content: str
) -> str:
    """
    Format a diff section for display using git's word-level highlighting.

    Args:
        diff_num: Current diff number
        total_diffs: Total number of diffs
        diff_type: Type of diff (e.g., "JSON text field")
        diff_content: Diff content (unified diff format)

    Returns:
        Formatted diff section with word-level highlighting from git
    """
    output = []
    output.append(colorize(f"[DIFF {diff_num}/{total_diffs}] {diff_type}:", "cyan"))

    # Use git diff for word-level highlighting
    word_diff = generate_git_word_diff(diff_content)
    output.append(word_diff)
    output.append("")

    return "\n".join(output)


def generate_git_word_diff(diff_content: str) -> str:
    """
    Generate word-level diff using git diff --color-words.

    This preserves git's ANSI color codes for character-level highlighting.

    Args:
        diff_content: Unified diff content

    Returns:
        Colored word-diff output with word-level highlighting
    """
    try:
        # Extract old and new content from unified diff
        lines = diff_content.split("\n")
        old_lines = []
        new_lines = []

        for line in lines:
            if line.startswith("-") and not line.startswith("---"):
                old_lines.append(line[1:])
            elif line.startswith("+") and not line.startswith("+++"):
                new_lines.append(line[1:])

        # If no content, just show the headers
        if not old_lines and not new_lines:
            return diff_content

        old_text = "\n".join(old_lines) if old_lines else " "
        new_text = "\n".join(new_lines) if new_lines else " "

        # Create temporary files
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt", encoding="utf-8"
        ) as f:
            f.write(old_text)
            old_path = f.name

        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt", encoding="utf-8"
        ) as f:
            f.write(new_text)
            new_path = f.name

        try:
            # Use git diff with character-level highlighting
            # --word-diff-regex=. highlights each character individually
            # --ws-error-highlight=all shows whitespace changes
            result = subprocess.run(
                [
                    "git",
                    "diff",
                    "--no-index",
                    "--color=always",
                    "--word-diff=color",
                    "--word-diff-regex=.",
                    "--ws-error-highlight=all",
                    old_path,
                    new_path,
                ],
                capture_output=True,
                text=True,
                env={**os.environ, "TERM": "xterm-256color"},
                timeout=5,
            )

            # git diff --no-index returns exit code 1 when files differ
            if result.returncode in [0, 1] and result.stdout:
                # Find and extract the actual diff content (after @@)
                output_lines = result.stdout.split("\n")

                for i, line in enumerate(output_lines):
                    # Look for @@ marker (may have ANSI codes like [36m@@)
                    if "@@" in line:
                        # Return everything after the @@ line
                        remaining = output_lines[i + 1 :]
                        filtered = [l for l in remaining if l.strip()]
                        if filtered:
                            return "\n".join(filtered)
                        break

            # If git diff didn't work, return original diff
            return diff_content

        finally:
            # Clean up temp files
            try:
                os.unlink(old_path)
                os.unlink(new_path)
            except:
                pass

    except Exception:
        # If git not available or error, return original diff
        return diff_content
