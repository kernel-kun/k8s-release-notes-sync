"""
Validation logic for checking consistency across map files, JSON, and Markdown.
"""

import os
from typing import Dict, List, Optional

from .comparator import (ComparisonResult, compare_texts,
                         extract_text_from_markdown, validate_markdown_in_file)
from .constants import (STATUS_CORRECT, STATUS_ERROR, STATUS_INCORRECT,
                        STATUS_MISSING_JSON, STATUS_MISSING_MD, get_json_file,
                        get_map_file, get_maps_dir, get_md_file)
from .file_loader import (extract_pr_number_from_filename,
                          extract_pr_number_from_json_entry,
                          extract_text_from_map, get_all_map_files,
                          get_json_markdown, get_json_text, load_json_file,
                          load_map_file, load_markdown_file)


def validate_pr(
    pr_number: str, release_version: str, repo_root: str = None
) -> ComparisonResult:
    """
    Validate consistency of a single PR across all files.

    Args:
        pr_number: PR number to validate
        release_version: Release version (e.g., "1.35")
        repo_root: Optional repository root path

    Returns:
        ComparisonResult with validation details
    """
    result = ComparisonResult(pr_number)

    try:
        # Step 1: Load map file
        map_file_path = get_map_file(pr_number, release_version, repo_root)

        if not os.path.exists(map_file_path):
            result.status = STATUS_MISSING_JSON  # If no map, it's an issue
            result.map_exists = False
            return result

        result.map_exists = True
        map_data = load_map_file(map_file_path)
        result.map_text = extract_text_from_map(map_data)

        if not result.map_text:
            result.status = STATUS_ERROR
            result.error = "Map file exists but has no text field"
            return result

        # Step 2: Load JSON file and find entry
        json_file_path = get_json_file(release_version, repo_root)
        json_data = load_json_file(json_file_path)

        json_entry = extract_pr_number_from_json_entry(json_data, pr_number)

        if json_entry is None:
            result.status = STATUS_MISSING_JSON
            result.json_exists = False
            return result

        result.json_exists = True
        result.json_text = get_json_text(json_entry)
        result.json_markdown = get_json_markdown(json_entry)

        # Step 3: Compare map text with JSON text
        result.map_json_match = compare_texts(result.map_text, result.json_text)

        # Step 4: Extract text from JSON markdown field and compare
        json_md_text = extract_text_from_markdown(result.json_markdown)
        result.json_md_match = compare_texts(result.json_text, json_md_text)

        # Step 5: Check markdown file
        md_file_path = get_md_file(release_version, repo_root)
        md_content = load_markdown_file(md_file_path)

        result.md_content = result.json_markdown  # Store expected content
        result.md_exists = validate_markdown_in_file(result.json_markdown, md_content)
        result.md_file_match = result.md_exists

        if not result.md_exists:
            result.status = STATUS_MISSING_MD
            return result

        # Step 6: Determine overall status
        if result.is_correct():
            result.status = STATUS_CORRECT
        else:
            result.status = STATUS_INCORRECT

    except Exception as e:
        result.status = STATUS_ERROR
        result.error = str(e)

    return result


def validate_all_prs(
    release_version: str, pr_numbers: Optional[List[str]] = None, repo_root: str = None
) -> Dict[str, List[ComparisonResult]]:
    """
    Validate multiple PRs and categorize results.

    Args:
        release_version: Release version (e.g., "1.35")
        pr_numbers: Optional list of specific PR numbers to validate.
                   If None, validates all map files.
        repo_root: Optional repository root path

    Returns:
        Dictionary with categorized results:
        {
            'correct': [ComparisonResult, ...],
            'incorrect': [ComparisonResult, ...],
            'missing_json': [ComparisonResult, ...],
            'missing_md': [ComparisonResult, ...],
            'errors': [{'pr_number': str, 'error': str}, ...]
        }
    """
    results = {
        "correct": [],
        "incorrect": [],
        "missing_json": [],
        "missing_md": [],
        "errors": [],
    }

    # Get PR numbers to validate
    if pr_numbers is None:
        # Get all map files in directory
        maps_dir = get_maps_dir(release_version, repo_root)
        map_files = get_all_map_files(maps_dir)
        pr_numbers = []

        for map_file in map_files:
            pr_num = extract_pr_number_from_filename(os.path.basename(map_file))
            if pr_num:
                pr_numbers.append(pr_num)

    # Validate each PR
    for pr_num in pr_numbers:
        try:
            validation = validate_pr(pr_num, release_version, repo_root)

            if validation.status == STATUS_CORRECT:
                results["correct"].append(validation)
            elif validation.status == STATUS_INCORRECT:
                results["incorrect"].append(validation)
            elif validation.status == STATUS_MISSING_JSON:
                results["missing_json"].append(validation)
            elif validation.status == STATUS_MISSING_MD:
                results["missing_md"].append(validation)
            elif validation.status == STATUS_ERROR:
                results["errors"].append(
                    {"pr_number": pr_num, "error": validation.error}
                )
        except Exception as e:
            results["errors"].append({"pr_number": pr_num, "error": str(e)})

    return results


def validate_incremental(
    release_version: str, pr_numbers: List[str], repo_root: str = None
) -> Dict[str, List[ComparisonResult]]:
    """
    Validate specific PRs (incremental mode).

    Args:
        release_version: Release version (e.g., "1.35")
        pr_numbers: List of PR numbers to validate
        repo_root: Optional repository root path

    Returns:
        Categorized validation results
    """
    return validate_all_prs(release_version, pr_numbers, repo_root)


def validate_global(
    release_version: str, repo_root: str = None
) -> Dict[str, List[ComparisonResult]]:
    """
    Validate all PRs in a release (global mode).

    Args:
        release_version: Release version (e.g., "1.35")
        repo_root: Optional repository root path

    Returns:
        Categorized validation results
    """
    return validate_all_prs(release_version, None, repo_root)


def get_validation_summary(results: Dict[str, List]) -> Dict[str, int]:
    """
    Get summary counts from validation results.

    Args:
        results: Categorized validation results

    Returns:
        Dictionary with count summaries
    """
    return {
        "correct": len(results.get("correct", [])),
        "incorrect": len(results.get("incorrect", [])),
        "missing_json": len(results.get("missing_json", [])),
        "missing_md": len(results.get("missing_md", [])),
        "errors": len(results.get("errors", [])),
        "total": sum(
            [
                len(results.get("correct", [])),
                len(results.get("incorrect", [])),
                len(results.get("missing_json", [])),
                len(results.get("missing_md", [])),
                len(results.get("errors", [])),
            ]
        ),
    }


def has_validation_issues(results: Dict[str, List]) -> bool:
    """
    Check if validation found any issues.

    Args:
        results: Categorized validation results

    Returns:
        True if there are any incorrect, missing, or error results
    """
    return (
        len(results.get("incorrect", [])) > 0
        or len(results.get("missing_json", [])) > 0
        or len(results.get("missing_md", [])) > 0
        or len(results.get("errors", [])) > 0
    )
