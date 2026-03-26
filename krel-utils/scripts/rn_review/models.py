"""Data models for the Release Notes Review utility.

Defines TypedDicts and dataclasses used across the tool for type safety
and clear data contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict


class ReviewMetadata(TypedDict):
    """Metadata about the review session."""

    releaseVersion: str
    generatedAt: str
    mode: str  # "diff" or "full"
    oldRef: str
    newRef: str
    totalPRs: int
    reviewedPRs: int
    githubRepo: str


class PRReviewEntry(TypedDict):
    """A single PR entry in the review JSON file.

    Fields:
        prNumber: The PR number.
        prUrl: Full GitHub URL to the PR.
        author: GitHub username of the PR author.
        sigs: List of SIG labels from krel.
        kinds: List of kind labels from krel.
        areas: List of area labels from krel.
        originalNote: The author's original release note text — immutable
            baseline. When --fetch-github is used, this comes from the PR
            body's ```release-note block. Otherwise falls back to the JSON
            text from krel.
        currentDraftNote: The working text — AI/human edits this directly.
        reviewDone: Whether this PR has been reviewed.
        reviewNotes: Optional notes from the reviewer.
    """

    prNumber: int
    prUrl: str
    author: str
    sigs: list[str]
    kinds: list[str]
    areas: list[str]
    originalNote: str
    currentDraftNote: str
    reviewDone: bool
    reviewNotes: str


class ReviewFile(TypedDict):
    """Top-level structure of the review JSON file."""

    metadata: ReviewMetadata
    prs: dict[str, PRReviewEntry]


@dataclass
class PREntry:
    """Internal representation of a PR during extraction.

    Used as an intermediate data structure before writing to the review JSON.
    """

    pr_number: int
    pr_url: str = ""
    author: str = ""
    sigs: list[str] = field(default_factory=list)
    kinds: list[str] = field(default_factory=list)
    areas: list[str] = field(default_factory=list)
    original_note: str = ""
    current_draft_note: str = ""

    def to_review_entry(self) -> PRReviewEntry:
        """Convert to a PRReviewEntry for JSON serialization."""
        return PRReviewEntry(
            prNumber=self.pr_number,
            prUrl=self.pr_url,
            author=self.author,
            sigs=self.sigs,
            kinds=self.kinds,
            areas=self.areas,
            originalNote=self.original_note,
            currentDraftNote=self.current_draft_note,
            reviewDone=False,
            reviewNotes="",
        )


@dataclass
class MapFileData:
    """Data needed to generate a single map YAML file.

    Mirrors the krel ReleaseNotesMap struct fields we use.
    """

    pr_number: int
    text: str
    sigs: list[str]
    kinds: list[str]
    areas: list[str]
    pr_body: str = ""  # Always empty string per convention
