"""Tests for markdown_extractor multi-line note handling."""

from __future__ import annotations

from .markdown_extractor import extract_pr_entries, _extract_note_text


# ---------------------------------------------------------------------------
# Test data: the exact example from the bug report
# ---------------------------------------------------------------------------
MULTILINE_EXAMPLE = """\
## Changes by Kind

### Feature

- The ConstrainedImpersonation feature is now beta and enabled by default. ([#137609](https://github.com/kubernetes/kubernetes/pull/137609), [@enj](https://github.com/enj)) [SIG API Machinery and Testing]
- The `StrictIPCIDRValidation` feature gate to kube-apiserver is now
  enabled by default, meaning that API fields no longer allow IP or CIDR
  values with extraneous leading "0"s (e.g., `010.000.000.005` rather than
  `10.0.0.5`) or CIDR subnet/mask values with ambiguous semantics (e.g.,
  `192.168.0.5/24` rather than `192.168.0.0/24` or `192.168.0.5/32`). ([#137053](https://github.com/kubernetes/kubernetes/pull/137053), [@danwinship](https://github.com/danwinship)) [SIG Network and Testing]
"""

# ---------------------------------------------------------------------------
# Test data: multi-line with blank lines (paragraph breaks within a note)
# ---------------------------------------------------------------------------
MULTILINE_WITH_BLANKS = """\
## Changes by Kind

### Feature

- A new alpha feature gate, `MutableCSINodeAllocatableCount`, has been introduced.
  
  When this feature gate is enabled, the `CSINode.Spec.Drivers[*].Allocatable.Count` field becomes mutable, and a new field, `NodeAllocatableUpdatePeriodSeconds`, is available in the `CSIDriver` object. This allows periodic updates to a node's reported allocatable volume capacity, preventing stateful pods from becoming stuck due to outdated information that kube-scheduler relies on. ([#130007](https://github.com/kubernetes/kubernetes/pull/130007), [@torredil](https://github.com/torredil)) [SIG Apps, Node, Scheduling and Storage]
"""

# ---------------------------------------------------------------------------
# Test data: single-line entry (should still work)
# ---------------------------------------------------------------------------
SINGLE_LINE_EXAMPLE = """\
## Changes by Kind

### Bug or Regression

- Fixed a bug in the scheduler. ([#12345](https://github.com/kubernetes/kubernetes/pull/12345), [@dev](https://github.com/dev)) [SIG Scheduling]
"""

# ---------------------------------------------------------------------------
# Test data: multi-line with sub-bullets
# ---------------------------------------------------------------------------
MULTILINE_WITH_SUBBULLETS = """\
## Changes by Kind

### Feature

- Graduated image volume sources to beta:
    - Allowed `subPath`/`subPathExpr` for image volumes
    - Added kubelet metrics `kubelet_image_volume_requested_total`, `kubelet_image_volume_mounted_succeed_total` and `kubelet_image_volume_mounted_errors_total` ([#130135](https://github.com/kubernetes/kubernetes/pull/130135), [@saschagrunert](https://github.com/saschagrunert)) [SIG API Machinery, Apps, Node and Testing]
"""

# ---------------------------------------------------------------------------
# Test data: entry with multiple PR links
# ---------------------------------------------------------------------------
MULTI_PR_LINKS = """\
## Changes by Kind

### Feature

- When the `StrictIPCIDRValidation` feature gate is enabled, Kubernetes will be
  slightly stricter about what values will be accepted as IP addresses. ([#122550](https://github.com/kubernetes/kubernetes/pull/122550), [#128786](https://github.com/kubernetes/kubernetes/pull/128786), [@danwinship](https://github.com/danwinship)) [SIG API Machinery, Apps, Network, Node, Scheduling and Testing]
"""


def test_single_line_entry():
    """Single-line entries should still be extracted correctly."""
    entries = extract_pr_entries(SINGLE_LINE_EXAMPLE)
    assert 12345 in entries
    entry = entries[12345]
    assert entry.note_text == "Fixed a bug in the scheduler."
    assert entry.section == "Bug or Regression"


def test_multiline_entry_from_bug_report():
    """Multi-line entries from the bug report should be fully captured."""
    entries = extract_pr_entries(MULTILINE_EXAMPLE)

    # Single-line entry should work
    assert 137609 in entries
    assert entries[137609].note_text == (
        "The ConstrainedImpersonation feature is now beta and enabled by default."
    )

    # Multi-line entry should capture the full text
    assert 137053 in entries
    note = entries[137053].note_text
    assert note.startswith("The `StrictIPCIDRValidation` feature gate")
    assert "`192.168.0.5/32`)" in note
    # Should NOT contain the PR link or SIG info
    assert "137053" not in note
    assert "[SIG" not in note
    assert "[@danwinship]" not in note


def test_multiline_with_blank_lines():
    """Multi-line entries with blank paragraph breaks should be captured."""
    entries = extract_pr_entries(MULTILINE_WITH_BLANKS)
    assert 130007 in entries
    note = entries[130007].note_text
    assert note.startswith("A new alpha feature gate")
    assert "NodeAllocatableUpdatePeriodSeconds" in note
    # Should NOT contain the PR link
    assert "130007" not in note


def test_multiline_with_subbullets():
    """Multi-line entries with sub-bullets should be captured."""
    entries = extract_pr_entries(MULTILINE_WITH_SUBBULLETS)
    assert 130135 in entries
    note = entries[130135].note_text
    assert note.startswith("Graduated image volume sources to beta:")
    assert "subPath" in note


def test_multi_pr_links():
    """Entries with multiple PR links should use the first PR number."""
    entries = extract_pr_entries(MULTI_PR_LINKS)
    assert 122550 in entries
    note = entries[122550].note_text
    assert note.startswith("When the `StrictIPCIDRValidation`")
    assert "122550" not in note


# ---------------------------------------------------------------------------
# Test data: leading-space bullet (e.g. " - Foo")
# ---------------------------------------------------------------------------
LEADING_SPACE_BULLET = """\
## Changes by Kind

### Action Required

 - Renamed `UpdatePodTolerations` action type to `UpdatePodToleration`.
  Action required for custom plugin developers to update their code to follow the rename. ([#129023](https://github.com/kubernetes/kubernetes/pull/129023), [@zhifei92](https://github.com/zhifei92)) [SIG Scheduling and Testing]
"""


def test_leading_space_bullet():
    """Bullets with leading spaces should still capture continuation lines."""
    entries = extract_pr_entries(LEADING_SPACE_BULLET)
    assert 129023 in entries
    note = entries[129023].note_text
    assert "Renamed" in note
    assert "Action required" in note
    assert "129023" not in note


def test_section_tracking():
    """Section headings should be tracked correctly."""
    entries = extract_pr_entries(MULTILINE_EXAMPLE)
    assert entries[137609].section == "Feature"
    assert entries[137053].section == "Feature"


def test_entry_count():
    """The correct number of entries should be extracted."""
    entries = extract_pr_entries(MULTILINE_EXAMPLE)
    assert len(entries) == 2


def test_extract_note_text_single_line():
    """_extract_note_text should handle a single bullet line."""
    line = "- Fixed a bug in the scheduler. ([#12345](https://github.com/kubernetes/kubernetes/pull/12345), [@dev](https://github.com/dev)) [SIG Scheduling]"
    result = _extract_note_text(line)
    assert result == "Fixed a bug in the scheduler."


def test_extract_note_text_multiline():
    """_extract_note_text should handle multi-line block text."""
    block = (
        "- The `StrictIPCIDRValidation` feature gate to kube-apiserver is now\n"
        "  enabled by default, meaning that API fields no longer allow IP or CIDR\n"
        "  values with extraneous leading \"0\"s. ([#137053](https://github.com/kubernetes/kubernetes/pull/137053), [@danwinship](https://github.com/danwinship)) [SIG Network and Testing]"
    )
    result = _extract_note_text(block)
    assert result.startswith("The `StrictIPCIDRValidation` feature gate")
    assert 'enabled by default' in result
    assert 'extraneous leading "0"s.' in result
    assert "137053" not in result


if __name__ == "__main__":
    test_single_line_entry()
    test_multiline_entry_from_bug_report()
    test_multiline_with_blank_lines()
    test_multiline_with_subbullets()
    test_multi_pr_links()
    test_leading_space_bullet()
    test_section_tracking()
    test_entry_count()
    test_extract_note_text_single_line()
    test_extract_note_text_multiline()
    print("All tests passed!")
