"""
Constants and configuration for the Release Notes Sync Tool.
"""

import os

# Directory structure patterns
RELEASE_DIR_PATTERN = "releases/release-{version}"
MAPS_DIR_NAME = "release-notes/maps"
JSON_FILENAME = "release-notes-draft.json"
MD_FILENAME = "release-notes-draft.md"

# File patterns
MAP_FILE_PATTERN = "pr-{pr_number}-map.yaml"
MAP_FILE_REGEX = r"pr-(\d+)-map\.yaml$"

# YAML field paths
YAML_RELEASENOTE_TEXT = "releasenote.text"

# JSON field names
JSON_TEXT_FIELD = "text"
JSON_MARKDOWN_FIELD = "markdown"

# Validation statuses
STATUS_CORRECT = "correct"
STATUS_INCORRECT = "incorrect"
STATUS_MISSING_MAP = "missing_map"
STATUS_MISSING_JSON = "missing_json"
STATUS_MISSING_MD = "missing_md"
STATUS_ERROR = "error"

# Output formats
OUTPUT_TABLE = "table"
OUTPUT_JSON = "json"
OUTPUT_CSV = "csv"

# ANSI color codes (for colorama)
COLOR_GREEN = "\033[92m"
COLOR_RED = "\033[91m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_RESET = "\033[0m"

# Symbols for output
SYMBOL_CHECK = "✓"
SYMBOL_CROSS = "✗"
SYMBOL_WARNING = "⚠"

# Diff display settings
MAX_DIFF_DISPLAY_CHARS = 1000
DIFF_CONTEXT_LINES = 3


def get_release_dir(release_version: str, repo_root: str = None) -> str:
    """
    Get the full path to a release directory.

    Args:
        release_version: Release version (e.g., "1.35")
        repo_root: Optional repository root path. Defaults to current directory.

    Returns:
        Full path to release directory
    """
    if repo_root is None:
        repo_root = os.getcwd()

    release_dir = RELEASE_DIR_PATTERN.format(version=release_version)
    return os.path.join(repo_root, release_dir)


def get_maps_dir(release_version: str, repo_root: str = None) -> str:
    """
    Get the full path to the maps directory.

    Args:
        release_version: Release version (e.g., "1.35")
        repo_root: Optional repository root path

    Returns:
        Full path to maps directory
    """
    release_dir = get_release_dir(release_version, repo_root)
    return os.path.join(release_dir, MAPS_DIR_NAME)


def get_json_file(release_version: str, repo_root: str = None) -> str:
    """
    Get the full path to the JSON file.

    Args:
        release_version: Release version (e.g., "1.35")
        repo_root: Optional repository root path

    Returns:
        Full path to JSON file
    """
    release_dir = get_release_dir(release_version, repo_root)
    return os.path.join(release_dir, "release-notes", JSON_FILENAME)


def get_md_file(release_version: str, repo_root: str = None) -> str:
    """
    Get the full path to the Markdown file.

    Args:
        release_version: Release version (e.g., "1.35")
        repo_root: Optional repository root path

    Returns:
        Full path to Markdown file
    """
    release_dir = get_release_dir(release_version, repo_root)
    return os.path.join(release_dir, "release-notes", MD_FILENAME)


def get_map_file(pr_number: str, release_version: str, repo_root: str = None) -> str:
    """
    Get the full path to a specific map file.

    Args:
        pr_number: PR number as string
        release_version: Release version (e.g., "1.35")
        repo_root: Optional repository root path

    Returns:
        Full path to map file
    """
    maps_dir = get_maps_dir(release_version, repo_root)
    filename = MAP_FILE_PATTERN.format(pr_number=pr_number)
    return os.path.join(maps_dir, filename)
