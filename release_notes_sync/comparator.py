"""
Text comparison utilities for release notes synchronization.
"""

import difflib
import re
from typing import Dict, Optional, Tuple

from .file_loader import normalize_yaml_text


def compare_texts(text1: str, text2: str) -> bool:
    """
    Compare two texts for equivalence after normalization.

    Args:
        text1: First text to compare
        text2: Second text to compare

    Returns:
        True if texts match after normalization, False otherwise
    """
    normalized1 = normalize_yaml_text(text1)
    normalized2 = normalize_yaml_text(text2)
    return normalized1 == normalized2


def extract_text_from_markdown(markdown_field: str) -> str:
    """
    Extract the descriptive text from a markdown field, excluding metadata.

    The markdown field format is:
    "Descriptive text ([#PR](url), [@author](url)) [SIG Name]"

    This function extracts only "Descriptive text" part.

    Args:
        markdown_field: Full markdown field content

    Returns:
        Extracted text portion (before PR link)
    """
    if not markdown_field:
        return ""

    # Match everything before the first PR link pattern
    # Pattern: ([#123456]
    # Use DOTALL flag to match across newlines
    pattern = r"^(.*?)\s*\(\[#\d+\]"
    match = re.match(pattern, markdown_field, re.DOTALL)

    if match:
        return match.group(1).strip()

    # Fallback: return entire field if pattern not found
    return markdown_field.strip()


def are_texts_equivalent(text1: str, text2: str) -> bool:
    """
    Check if two texts are equivalent (alias for compare_texts).

    Args:
        text1: First text
        text2: Second text

    Returns:
        True if equivalent, False otherwise
    """
    return compare_texts(text1, text2)


def generate_diff(old_text: str, new_text: str, context_lines: int = 3) -> str:
    """
    Generate a unified diff between old and new text.

    Args:
        old_text: Original text
        new_text: New text
        context_lines: Number of context lines to show (default: 3)

    Returns:
        Unified diff as string
    """
    if not old_text:
        old_text = ""
    if not new_text:
        new_text = ""

    old_lines = old_text.split("\n")
    new_lines = new_text.split("\n")

    diff = difflib.unified_diff(
        old_lines, new_lines, lineterm="", fromfile="OLD", tofile="NEW", n=context_lines
    )

    return "\n".join(diff)


def generate_side_by_side_diff(old_text: str, new_text: str, width: int = 80) -> str:
    """
    Generate a side-by-side diff display.

    Args:
        old_text: Original text
        new_text: New text
        width: Display width for each side

    Returns:
        Side-by-side diff as string
    """
    if not old_text:
        old_text = ""
    if not new_text:
        new_text = ""

    # For simple single-line diffs, just show both
    if "\n" not in old_text and "\n" not in new_text:
        return f"OLD: {old_text}\nNEW: {new_text}"

    # For multi-line, use unified diff
    return generate_diff(old_text, new_text)


def compare_map_to_json(map_text: str, json_text: str) -> Tuple[bool, Optional[str]]:
    """
    Compare map text with JSON text field.

    Args:
        map_text: Text from map file
        json_text: Text from JSON file

    Returns:
        Tuple of (match: bool, diff: str or None)
    """
    match = compare_texts(map_text, json_text)
    diff = None if match else generate_diff(json_text, map_text)
    return match, diff


def compare_json_to_markdown(
    json_text: str, markdown_field: str
) -> Tuple[bool, Optional[str]]:
    """
    Compare JSON text field with the text portion of JSON markdown field.

    Args:
        json_text: Text from JSON text field
        markdown_field: Full markdown field from JSON

    Returns:
        Tuple of (match: bool, diff: str or None)
    """
    md_text = extract_text_from_markdown(markdown_field)
    match = compare_texts(json_text, md_text)
    diff = None if match else generate_diff(md_text, json_text)
    return match, diff


def validate_markdown_in_file(markdown_field: str, markdown_content: str) -> bool:
    """
    Check if the markdown field exists in the markdown file content.

    Args:
        markdown_field: The markdown line to search for
        markdown_content: Full markdown file content

    Returns:
        True if found, False otherwise
    """
    from .file_loader import find_markdown_entry

    return find_markdown_entry(markdown_content, markdown_field)


class ComparisonResult:
    """
    Data class to hold comparison results for a PR.
    """

    def __init__(self, pr_number: str):
        self.pr_number = pr_number
        self.map_text: Optional[str] = None
        self.json_text: Optional[str] = None
        self.json_markdown: Optional[str] = None
        self.md_content: Optional[str] = None

        self.map_exists = False
        self.json_exists = False
        self.md_exists = False

        self.map_json_match = False
        self.json_md_match = False
        self.md_file_match = False

        self.status = "unknown"
        self.error: Optional[str] = None

    def is_correct(self) -> bool:
        """Check if all fields match correctly."""
        return (
            self.map_exists
            and self.json_exists
            and self.md_exists
            and self.map_json_match
            and self.json_md_match
            and self.md_file_match
        )

    def is_incorrect(self) -> bool:
        """Check if there are mismatches."""
        return (
            self.map_exists
            and self.json_exists
            and not self.is_correct()
            and self.status != "missing_md"
        )

    def has_missing_files(self) -> bool:
        """Check if any files are missing."""
        return not (self.map_exists and self.json_exists and self.md_exists)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON output."""
        return {
            "pr_number": self.pr_number,
            "map_text": self.map_text,
            "json_text": self.json_text,
            "json_markdown": self.json_markdown,
            "map_exists": self.map_exists,
            "json_exists": self.json_exists,
            "md_exists": self.md_exists,
            "map_json_match": self.map_json_match,
            "json_md_match": self.json_md_match,
            "md_file_match": self.md_file_match,
            "status": self.status,
            "error": self.error,
        }
