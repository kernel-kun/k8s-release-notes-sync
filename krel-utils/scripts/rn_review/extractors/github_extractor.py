"""GitHub API integration for fetching PR descriptions.

Fetches PR body content from the GitHub API and extracts the
"Does this PR introduce a user-facing change?" section.

Includes persistent disk caching to survive rate limits and
script restarts.
"""

from __future__ import annotations

import json as json_module
import logging
import os
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Pattern to find the user-facing change section in PR body
# Matches the question line and the code block that follows it
USER_FACING_CHANGE_PATTERN = re.compile(
    r"(?:^|\n)"
    r"[#]*\s*Does this PR introduce a user-facing change\?"
    r".*?\n"
    r"```(?:release-note)?\s*\n"
    r"(.*?)"
    r"\n```",
    re.DOTALL | re.IGNORECASE,
)

# Alternative pattern: some PRs use a different format
USER_FACING_CHANGE_ALT_PATTERN = re.compile(
    r"```release-note\s*\n"
    r"(.*?)"
    r"\n```",
    re.DOTALL,
)


class RateLimitExhausted(Exception):
    """Raised when GitHub API rate limit is exhausted.

    Attributes:
        reset_time: Unix timestamp when the rate limit resets.
        fetched_so_far: Number of PRs successfully fetched before hitting the limit.
    """

    def __init__(self, reset_time: int, fetched_so_far: int) -> None:
        self.reset_time = reset_time
        self.fetched_so_far = fetched_so_far
        reset_str = time.strftime("%H:%M:%S", time.localtime(reset_time))
        super().__init__(
            f"GitHub API rate limit exhausted. "
            f"Fetched {fetched_so_far} PRs before limit. "
            f"Resets at {reset_str}. "
            f"Set GITHUB_TOKEN env var for 5000 requests/hour."
        )


@dataclass
class PRDescription:
    """Extracted PR description data."""

    pr_number: int
    body: str
    user_facing_change: str
    author: str
    title: str


class DiskCache:
    """Persistent JSON-based cache for PR descriptions.

    Stores fetched PR data on disk so subsequent runs don't
    re-fetch PRs that were already retrieved. This is critical
    for surviving rate limits — if you hit the limit at PR 55/158,
    the next run will skip the first 55 and continue from 56.
    """

    def __init__(self, cache_path: str | Path) -> None:
        """Initialize the disk cache.

        Args:
            cache_path: Path to the cache JSON file.
        """
        self._path = Path(cache_path)
        self._data: dict[int, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Load cache from disk if it exists."""
        if self._path.exists():
            try:
                with open(self._path, encoding="utf-8") as f:
                    raw = json_module.load(f)
                # Keys are strings in JSON, convert to int
                self._data = {int(k): v for k, v in raw.items()}
                logger.info(
                    "Loaded %d cached PR descriptions from %s",
                    len(self._data),
                    self._path,
                )
            except (json_module.JSONDecodeError, ValueError) as e:
                logger.warning("Failed to load cache file %s: %s", self._path, e)
                self._data = {}

    def save(self) -> None:
        """Persist cache to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json_module.dump(self._data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        logger.debug("Saved %d entries to cache %s", len(self._data), self._path)

    def get(self, pr_number: int) -> PRDescription | None:
        """Get a cached PR description.

        Args:
            pr_number: The PR number.

        Returns:
            PRDescription if cached, None otherwise.
        """
        entry = self._data.get(pr_number)
        if entry is None:
            return None
        return PRDescription(**entry)

    def put(self, desc: PRDescription) -> None:
        """Store a PR description in the cache.

        Args:
            desc: The PR description to cache.
        """
        self._data[desc.pr_number] = asdict(desc)

    def has(self, pr_number: int) -> bool:
        """Check if a PR is in the cache."""
        return pr_number in self._data

    def __len__(self) -> int:
        return len(self._data)


class GitHubExtractor:
    """Fetches PR data from the GitHub API.

    Supports both authenticated and unauthenticated requests,
    with rate limiting, retry logic, and persistent disk caching.
    """

    BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: str | None = None,
        owner: str = "kubernetes",
        repo: str = "kubernetes",
        max_retries: int = 3,
        retry_delay: float = 1.0,
        cache_path: str | Path | None = None,
    ) -> None:
        """Initialize the GitHub extractor.

        Args:
            token: GitHub personal access token. If None, reads from
                   GITHUB_TOKEN environment variable.
            owner: Repository owner (default: kubernetes).
            repo: Repository name (default: kubernetes).
            max_retries: Maximum number of retries on failure.
            retry_delay: Base delay between retries (exponential backoff).
            cache_path: Path for persistent disk cache. If None, caching
                        is in-memory only.
        """
        self._token = token or os.environ.get("GITHUB_TOKEN", "")
        self._owner = owner
        self._repo = repo
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._memory_cache: dict[int, PRDescription] = {}
        self._disk_cache: DiskCache | None = None

        if cache_path:
            self._disk_cache = DiskCache(cache_path)

        if not self._token:
            logger.warning(
                "No GitHub token provided. API rate limits will be very low "
                "(60 requests/hour). Set GITHUB_TOKEN environment variable."
            )

    def _get_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "krel-rn-review-utility",
        }
        if self._token:
            headers["Authorization"] = f"token {self._token}"
        return headers

    def _make_request(self, url: str) -> dict[str, Any]:
        """Make an HTTP GET request with retry logic.

        Uses urllib to avoid external dependencies.

        Args:
            url: The full URL to request.

        Returns:
            Parsed JSON response.

        Raises:
            RateLimitExhausted: If rate limit is hit and cannot proceed.
            RuntimeError: If all retries are exhausted.
        """
        import urllib.error
        import urllib.request

        headers = self._get_headers()
        request = urllib.request.Request(url, headers=headers)

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    # Check rate limit headers
                    remaining = response.headers.get("X-RateLimit-Remaining")
                    if remaining and int(remaining) < 10:
                        reset_time = int(
                            response.headers.get("X-RateLimit-Reset", "0")
                        )
                        logger.warning(
                            "GitHub API rate limit low: %s remaining. "
                            "Resets at %s",
                            remaining,
                            time.strftime(
                                "%H:%M:%S", time.localtime(reset_time)
                            ),
                        )

                    return json_module.loads(response.read().decode("utf-8"))

            except urllib.error.HTTPError as e:
                last_error = e
                if e.code == 403:
                    # Rate limited — check reset time
                    reset_time = int(
                        e.headers.get("X-RateLimit-Reset", "0")
                    )
                    remaining = e.headers.get("X-RateLimit-Remaining", "")
                    if remaining == "0":
                        # Truly rate limited — raise immediately
                        raise RateLimitExhausted(
                            reset_time=reset_time,
                            fetched_so_far=0,
                        ) from e
                    # Might be a secondary rate limit, brief wait
                    wait_time = min(max(reset_time - int(time.time()), 1), 60)
                    logger.warning(
                        "Rate limited (403). Waiting %d seconds...", wait_time
                    )
                    time.sleep(wait_time)
                    continue
                elif e.code == 404:
                    raise RuntimeError(
                        f"PR not found at {url}"
                    ) from e
                elif e.code >= 500:
                    delay = self._retry_delay * (2**attempt)
                    logger.warning(
                        "Server error %d, retrying in %.1fs...",
                        e.code,
                        delay,
                    )
                    time.sleep(delay)
                    continue
                else:
                    raise RuntimeError(
                        f"GitHub API error {e.code}: {e.read().decode()}"
                    ) from e

            except urllib.error.URLError as e:
                last_error = e
                delay = self._retry_delay * (2**attempt)
                logger.warning(
                    "Network error: %s, retrying in %.1fs...",
                    e.reason,
                    delay,
                )
                time.sleep(delay)
                continue

        raise RuntimeError(
            f"Failed after {self._max_retries} retries: {last_error}"
        )

    def fetch_pr(self, pr_number: int) -> PRDescription:
        """Fetch a single PR's description from GitHub.

        Checks memory cache, then disk cache, then makes API call.

        Args:
            pr_number: The PR number to fetch.

        Returns:
            PRDescription with extracted data.
        """
        # Check memory cache
        if pr_number in self._memory_cache:
            logger.debug("Memory cache hit for PR #%d", pr_number)
            return self._memory_cache[pr_number]

        # Check disk cache
        if self._disk_cache and self._disk_cache.has(pr_number):
            desc = self._disk_cache.get(pr_number)
            if desc:
                logger.debug("Disk cache hit for PR #%d", pr_number)
                self._memory_cache[pr_number] = desc
                return desc

        # Fetch from API
        url = (
            f"{self.BASE_URL}/repos/{self._owner}/{self._repo}"
            f"/pulls/{pr_number}"
        )
        logger.info("Fetching PR #%d from GitHub API", pr_number)

        data = self._make_request(url)

        body = data.get("body", "") or ""
        user_facing_change = extract_user_facing_change(body)
        author = data.get("user", {}).get("login", "")
        title = data.get("title", "")

        description = PRDescription(
            pr_number=pr_number,
            body=body,
            user_facing_change=user_facing_change,
            author=author,
            title=title,
        )

        # Store in both caches
        self._memory_cache[pr_number] = description
        if self._disk_cache:
            self._disk_cache.put(description)

        return description

    def fetch_prs(
        self,
        pr_numbers: list[int],
        progress_callback: Any | None = None,
    ) -> dict[int, PRDescription]:
        """Fetch multiple PRs from GitHub.

        If rate limit is hit, saves the disk cache and raises
        RateLimitExhausted with the count of PRs fetched so far.
        Re-running the command will resume from where it left off
        thanks to the disk cache.

        Args:
            pr_numbers: List of PR numbers to fetch.
            progress_callback: Optional callable(current, total) for progress.

        Returns:
            Dict mapping PR number to PRDescription.

        Raises:
            RateLimitExhausted: If rate limit is hit mid-fetch.
        """
        results: dict[int, PRDescription] = {}
        total = len(pr_numbers)
        api_calls = 0

        for i, pr_number in enumerate(pr_numbers, 1):
            try:
                was_cached = (
                    pr_number in self._memory_cache
                    or (self._disk_cache and self._disk_cache.has(pr_number))
                )
                results[pr_number] = self.fetch_pr(pr_number)
                if not was_cached:
                    api_calls += 1
            except RateLimitExhausted as e:
                # Save disk cache before propagating
                if self._disk_cache:
                    self._disk_cache.save()
                    logger.info(
                        "Saved %d cached PRs to disk before rate limit exit",
                        len(self._disk_cache),
                    )
                e.fetched_so_far = len(results)
                raise
            except RuntimeError as e:
                logger.error("Failed to fetch PR #%d: %s", pr_number, e)
                results[pr_number] = PRDescription(
                    pr_number=pr_number,
                    body="",
                    user_facing_change="",
                    author="",
                    title="",
                )

            if progress_callback:
                progress_callback(i, total)

            # Small delay between API requests to be respectful
            if not (
                pr_number in self._memory_cache
                or (self._disk_cache and self._disk_cache.has(pr_number))
            ):
                if i < total:
                    time.sleep(0.25)

        # Save disk cache at the end
        if self._disk_cache:
            self._disk_cache.save()

        logger.info(
            "Fetched %d PRs (%d from API, %d from cache)",
            len(results),
            api_calls,
            len(results) - api_calls,
        )

        return results

    @property
    def cache_size(self) -> int:
        """Number of cached PR descriptions (memory + disk)."""
        if self._disk_cache:
            return len(self._disk_cache)
        return len(self._memory_cache)

    def clear_cache(self) -> None:
        """Clear the PR description cache (memory only)."""
        self._memory_cache.clear()


def extract_user_facing_change(body: str) -> str:
    """Extract the user-facing change content from a PR body.

    Looks for the "Does this PR introduce a user-facing change?" section
    and extracts the content from the code block below it.

    Args:
        body: The full PR body text.

    Returns:
        The user-facing change text, or empty string if not found.
    """
    if not body:
        return ""

    # Try the full pattern first (question + code block)
    match = USER_FACING_CHANGE_PATTERN.search(body)
    if match:
        text = match.group(1).strip()
        # Filter out common "no change" markers
        if _is_no_change(text):
            return ""
        return text

    # Fall back to just looking for release-note code blocks
    match = USER_FACING_CHANGE_ALT_PATTERN.search(body)
    if match:
        text = match.group(1).strip()
        if _is_no_change(text):
            return ""
        return text

    return ""


def _is_no_change(text: str) -> bool:
    """Check if the text indicates no user-facing change.

    Args:
        text: The extracted text from the code block.

    Returns:
        True if the text indicates no change.
    """
    normalized = text.lower().strip()
    no_change_markers = [
        "none",
        "n/a",
        "na",
        "no",
        "none.",
        "no change",
        "no user-facing change",
        "no user facing change",
        "not applicable",
        "<!--",
    ]
    return normalized in no_change_markers or normalized.startswith("<!--")
