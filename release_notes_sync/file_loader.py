"""
File loading and parsing utilities for YAML, JSON, and Markdown files.
"""

import json
import os
import re
from typing import Any, Dict, Optional

import yaml

from .constants import JSON_MARKDOWN_FIELD, JSON_TEXT_FIELD


def load_map_file(file_path: str) -> Dict[str, Any]:
    """
    Load a YAML map file and return its contents.

    Args:
        file_path: Path to the map file

    Returns:
        Parsed YAML content as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML is malformed
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Map file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
            return data
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing YAML file {file_path}: {e}")


def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    Load the JSON release notes file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Parsed JSON content as dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is malformed
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Error parsing JSON file {file_path}: {e.msg}", e.doc, e.pos
            )


def load_markdown_file(file_path: str) -> str:
    """
    Load the Markdown release notes file.

    Args:
        file_path: Path to the Markdown file

    Returns:
        Markdown content as string

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Markdown file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def save_json_file(file_path: str, data: Dict[str, Any]) -> None:
    """
    Save data to JSON file with proper formatting.

    Args:
        file_path: Path to the JSON file
        data: Dictionary to save

    Raises:
        IOError: If file cannot be written
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        # Add newline at end of file
        f.write("\n")


def save_markdown_file(file_path: str, content: str) -> None:
    """
    Save content to Markdown file.

    Args:
        file_path: Path to the Markdown file
        content: Markdown content to save

    Raises:
        IOError: If file cannot be written
    """
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)


def extract_text_from_map(map_data: Dict[str, Any]) -> Optional[str]:
    """
    Extract the release note text from a map file data structure.

    YAML files may have quotes around the text field. The YAML parser
    handles them, but we strip any remaining quotes just to be safe.

    Args:
        map_data: Parsed map file content

    Returns:
        Release note text or None if not found
    """
    try:
        # Navigate the nested structure: releasenote -> text
        text = map_data.get("releasenote", {}).get("text")
        if text and isinstance(text, str):
            # Strip enclosing quotes if present (shouldn't be needed but safe)
            text = text.strip()
            if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
                text = text[1:-1]
        return text
    except (AttributeError, TypeError):
        return None


def extract_pr_number_from_json_entry(
    json_data: Dict[str, Any], pr_number: str
) -> Optional[Dict[str, Any]]:
    """
    Extract a specific PR entry from JSON data.

    Args:
        json_data: Parsed JSON file content
        pr_number: PR number to look for

    Returns:
        PR entry dictionary or None if not found
    """
    return json_data.get(pr_number)


def get_json_text(json_entry: Dict[str, Any]) -> str:
    """
    Get the text field from a JSON entry.

    Args:
        json_entry: JSON entry for a PR

    Returns:
        Text content or empty string if not found
    """
    return json_entry.get(JSON_TEXT_FIELD, "")


def get_json_markdown(json_entry: Dict[str, Any]) -> str:
    """
    Get the markdown field from a JSON entry.

    Args:
        json_entry: JSON entry for a PR

    Returns:
        Markdown content or empty string if not found
    """
    return json_entry.get(JSON_MARKDOWN_FIELD, "")


def normalize_yaml_text(text: str) -> str:
    """
    Normalize YAML text for comparison.

    YAML multi-line strings are collapsed unless they contain explicit \\n.
    This handles the case where YAML natural line breaks should become spaces,
    while preserving intentional line breaks marked with \\n.

    Args:
        text: Raw text from YAML

    Returns:
        Normalized text
    """
    if text is None:
        return ""

    # Strip leading/trailing whitespace
    text = text.strip()

    # Collapse all whitespace (spaces, tabs, newlines) to single space
    # This handles YAML multi-line strings that should be treated as single line
    text = re.sub(r"\s+", " ", text)

    return text


def find_markdown_entry(markdown_content: str, markdown_line: str) -> bool:
    """
    Check if a markdown line exists in the markdown file.

    The markdown file may have:
    1. List item prefixes ("- ") that the JSON doesn't have
    2. Different whitespace/newline patterns

    We use normalized comparison (collapse all whitespace) to match.

    Args:
        markdown_content: Full markdown file content
        markdown_line: Specific line to search for (from JSON)

    Returns:
        True if line found, False otherwise
    """
    # First try direct match
    if markdown_line in markdown_content:
        return True

    # Try with markdown list item prefix "- "
    with_prefix = "- " + markdown_line
    if with_prefix in markdown_content:
        return True

    # If still not found, try normalized comparison
    # Normalize the markdown line (collapse whitespace)
    json_normalized = re.sub(r"\s+", " ", markdown_line.strip())

    # Normalize the markdown content and check
    md_normalized = re.sub(r"\s+", " ", markdown_content)
    if json_normalized in md_normalized:
        return True

    return False


def get_all_map_files(maps_dir: str) -> list:
    """
    Get all map files in a directory.

    Args:
        maps_dir: Path to maps directory

    Returns:
        List of map file paths
    """
    if not os.path.exists(maps_dir):
        return []

    map_files = []
    for filename in os.listdir(maps_dir):
        if filename.startswith("pr-") and filename.endswith("-map.yaml"):
            map_files.append(os.path.join(maps_dir, filename))

    return sorted(map_files)


def extract_pr_number_from_filename(filename: str) -> Optional[str]:
    """
    Extract PR number from a map filename.

    Args:
        filename: Map filename (e.g., "pr-133540-map.yaml")

    Returns:
        PR number as string or None if pattern doesn't match
    """
    from .constants import MAP_FILE_REGEX

    match = re.search(MAP_FILE_REGEX, filename)
    if match:
        return match.group(1)
    return None
