"""Git diff-based PR extraction from release-notes-draft.md.

Compares two git refs of the markdown file to identify new or modified
PR entries. This enables incremental review after krel regeneration.
"""

from __future__ import annotations

import logging
import subprocess
from collections import OrderedDict
from pathlib import Path

from .markdown_extractor import MarkdownPREntry, extract_pr_entries

logger = logging.getLogger(__name__)


def git_show_file(repo_dir: str, ref: str, file_path: str) -> str:
    """Retrieve file content at a specific git ref.

    Args:
        repo_dir: Path to the git repository.
        ref: Git ref (branch, tag, SHA, HEAD~, etc.).
        file_path: Path to the file relative to the repo root.

    Returns:
        The file content as a string.

    Raises:
        subprocess.CalledProcessError: If git command fails.
        FileNotFoundError: If the file doesn't exist at the given ref.
    """
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{file_path}"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        if "does not exist" in e.stderr or "fatal: path" in e.stderr:
            raise FileNotFoundError(
                f"File '{file_path}' not found at ref '{ref}' in {repo_dir}"
            ) from e
        raise


def extract_diff_prs(
    repo_dir: str,
    notes_path: str,
    old_ref: str = "HEAD~",
    new_ref: str = "HEAD",
) -> OrderedDict[int, MarkdownPREntry]:
    """Extract PRs that were added or modified between two git refs.

    Compares the release-notes-draft.md at old_ref vs new_ref and returns
    only the PR entries that are new or have changed note text.

    Args:
        repo_dir: Path to the sig-release git repository.
        notes_path: Path to release-notes-draft.md relative to repo root.
        old_ref: The older git ref (default: HEAD~).
        new_ref: The newer git ref (default: HEAD).

    Returns:
        OrderedDict of new/modified PR entries.
    """
    logger.info(
        "Extracting diff PRs: %s..%s for %s", old_ref, new_ref, notes_path
    )

    # Get file content at both refs
    try:
        old_content = git_show_file(repo_dir, old_ref, notes_path)
    except FileNotFoundError:
        logger.warning(
            "File not found at old ref '%s', treating all PRs as new",
            old_ref,
        )
        old_content = ""

    new_content = git_show_file(repo_dir, new_ref, notes_path)

    # Parse both versions
    old_entries = extract_pr_entries(old_content)
    new_entries = extract_pr_entries(new_content)

    # Find new or modified entries
    diff_entries: OrderedDict[int, MarkdownPREntry] = OrderedDict()

    for pr_number, new_entry in new_entries.items():
        if pr_number not in old_entries:
            logger.debug("PR #%d is new", pr_number)
            diff_entries[pr_number] = new_entry
        elif old_entries[pr_number].note_text != new_entry.note_text:
            logger.debug("PR #%d has modified text", pr_number)
            diff_entries[pr_number] = new_entry

    logger.info(
        "Found %d new/modified PRs (out of %d total in new ref)",
        len(diff_entries),
        len(new_entries),
    )

    return diff_entries


def extract_full_prs(
    repo_dir: str,
    notes_path: str,
    ref: str = "HEAD",
) -> OrderedDict[int, MarkdownPREntry]:
    """Extract all PRs from release-notes-draft.md at a given ref.

    Args:
        repo_dir: Path to the sig-release git repository.
        notes_path: Path to release-notes-draft.md relative to repo root.
        ref: Git ref to read from (default: HEAD).

    Returns:
        OrderedDict of all PR entries.
    """
    logger.info("Extracting all PRs from %s at ref %s", notes_path, ref)

    content = git_show_file(repo_dir, ref, notes_path)
    entries = extract_pr_entries(content)

    logger.info("Found %d PRs", len(entries))
    return entries


def extract_prs_from_file(file_path: str | Path) -> OrderedDict[int, MarkdownPREntry]:
    """Extract all PRs from a local release-notes-draft.md file.

    This is a convenience function for when you have the file locally
    and don't need git ref resolution.

    Args:
        file_path: Path to the local release-notes-draft.md file.

    Returns:
        OrderedDict of all PR entries.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Markdown file not found: {path}")

    content = path.read_text(encoding="utf-8")
    entries = extract_pr_entries(content)

    logger.info("Found %d PRs in %s", len(entries), path)
    return entries
