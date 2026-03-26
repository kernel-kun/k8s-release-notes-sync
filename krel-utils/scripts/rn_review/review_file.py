"""Review JSON file management.

Handles creation, loading, saving, and updating of the intermediate
review JSON file that tracks PR review progress.
"""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import PREntry, PRReviewEntry, ReviewFile, ReviewMetadata

logger = logging.getLogger(__name__)


class ReviewFileManager:
    """Manages the review JSON file lifecycle.

    Provides methods to create, load, save, and update the review file
    that serves as the intermediate format between extraction and
    map generation.
    """

    def __init__(self, file_path: str | Path) -> None:
        """Initialize the review file manager.

        Args:
            file_path: Path where the review JSON file will be stored.
        """
        self._path = Path(file_path)
        self._data: ReviewFile | None = None

    @property
    def path(self) -> Path:
        """The path to the review file."""
        return self._path

    @property
    def is_loaded(self) -> bool:
        """Whether a review file is currently loaded."""
        return self._data is not None

    def create(
        self,
        pr_entries: list[PREntry],
        release_version: str,
        extraction_mode: str = "full",
        old_ref: str = "",
        new_ref: str = "",
    ) -> ReviewFile:
        """Create a new review file from extracted PR entries.

        Args:
            pr_entries: List of PREntry objects from extraction.
            release_version: The Kubernetes release version (e.g., "1.36").
            extraction_mode: How PRs were extracted ("full" or "diff").
            old_ref: The old git ref (for diff mode).
            new_ref: The new git ref (for diff mode).

        Returns:
            The created ReviewFile data.
        """
        now = datetime.now(timezone.utc).isoformat()

        metadata: ReviewMetadata = {
            "releaseVersion": release_version,
            "createdAt": now,
            "updatedAt": now,
            "extractionMode": extraction_mode,
            "oldRef": old_ref,
            "newRef": new_ref,
            "totalPRs": len(pr_entries),
            "reviewedPRs": 0,
        }

        prs: list[PRReviewEntry] = [
            entry.to_review_entry() for entry in pr_entries
        ]

        self._data = {
            "metadata": metadata,
            "prs": prs,
        }

        logger.info(
            "Created review file with %d PRs for release %s",
            len(prs),
            release_version,
        )

        return self._data

    def load(self) -> ReviewFile:
        """Load an existing review file from disk.

        Returns:
            The loaded ReviewFile data.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        if not self._path.exists():
            raise FileNotFoundError(
                f"Review file not found: {self._path}"
            )

        with open(self._path, encoding="utf-8") as f:
            self._data = json.load(f)

        logger.info(
            "Loaded review file with %d PRs from %s",
            len(self._data["prs"]),
            self._path,
        )

        return self._data

    def save(self, backup: bool = True) -> None:
        """Save the review file to disk.

        Args:
            backup: If True and file exists, create a .bak backup first.

        Raises:
            RuntimeError: If no data is loaded.
        """
        if self._data is None:
            raise RuntimeError("No review data loaded. Call create() or load() first.")

        # Create parent directories if needed
        self._path.parent.mkdir(parents=True, exist_ok=True)

        # Backup existing file
        if backup and self._path.exists():
            backup_path = self._path.with_suffix(".json.bak")
            shutil.copy2(self._path, backup_path)
            logger.debug("Backed up existing file to %s", backup_path)

        # Update the updatedAt timestamp
        self._data["metadata"]["updatedAt"] = (
            datetime.now(timezone.utc).isoformat()
        )

        # Recount reviewed PRs
        self._data["metadata"]["reviewedPRs"] = sum(
            1 for pr in self._data["prs"] if pr.get("reviewDone", False)
        )
        self._data["metadata"]["totalPRs"] = len(self._data["prs"])

        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
            f.write("\n")

        logger.info("Saved review file to %s", self._path)

    def get_data(self) -> ReviewFile:
        """Get the current review file data.

        Returns:
            The ReviewFile data.

        Raises:
            RuntimeError: If no data is loaded.
        """
        if self._data is None:
            raise RuntimeError("No review data loaded. Call create() or load() first.")
        return self._data

    def get_pr(self, pr_number: int) -> PRReviewEntry | None:
        """Get a specific PR entry by number.

        Args:
            pr_number: The PR number to look up.

        Returns:
            The PRReviewEntry, or None if not found.
        """
        if self._data is None:
            return None
        for pr in self._data["prs"]:
            if pr["prNumber"] == pr_number:
                return pr
        return None

    def update_pr(self, pr_number: int, updates: dict[str, Any]) -> bool:
        """Update fields on a specific PR entry.

        Args:
            pr_number: The PR number to update.
            updates: Dict of field names to new values.

        Returns:
            True if the PR was found and updated.
        """
        if self._data is None:
            return False

        for pr in self._data["prs"]:
            if pr["prNumber"] == pr_number:
                for key, value in updates.items():
                    if key in pr:
                        pr[key] = value
                    else:
                        logger.warning(
                            "Unknown field '%s' for PR #%d, skipping",
                            key,
                            pr_number,
                        )
                return True

        logger.warning("PR #%d not found in review file", pr_number)
        return False

    def mark_reviewed(
        self,
        pr_number: int,
        review_notes: str = "",
    ) -> bool:
        """Mark a PR as reviewed.

        Args:
            pr_number: The PR number to mark.
            review_notes: Optional notes about the review.

        Returns:
            True if the PR was found and marked.
        """
        updates: dict[str, Any] = {"reviewDone": True}
        if review_notes:
            updates["reviewNotes"] = review_notes
        return self.update_pr(pr_number, updates)

    def mark_unreviewed(self, pr_number: int) -> bool:
        """Mark a PR as not yet reviewed.

        Args:
            pr_number: The PR number to unmark.

        Returns:
            True if the PR was found and unmarked.
        """
        return self.update_pr(pr_number, {"reviewDone": False})

    def get_unreviewed_prs(self) -> list[PRReviewEntry]:
        """Get all PRs that haven't been reviewed yet.

        Returns:
            List of unreviewed PRReviewEntry objects.
        """
        if self._data is None:
            return []
        return [
            pr for pr in self._data["prs"]
            if not pr.get("reviewDone", False)
        ]

    def get_reviewed_prs(self) -> list[PRReviewEntry]:
        """Get all PRs that have been reviewed.

        Returns:
            List of reviewed PRReviewEntry objects.
        """
        if self._data is None:
            return []
        return [
            pr for pr in self._data["prs"]
            if pr.get("reviewDone", False)
        ]

    def get_modified_prs(self) -> list[PRReviewEntry]:
        """Get all PRs where the note was modified from the original.

        A PR is considered modified if currentDraftNote != originalNote.

        Returns:
            List of modified PRReviewEntry objects.
        """
        if self._data is None:
            return []
        return [
            pr for pr in self._data["prs"]
            if pr.get("currentDraftNote", "") != pr.get("originalNote", "")
        ]

    def get_map_candidates(self) -> list[PRReviewEntry]:
        """Get PRs that are ready for map file generation.

        A PR is a map candidate if:
        - It has been reviewed (reviewDone == True)
        - Its note was modified (currentDraftNote != originalNote)

        Returns:
            List of PRReviewEntry objects ready for map generation.
        """
        if self._data is None:
            return []
        return [
            pr for pr in self._data["prs"]
            if pr.get("reviewDone", False)
            and pr.get("currentDraftNote", "") != pr.get("originalNote", "")
        ]

    def get_progress(self) -> dict[str, int]:
        """Get review progress statistics.

        Returns:
            Dict with keys: total, reviewed, unreviewed, modified, mapCandidates.
        """
        if self._data is None:
            return {
                "total": 0,
                "reviewed": 0,
                "unreviewed": 0,
                "modified": 0,
                "mapCandidates": 0,
            }

        total = len(self._data["prs"])
        reviewed = len(self.get_reviewed_prs())
        modified = len(self.get_modified_prs())
        map_candidates = len(self.get_map_candidates())

        return {
            "total": total,
            "reviewed": reviewed,
            "unreviewed": total - reviewed,
            "modified": modified,
            "mapCandidates": map_candidates,
        }

    def merge_new_prs(self, new_entries: list[PREntry]) -> int:
        """Merge new PR entries into an existing review file.

        Only adds PRs that don't already exist in the file.
        Useful for incremental updates after krel regeneration.

        Args:
            new_entries: List of new PREntry objects.

        Returns:
            Number of new PRs added.
        """
        if self._data is None:
            raise RuntimeError("No review data loaded. Call load() first.")

        existing_numbers = {pr["prNumber"] for pr in self._data["prs"]}
        added = 0

        for entry in new_entries:
            if entry.pr_number not in existing_numbers:
                self._data["prs"].append(entry.to_review_entry())
                added += 1
                logger.debug("Added new PR #%d", entry.pr_number)

        if added > 0:
            logger.info("Merged %d new PRs into review file", added)

        return added
