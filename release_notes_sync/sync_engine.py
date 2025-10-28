"""
Synchronization engine for applying changes from map files to JSON and Markdown.
"""

import re
from typing import Dict, List

from .comparator import compare_texts, generate_diff
from .constants import (JSON_MARKDOWN_FIELD, JSON_TEXT_FIELD, get_json_file,
                        get_map_file, get_md_file)
from .file_loader import (extract_text_from_map, get_json_markdown,
                          get_json_text, load_json_file, load_map_file,
                          load_markdown_file, save_json_file,
                          save_markdown_file)


def update_markdown_text_portion(old_markdown: str, new_text: str) -> str:
    """
    Update the text portion of a markdown field while preserving metadata.

    The markdown field format is:
    "Descriptive text ([#PR](url), [@author](url)) [SIG Name]"

    This function replaces "Descriptive text" with new_text while keeping
    the metadata (PR link, author, SIG) intact.

    Args:
        old_markdown: Original markdown field
        new_text: New text to replace the descriptive portion

    Returns:
        Updated markdown field
    """
    # Find where the PR link starts: ([#123456]
    match = re.search(r"\s*(\(\[#\d+\].*)", old_markdown)

    if match:
        metadata = match.group(1)
        return f"{new_text} {metadata}"

    # Fallback: if pattern not found, just return new text
    # This shouldn't happen in well-formed data
    return new_text


def prepare_sync_changes(
    pr_number: str, map_text: str, json_entry: Dict, markdown_content: str
) -> Dict:
    """
    Prepare all changes needed for a PR sync without applying them.

    Args:
        pr_number: PR number
        map_text: Text from map file (source of truth)
        json_entry: JSON entry for this PR
        markdown_content: Full markdown file content

    Returns:
        Dictionary with prepared changes and diffs
    """
    from .comparator import extract_text_from_markdown

    old_json_text = get_json_text(json_entry)
    old_json_markdown = get_json_markdown(json_entry)

    # Prepare new values
    new_json_text = map_text
    new_json_markdown = update_markdown_text_portion(old_json_markdown, map_text)

    # Prepare markdown file update
    new_markdown_content = markdown_content.replace(
        old_json_markdown, new_json_markdown
    )

    # Check if changes are needed
    # Changes needed if:
    # 1. Map text != JSON text, OR
    # 2. JSON text != text portion of JSON markdown field
    map_json_match = compare_texts(map_text, old_json_text)

    # Extract text from JSON markdown and compare with JSON text
    json_md_text = extract_text_from_markdown(old_json_markdown)
    json_md_match = compare_texts(old_json_text, json_md_text)

    changes_needed = not (map_json_match and json_md_match)

    # Generate diffs
    changes = {
        "pr_number": pr_number,
        "changes_needed": changes_needed,
        "json_text": {
            "old": old_json_text,
            "new": new_json_text,
            "diff": generate_diff(old_json_text, new_json_text),
        },
        "json_markdown": {
            "old": old_json_markdown,
            "new": new_json_markdown,
            "diff": generate_diff(old_json_markdown, new_json_markdown),
        },
        "markdown_file": {
            "old": old_json_markdown,  # Just the line
            "new": new_json_markdown,
            "diff": generate_diff(old_json_markdown, new_json_markdown),
            "full_content": new_markdown_content,
        },
    }

    return changes


def apply_sync_changes(
    pr_number: str,
    changes: Dict,
    json_data: Dict,
    json_file_path: str,
    md_file_path: str,
) -> bool:
    """
    Apply prepared sync changes to files.

    Args:
        pr_number: PR number
        changes: Prepared changes dictionary
        json_data: Full JSON data (will be modified)
        json_file_path: Path to JSON file
        md_file_path: Path to markdown file

    Returns:
        True if changes applied successfully, False otherwise
    """
    try:
        # Update JSON entry
        json_data[pr_number][JSON_TEXT_FIELD] = changes["json_text"]["new"]
        json_data[pr_number][JSON_MARKDOWN_FIELD] = changes["json_markdown"]["new"]

        # Write JSON file
        save_json_file(json_file_path, json_data)

        # Write Markdown file
        save_markdown_file(md_file_path, changes["markdown_file"]["full_content"])

        return True
    except Exception as e:
        print(f"Error applying changes: {e}")
        return False


def sync_pr(
    pr_number: str,
    release_version: str,
    auto_approve: bool = False,
    dry_run: bool = False,
    repo_root: str = None,
) -> Dict:
    """
    Sync a single PR from map file to JSON and markdown.

    Args:
        pr_number: PR number to sync
        release_version: Release version (e.g., "1.35")
        auto_approve: If True, skip user confirmation
        dry_run: If True, show changes but don't apply
        repo_root: Optional repository root path

    Returns:
        Dictionary with sync results:
        {
            'pr_number': str,
            'changes_made': bool,
            'changes_needed': bool,
            'json_updated': bool,
            'md_updated': bool,
            'user_approved': bool,
            'diffs': List[Dict],
            'error': Optional[str]
        }
    """
    result = {
        "pr_number": pr_number,
        "changes_made": False,
        "changes_needed": False,
        "json_updated": False,
        "md_updated": False,
        "user_approved": False,
        "diffs": [],
        "error": None,
    }

    try:
        # Load map file (source of truth)
        map_file_path = get_map_file(pr_number, release_version, repo_root)
        map_data = load_map_file(map_file_path)
        map_text = extract_text_from_map(map_data)

        if not map_text:
            result["error"] = "Map file has no text field"
            return result

        # Load JSON file
        json_file_path = get_json_file(release_version, repo_root)
        json_data = load_json_file(json_file_path)

        if pr_number not in json_data:
            result["error"] = f"PR {pr_number} not found in JSON file"
            return result

        json_entry = json_data[pr_number]

        # Load markdown file
        md_file_path = get_md_file(release_version, repo_root)
        md_content = load_markdown_file(md_file_path)

        # Prepare changes
        changes = prepare_sync_changes(pr_number, map_text, json_entry, md_content)

        result["changes_needed"] = changes["changes_needed"]

        # If no changes needed, return early
        if not changes["changes_needed"]:
            return result

        # Store diffs for display
        result["diffs"] = [
            {
                "type": "JSON text field",
                "old": changes["json_text"]["old"],
                "new": changes["json_text"]["new"],
                "diff": changes["json_text"]["diff"],
            },
            {
                "type": "JSON markdown field",
                "old": changes["json_markdown"]["old"],
                "new": changes["json_markdown"]["new"],
                "diff": changes["json_markdown"]["diff"],
            },
            {
                "type": "Markdown file",
                "old": changes["markdown_file"]["old"],
                "new": changes["markdown_file"]["new"],
                "diff": changes["markdown_file"]["diff"],
            },
        ]

        # In dry-run mode, don't apply changes
        if dry_run:
            result["user_approved"] = False
            return result

        # Get user approval if not auto-approve
        if not auto_approve:
            # This will be handled by the CLI, we just mark it as approved here
            # The CLI will call this function after getting approval
            result["user_approved"] = True
        else:
            result["user_approved"] = True

        # Apply changes if approved
        if result["user_approved"]:
            success = apply_sync_changes(
                pr_number, changes, json_data, json_file_path, md_file_path
            )

            if success:
                result["changes_made"] = True
                result["json_updated"] = True
                result["md_updated"] = True
            else:
                result["error"] = "Failed to apply changes"

    except Exception as e:
        result["error"] = str(e)

    return result


def sync_multiple_prs(
    pr_numbers: List[str],
    release_version: str,
    auto_approve: bool = False,
    dry_run: bool = False,
    repo_root: str = None,
    interactive_callback=None,
) -> List[Dict]:
    """
    Sync multiple PRs with optional interactive approval.

    Args:
        pr_numbers: List of PR numbers to sync
        release_version: Release version (e.g., "1.35")
        auto_approve: If True, skip all confirmations
        dry_run: If True, show changes but don't apply
        repo_root: Optional repository root path
        interactive_callback: Optional function to call for each PR
                             Should accept (pr_number, diffs) and return bool

    Returns:
        List of sync result dictionaries
    """
    results = []

    for pr_num in pr_numbers:
        # First, prepare the sync to see if changes are needed
        result = sync_pr(
            pr_num,
            release_version,
            auto_approve=False,
            dry_run=True,  # Initially dry-run to get diffs
            repo_root=repo_root,
        )

        # If no changes needed, just record and continue
        if not result["changes_needed"]:
            results.append(result)
            continue

        # If there are changes and we have a callback, get user input
        if interactive_callback and not auto_approve and not dry_run:
            approved = interactive_callback(pr_num, result["diffs"])
            if not approved:
                result["user_approved"] = False
                results.append(result)
                continue

        # If we get here, apply the changes
        if not dry_run:
            result = sync_pr(
                pr_num,
                release_version,
                auto_approve=True,  # We already got approval
                dry_run=False,
                repo_root=repo_root,
            )

        results.append(result)

    return results


def get_prs_needing_sync(
    pr_numbers: List[str], release_version: str, repo_root: str = None
) -> List[str]:
    """
    Get list of PRs that need synchronization.

    Args:
        pr_numbers: List of PR numbers to check
        release_version: Release version (e.g., "1.35")
        repo_root: Optional repository root path

    Returns:
        List of PR numbers that have mismatched text
    """
    from .validator import validate_pr

    needs_sync = []

    for pr_num in pr_numbers:
        validation = validate_pr(pr_num, release_version, repo_root)
        if (
            not validation.is_correct()
            and validation.map_exists
            and validation.json_exists
        ):
            needs_sync.append(pr_num)

    return needs_sync
