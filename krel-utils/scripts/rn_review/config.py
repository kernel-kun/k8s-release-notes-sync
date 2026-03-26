"""Configuration constants and path construction for the Release Notes Review utility."""

from __future__ import annotations

import os
from pathlib import Path


# Default GitHub settings
DEFAULT_GITHUB_OWNER = "kubernetes"
DEFAULT_GITHUB_REPO = "kubernetes"
GITHUB_API_BASE = "https://api.github.com"
GITHUB_WEB_BASE = "https://github.com"

# File names used by krel
DRAFT_MARKDOWN_FILE = "release-notes-draft.md"
DRAFT_JSON_FILE = "release-notes-draft.json"
RELEASE_NOTES_WORK_DIR = "release-notes"
MAPS_DIRECTORY = "maps"

# Default output file name
DEFAULT_REVIEW_FILE = "review-prs.json"


def get_github_token() -> str:
    """Retrieve the GitHub token from environment.

    Returns:
        The token string, or empty string if not set.
    """
    return os.environ.get("GITHUB_TOKEN", "")


def build_release_path(repo_dir: str, release_version: str) -> Path:
    """Build the path to the release directory within the sig-release repo.

    Args:
        repo_dir: Path to the sig-release repository root.
        release_version: Release version string, e.g., "1.36".

    Returns:
        Path to releases/release-<version>/release-notes/
    """
    return (
        Path(repo_dir)
        / "releases"
        / f"release-{release_version}"
        / RELEASE_NOTES_WORK_DIR
    )


def build_notes_md_path(repo_dir: str, release_version: str) -> Path:
    """Build the path to release-notes-draft.md."""
    return build_release_path(repo_dir, release_version) / DRAFT_MARKDOWN_FILE


def build_notes_json_path(repo_dir: str, release_version: str) -> Path:
    """Build the path to release-notes-draft.json."""
    return build_release_path(repo_dir, release_version) / DRAFT_JSON_FILE


def build_maps_dir(repo_dir: str, release_version: str) -> Path:
    """Build the path to the maps directory."""
    return build_release_path(repo_dir, release_version) / MAPS_DIRECTORY


def build_map_file_path(
    repo_dir: str, release_version: str, pr_number: int
) -> Path:
    """Build the path to a specific map file."""
    return build_maps_dir(repo_dir, release_version) / f"pr-{pr_number}-map.yaml"
