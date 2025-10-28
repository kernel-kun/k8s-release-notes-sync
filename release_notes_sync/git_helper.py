"""
Git integration utilities for detecting changed files and PR numbers.
"""

import os
import re
import subprocess
from typing import List, Optional

from .constants import MAP_FILE_REGEX


def is_git_repo(repo_root: str = None) -> bool:
    """
    Check if the directory is a git repository.

    Args:
        repo_root: Optional repository root path. Defaults to current directory.

    Returns:
        True if it's a git repo, False otherwise
    """
    if repo_root is None:
        repo_root = os.getcwd()

    git_dir = os.path.join(repo_root, ".git")
    return os.path.isdir(git_dir)


def run_git_command(args: List[str], cwd: str = None) -> Optional[str]:
    """
    Run a git command and return its output.

    Args:
        args: List of command arguments (e.g., ['diff', '--name-only'])
        cwd: Working directory for the command

    Returns:
        Command output as string, or None if command failed
    """
    try:
        cmd = ["git"] + args
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        return None
    except FileNotFoundError:
        print("Git command not found. Please ensure git is installed.")
        return None


def get_changed_files_since_commit(
    commit_id: str, directory: str = None, repo_root: str = None
) -> List[str]:
    """
    Get list of changed files since a specific commit.

    Args:
        commit_id: Commit hash or reference (e.g., 'HEAD~1', 'abc123')
        directory: Optional directory to filter changes (relative to repo root)
        repo_root: Optional repository root path

    Returns:
        List of file paths relative to repo root
    """
    if repo_root is None:
        repo_root = os.getcwd()

    if not is_git_repo(repo_root):
        print(f"Not a git repository: {repo_root}")
        return []

    # Build git diff command
    args = ["diff", "--name-only", commit_id, "HEAD"]

    # Add directory filter if specified
    if directory:
        args.extend(["--", directory])

    output = run_git_command(args, cwd=repo_root)

    if output is None:
        return []

    # Filter out empty lines
    files = [f for f in output.split("\n") if f]
    return files


def filter_map_files(file_list: List[str]) -> List[str]:
    """
    Filter list to only include map files.

    Args:
        file_list: List of file paths

    Returns:
        List of map file paths
    """
    map_files = []

    for file_path in file_list:
        filename = os.path.basename(file_path)
        if re.match(MAP_FILE_REGEX, filename):
            map_files.append(file_path)

    return map_files


def extract_pr_numbers(map_files: List[str]) -> List[str]:
    """
    Extract PR numbers from map file paths.

    Args:
        map_files: List of map file paths

    Returns:
        List of PR numbers as strings
    """
    pr_numbers = []

    for file_path in map_files:
        filename = os.path.basename(file_path)
        match = re.search(MAP_FILE_REGEX, filename)
        if match:
            pr_numbers.append(match.group(1))

    return pr_numbers


def get_changed_map_files(
    commit_id: str, release_version: str, repo_root: str = None
) -> List[str]:
    """
    Get list of changed map files since a commit for a specific release.

    Args:
        commit_id: Commit hash or reference
        release_version: Release version (e.g., "1.35")
        repo_root: Optional repository root path

    Returns:
        List of changed map file paths
    """
    # Construct the maps directory path
    maps_dir = f"releases/release-{release_version}/release-notes/maps"

    # Get all changed files in the maps directory
    changed_files = get_changed_files_since_commit(commit_id, maps_dir, repo_root)

    # Filter to only map files
    map_files = filter_map_files(changed_files)

    return map_files


def get_changed_pr_numbers(
    commit_id: str, release_version: str, repo_root: str = None
) -> List[str]:
    """
    Get list of PR numbers from changed map files since a commit.

    Args:
        commit_id: Commit hash or reference
        release_version: Release version (e.g., "1.35")
        repo_root: Optional repository root path

    Returns:
        List of PR numbers as strings
    """
    map_files = get_changed_map_files(commit_id, release_version, repo_root)
    pr_numbers = extract_pr_numbers(map_files)
    return pr_numbers


def has_uncommitted_changes(repo_root: str = None) -> bool:
    """
    Check if there are uncommitted changes in the repository.

    Args:
        repo_root: Optional repository root path

    Returns:
        True if there are uncommitted changes, False otherwise
    """
    if repo_root is None:
        repo_root = os.getcwd()

    if not is_git_repo(repo_root):
        return False

    try:
        # Use git status --porcelain for faster check
        cmd = ["git", "status", "--porcelain"]
        result = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)

        # If there's any output, there are changes
        return bool(result.stdout.strip())

    except subprocess.TimeoutExpired:
        print("Warning: Git status check timed out, skipping uncommitted changes check")
        return False
    except Exception as e:
        print(f"Warning: Could not check git status: {e}")
        return False


def get_current_branch(repo_root: str = None) -> Optional[str]:
    """
    Get the current git branch name.

    Args:
        repo_root: Optional repository root path

    Returns:
        Branch name or None if not in a repo
    """
    if repo_root is None:
        repo_root = os.getcwd()

    if not is_git_repo(repo_root):
        return None

    output = run_git_command(["branch", "--show-current"], cwd=repo_root)
    return output


def validate_commit_reference(commit_ref: str, repo_root: str = None) -> bool:
    """
    Validate that a commit reference exists.

    Args:
        commit_ref: Commit reference (hash, branch, HEAD~1, etc.)
        repo_root: Optional repository root path

    Returns:
        True if commit exists, False otherwise
    """
    if repo_root is None:
        repo_root = os.getcwd()

    if not is_git_repo(repo_root):
        return False

    # Try to resolve the reference
    output = run_git_command(["rev-parse", "--verify", commit_ref], cwd=repo_root)
    return output is not None
