"""Extract PR data from release-notes-draft.json.

Parses the krel-generated JSON file to enrich PR entries with
SIGs, kinds, areas, author info, and the original note text.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class DraftJSONData:
    """Parsed release-notes-draft.json data with lookup methods."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    @classmethod
    def from_file(cls, json_path: str | Path) -> DraftJSONData:
        """Load and parse the release-notes-draft.json file.

        Args:
            json_path: Path to the release-notes-draft.json file.

        Returns:
            DraftJSONData instance.

        Raises:
            FileNotFoundError: If the file doesn't exist.
            json.JSONDecodeError: If the file is not valid JSON.
        """
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"Draft JSON file not found: {path}")

        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        logger.info("Loaded %d PR entries from %s", len(data), path)
        return cls(data)

    def get_pr(self, pr_number: int) -> dict[str, Any] | None:
        """Get the full entry for a PR number.

        Args:
            pr_number: The PR number to look up.

        Returns:
            The PR entry dict, or None if not found.
        """
        return self._data.get(str(pr_number))

    def get_text(self, pr_number: int) -> str:
        """Get the note text for a PR.

        Args:
            pr_number: The PR number.

        Returns:
            The note text, or empty string if not found.
        """
        entry = self.get_pr(pr_number)
        if entry is None:
            return ""
        return entry.get("text", "")

    def get_sigs(self, pr_number: int) -> list[str]:
        """Get the SIG labels for a PR.

        Args:
            pr_number: The PR number.

        Returns:
            List of SIG names, or empty list if not found.
        """
        entry = self.get_pr(pr_number)
        if entry is None:
            return []
        return entry.get("sigs", [])

    def get_kinds(self, pr_number: int) -> list[str]:
        """Get the kind labels for a PR.

        Args:
            pr_number: The PR number.

        Returns:
            List of kind names, or empty list if not found.
        """
        entry = self.get_pr(pr_number)
        if entry is None:
            return []
        return entry.get("kinds", [])

    def get_areas(self, pr_number: int) -> list[str]:
        """Get the area labels for a PR.

        Args:
            pr_number: The PR number.

        Returns:
            List of area names, or empty list if not found.
        """
        entry = self.get_pr(pr_number)
        if entry is None:
            return []
        return entry.get("areas", [])

    def get_author(self, pr_number: int) -> str:
        """Get the author username for a PR.

        Args:
            pr_number: The PR number.

        Returns:
            Author username, or empty string if not found.
        """
        entry = self.get_pr(pr_number)
        if entry is None:
            return ""
        return entry.get("author", "")

    def get_pr_url(self, pr_number: int) -> str:
        """Get the PR URL.

        Args:
            pr_number: The PR number.

        Returns:
            PR URL, or empty string if not found.
        """
        entry = self.get_pr(pr_number)
        if entry is None:
            return ""
        return entry.get("pr_url", "")

    def is_do_not_publish(self, pr_number: int) -> bool:
        """Check if a PR is marked as do_not_publish.

        Args:
            pr_number: The PR number.

        Returns:
            True if the PR should not be published.
        """
        entry = self.get_pr(pr_number)
        if entry is None:
            return False
        return entry.get("do_not_publish", False)

    def all_pr_numbers(self) -> list[int]:
        """Get all PR numbers in the JSON file.

        Returns:
            List of PR numbers.
        """
        numbers = []
        for key in self._data:
            try:
                numbers.append(int(key))
            except ValueError:
                logger.warning("Skipping non-numeric key in JSON: %s", key)
        return numbers
