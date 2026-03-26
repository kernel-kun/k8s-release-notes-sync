"""Extract PR entries from release-notes-draft.md.

Parses the markdown file to extract PR numbers and their associated
note text. Handles the standard krel-generated format where each entry
is a bullet point with a PR link, including multi-line entries where
the note text spans continuation lines.

Multi-line entry example::

    - The `StrictIPCIDRValidation` feature gate to kube-apiserver is now
      enabled by default, meaning that API fields no longer allow IP or CIDR
      values with extraneous leading "0"s. ([#137053](...), [@danwinship](...)) [SIG Network and Testing]
"""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import NamedTuple


class MarkdownPREntry(NamedTuple):
    """A PR entry extracted from the markdown file."""

    pr_number: int
    note_text: str
    section: str  # The "Changes by Kind" section heading


# Regex to match PR links in the format ([#NNNNN](url), [@author](url))
PR_LINK_PATTERN = re.compile(
    r"\(\[#(\d+)\]\(https://github\.com/kubernetes/kubernetes/pull/\d+\)"
)

# Section heading pattern (## or ### or deeper headings)
SECTION_HEADING_PATTERN = re.compile(r"^(#{2,})\s+(.+)$")

# Pattern to detect the start of a new bullet point
BULLET_START_PATTERN = re.compile(r"^(\s*)[-*]\s+")

# Pattern to match the trailing PR link(s), author, and SIG info at the
# end of a note entry.  Captures everything from the first ``([#`` to
# the end of the line (including optional ``[SIG …]`` suffix).
TRAILING_META_PATTERN = re.compile(
    r"\s*"
    r"\("
    r"(?:\[#\d+\]\(https://github\.com/[^)]+\),?\s*)+"  # one or more PR links
    r"(?:\[@[^\]]+\]\([^)]+\)\s*)"                       # author link
    r"\)"
    r"(?:\s*\[SIG [^\]]*\])?"                             # optional SIG suffix
    r"\s*$"
)


def _collect_bullet_blocks(markdown_content: str) -> list[tuple[str, str]]:
    """Collect complete bullet-point blocks from the markdown content.

    Each block is a tuple of ``(section_heading, full_text)`` where
    *full_text* is the concatenated text of the bullet line and all its
    continuation lines (joined with newlines).

    A continuation line is any line that is indented **more than** the
    bullet marker's own leading whitespace, **or** is a blank line that
    appears between indented continuation lines (krel sometimes inserts
    blank lines within a single note).

    For example, given ``" - Foo"`` (1 leading space before the dash),
    any line with > 1 leading space is treated as a continuation.

    Args:
        markdown_content: The full content of release-notes-draft.md.

    Returns:
        List of (section, block_text) tuples in document order.
    """
    blocks: list[tuple[str, str]] = []
    current_section = ""
    current_block_lines: list[str] = []
    # The number of leading whitespace characters before the bullet
    # marker (``-`` or ``*``).  Continuation lines must be indented
    # *more* than this value.
    bullet_leading_ws: int = 0
    # The column where the text starts after the bullet prefix.
    # For ``- Foo`` this is 2; for `` - Foo`` this is 3.
    # Sub-bullets must be indented at least this much.
    bullet_text_col: int = 0

    def _flush() -> None:
        if current_block_lines:
            blocks.append((current_section, "\n".join(current_block_lines)))

    for line in markdown_content.splitlines():
        # Track section headings (## or ### or deeper)
        section_match = SECTION_HEADING_PATTERN.match(line)
        if section_match:
            _flush()
            current_block_lines = []
            current_section = section_match.group(2).strip()
            continue

        # Detect start of a new top-level bullet point.
        # Sub-bullets (indented at or past the parent's text column)
        # are treated as continuation lines, not new blocks.
        bullet_match = BULLET_START_PATTERN.match(line)
        if bullet_match:
            new_bullet_ws = len(bullet_match.group(1))
            # If we're inside a block and this bullet's leading
            # whitespace is at or past the parent bullet's text column,
            # treat it as a sub-bullet (continuation line).
            # Example: parent ``- Foo`` has text_col=2, so a sub-bullet
            # ``    - Bar`` (ws=4 >= 2) is a continuation, but a sibling
            # `` - Baz`` (ws=1 < 2) starts a new block.
            if current_block_lines and new_bullet_ws >= bullet_text_col:
                current_block_lines.append(line)
                continue
            _flush()
            current_block_lines = [line]
            # Record the leading whitespace before the bullet marker.
            # group(1) captures the ``\s*`` before ``[-*]``.
            bullet_leading_ws = new_bullet_ws
            bullet_text_col = bullet_match.end()
            continue

        # If we're inside a bullet block, check for continuation lines.
        # Continuation lines are either:
        #   a) indented more than the bullet marker's leading whitespace, or
        #   b) blank/whitespace-only lines (paragraph breaks within a note)
        if current_block_lines:
            stripped = line.rstrip()
            if stripped == "":
                # Blank line — tentatively include as part of the block.
                # It will be dropped if the next non-blank line is not a
                # continuation, but that's handled by the bullet/section
                # detection above which calls _flush() first.
                current_block_lines.append(line)
                continue

            # Check if the line is indented enough to be a continuation.
            # A continuation must be indented *more* than the bullet
            # marker's own leading whitespace.  For ``- Foo`` (0 leading
            # spaces) any indented line qualifies; for `` - Foo`` (1
            # leading space) the continuation needs >= 2 spaces.
            leading_spaces = len(line) - len(line.lstrip())
            if leading_spaces > bullet_leading_ws:
                current_block_lines.append(line)
                continue

            # Not a continuation — flush the current block and ignore
            # this line (it's likely a non-bullet, non-heading line such
            # as a blank line between sections).
            _flush()
            current_block_lines = []

    # Don't forget the last block
    _flush()

    return blocks


def extract_pr_entries(markdown_content: str) -> OrderedDict[int, MarkdownPREntry]:
    """Extract all PR entries from release-notes-draft.md content.

    Handles both single-line and multi-line bullet entries.  For
    multi-line entries the note text is reconstructed by joining all
    lines and unwrapping the continuation indentation.

    Args:
        markdown_content: The full content of release-notes-draft.md.

    Returns:
        OrderedDict mapping PR number to MarkdownPREntry, preserving
        document order.
    """
    entries: OrderedDict[int, MarkdownPREntry] = OrderedDict()

    for section, block_text in _collect_bullet_blocks(markdown_content):
        # The PR link must be present somewhere in the block
        pr_match = PR_LINK_PATTERN.search(block_text)
        if not pr_match:
            continue

        pr_number = int(pr_match.group(1))
        note_text = _extract_note_text(block_text)

        entries[pr_number] = MarkdownPREntry(
            pr_number=pr_number,
            note_text=note_text,
            section=section,
        )

    return entries


def extract_pr_numbers(markdown_content: str) -> list[int]:
    """Extract just the PR numbers from release-notes-draft.md content.

    Args:
        markdown_content: The full content of release-notes-draft.md.

    Returns:
        List of PR numbers in document order.
    """
    return list(extract_pr_entries(markdown_content).keys())


def _extract_note_text(block_text: str) -> str:
    """Extract the note text from a (possibly multi-line) bullet block.

    Strips the bullet prefix, unwraps continuation-line indentation,
    and removes the trailing PR link / author / SIG metadata.

    Args:
        block_text: The full text of a single bullet block (may contain
            newlines for multi-line entries).

    Returns:
        The cleaned note text with continuation lines joined into a
        single coherent string.  Internal paragraph breaks (blank lines)
        are preserved as ``\\n\\n``.
    """
    lines = block_text.splitlines()
    if not lines:
        return ""

    # Remove the bullet prefix from the first line
    first_line = re.sub(r"^\s*[-*]\s+", "", lines[0])

    # Determine how much indentation to strip from continuation lines.
    # We try to detect the actual indentation of the first non-blank
    # continuation line, falling back to the bullet prefix length.
    bullet_match = BULLET_START_PATTERN.match(lines[0])
    text_indent = bullet_match.end() if bullet_match else 2

    # Check the actual indentation of the first continuation line to
    # handle cases where continuation lines don't align perfectly with
    # the text after the bullet marker (e.g. " - Foo\n  Bar" where
    # the bullet prefix is 3 chars but continuation indent is 2).
    if len(lines) > 1:
        for cont_line in lines[1:]:
            cont_stripped = cont_line.rstrip()
            if cont_stripped:
                actual_indent = len(cont_line) - len(cont_line.lstrip())
                text_indent = min(text_indent, actual_indent)
                break

    # Process continuation lines: strip the leading indentation
    processed: list[str] = [first_line]
    for line in lines[1:]:
        stripped = line.rstrip()
        if stripped == "":
            processed.append("")  # preserve paragraph breaks
        else:
            # Remove the continuation indentation
            if len(line) >= text_indent:
                processed.append(line[text_indent:])
            else:
                processed.append(line.lstrip())

    # Join all lines back together
    full_text = "\n".join(processed)

    # Remove trailing blank lines
    full_text = full_text.rstrip()

    # Remove the trailing PR link(s), author link, and SIG info
    full_text = TRAILING_META_PATTERN.sub("", full_text)

    return full_text.strip()
