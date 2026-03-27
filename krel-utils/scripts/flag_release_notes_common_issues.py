#!/usr/bin/env python3
"""
Release Notes Diff Review Tool for Kubernetes sig-release.

Compares two versions of a release-notes-draft.md file (typically HEAD vs HEAD~)
and produces a structured review report identifying:
  - Removed PRs
  - Content-modified PRs
  - SIG-tag-only changes
  - Reordered PRs
  - Newly added PRs
  - Guideline violations (missing periods, wrong tense, missing backticks, etc.)

Usage:
  --old-ref / --new-ref accept any valid git ref: commit SHAs, branch names,
  tags, HEAD~N, etc. They are passed directly to `git show <ref>:<path>`.

  # Compare last commit vs current (default: HEAD~ vs HEAD):
  python3 review_release_notes_diff.py --repo-dir /path/to/sig-release

  # Compare two commits:
  python3 review_release_notes_diff.py --repo-dir /path/to/sig-release \
      --old-ref abc1234 --new-ref def5678

  # Compare two branches (e.g. successive release-notes drafts):
  python3 review_release_notes_diff.py --repo-dir /path/to/sig-release \
      --old-ref release-notes-draft-v1.36.0-alpha.2 \
      --new-ref release-notes-draft-v1.36.0-beta.0

  # Compare a branch against a tag:
  python3 review_release_notes_diff.py --repo-dir /path/to/sig-release \
      --old-ref v1.35.0 --new-ref release-notes-draft-v1.36.0-beta.0

  # Compare N commits back:
  python3 review_release_notes_diff.py --repo-dir /path/to/sig-release \
      --old-ref HEAD~3 --new-ref HEAD

  # Compare two local files on disk (no git required):
  python3 review_release_notes_diff.py --old-file /tmp/old.md --new-file /tmp/new.md

  # Specify output file:
  python3 review_release_notes_diff.py --repo-dir /path/to/sig-release -o review-output.md

  # Specify the release notes path within the repo:
  python3 review_release_notes_diff.py --repo-dir /path/to/sig-release \
      --notes-path releases/release-1.36/release-notes/release-notes-draft.md

  Note: both --old-ref and --new-ref must point to refs where --notes-path exists.
  If the file was created on a feature branch, use that branch (not master) as a ref.
"""

import argparse
import os
import re
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Extraction helpers
# ---------------------------------------------------------------------------


def extract_pr_entries(text: str) -> OrderedDict:
    """
    Parse release-notes markdown and return an OrderedDict keyed by PR number.
    Each value is the full text of that bullet entry (may be multi-line).
    Preserves insertion order so we can detect reordering.
    """
    entries: OrderedDict = OrderedDict()
    lines = text.split("\n")
    current_entry: list[str] = []
    current_pr: str | None = None

    for line in lines:
        # New bullet point
        if line.startswith("- ") or line.startswith(" - "):
            # Save previous entry
            if current_pr and current_entry:
                entries[current_pr] = "\n".join(current_entry)
            current_entry = [line]
            pr_match = re.search(r"\[#(\d+)\]", line)
            current_pr = pr_match.group(1) if pr_match else None
        elif current_entry and (line.startswith("  ") or line == ""):
            if line == "" and current_pr:
                entries[current_pr] = "\n".join(current_entry)
                current_entry = []
                current_pr = None
            elif line.startswith("  "):
                current_entry.append(line)
        else:
            if current_pr and current_entry:
                entries[current_pr] = "\n".join(current_entry)
            current_entry = []
            current_pr = None

    # Last entry
    if current_pr and current_entry:
        entries[current_pr] = "\n".join(current_entry)

    return entries


def extract_section_order(text: str) -> dict[str, list[str]]:
    """
    Return a dict mapping section headings to the ordered list of PR numbers
    found under that section.
    """
    sections: dict[str, list[str]] = {}
    current_section = "preamble"
    sections[current_section] = []

    for line in text.split("\n"):
        heading_match = re.match(r"^#{1,4}\s+(.+)", line)
        if heading_match:
            current_section = heading_match.group(1).strip()
            sections.setdefault(current_section, [])
            continue
        pr_match = re.search(r"\[#(\d+)\]", line)
        if pr_match and (line.startswith("- ") or line.startswith(" - ")):
            sections[current_section].append(pr_match.group(1))

    return sections


def git_show_file(repo_dir: str, ref: str, filepath: str) -> str:
    """Run git show <ref>:<filepath> and return the content."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{filepath}"],
        capture_output=True,
        text=True,
        cwd=repo_dir,
    )
    if result.returncode != 0:
        print(
            f"ERROR: git show {ref}:{filepath} failed:\n{result.stderr}",
            file=sys.stderr,
        )
        sys.exit(1)
    return result.stdout


def git_log_oneline(repo_dir: str, count: int = 5) -> str:
    """Return recent git log for context."""
    result = subprocess.run(
        ["git", "log", f"--oneline", f"-{count}"],
        capture_output=True,
        text=True,
        cwd=repo_dir,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# Guideline checks
# ---------------------------------------------------------------------------

PRESENT_TENSE_STARTERS = [
    "Add ",
    "Allow ",
    "Adjust ",
    "Bump ",
    "Cap ",
    "Change ",
    "Create ",
    "Disable ",
    "Disallow ",
    "Enable ",
    "Ensure ",
    "Ensures ",
    "Explicitly ",
    "Extend ",
    "Fix ",
    "Fixes ",
    "Graduate ",
    "Improve ",
    "Instrument ",
    "Integrate ",
    "Introduce ",
    "Mark ",
    "Preserve ",
    "Promote ",
    "Reduce ",
    "Reflecting ",
    "Remove ",
    "Removes ",
    "Rename ",
    "Revert ",
    "Support ",
    "Truncate ",
    "Truncates ",
    "Update ",
    "Writes ",
    "Adding ",
    "Allowing ",
]

# Words that look present-tense but are actually fine
PRESENT_TENSE_EXCEPTIONS = [
    "Previously,",
    "Kubernetes is now",
    "The ",
    "DRA ",
    "DRAConsumableCapacity",
    "Feature gate",
    "PLEGOnDemandRelist",
    "Config.",
    "Slow requests",
    "Kubelet now",
    "Kubelet:",
    "Kube-",
    "Client-go:",
    "Cri-",
    "Garbage collector",
    "Validation messages",
    "Writes to the ServiceCIDR",
]


def strip_bullet(text: str) -> str:
    """Remove leading '- ' or ' - ' from a bullet entry."""
    t = text.strip()
    if t.startswith("- "):
        return t[2:]
    if t.startswith(" - "):
        return t[3:]
    return t


def check_missing_sig(entry_text: str) -> bool:
    """Return True if the entry is missing a trailing [SIG ...] suffix."""
    stripped = entry_text.rstrip()
    sig_pattern = re.compile(r"\[SIG\s+[^\]]+\]\s*$")
    return not sig_pattern.search(stripped)


def check_missing_period(entry_text: str) -> bool:
    """Return True if the entry is missing a trailing period before the PR link."""
    # The text before the PR link should end with a period, or the whole line
    # should end with a period after the SIG tag.
    stripped = entry_text.rstrip()
    # Check if ends with ]) or ]) [SIG ...] — those are fine structurally
    # But the actual note text before the PR link should end with period
    # Find the PR link
    pr_link_match = re.search(r"\(\[#\d+\]", stripped)
    if pr_link_match:
        before_link = stripped[: pr_link_match.start()].rstrip()
        if before_link and not before_link.endswith("."):
            return True
    return False


def check_present_tense(entry_text: str) -> str | None:
    """Return the problematic starter if the entry uses present tense, else None."""
    content = strip_bullet(entry_text).split("\n")[0]  # first line only

    # Skip exceptions
    for exc in PRESENT_TENSE_EXCEPTIONS:
        if content.startswith(exc):
            return None

    for starter in PRESENT_TENSE_STARTERS:
        if content.startswith(starter):
            return starter.strip()
    return None


def check_missing_backticks(entry_text: str) -> list[str]:
    """Return list of terms that should probably be in backticks but aren't."""
    issues = []
    content = strip_bullet(entry_text)

    # Feature gates: UpperCamelCase words that look like feature gates
    feature_gate_pattern = re.compile(
        r"(?<![`\w])([A-Z][a-z]+(?:[A-Z][a-z]+){2,})(?![`\w])"
    )
    for match in feature_gate_pattern.finditer(content):
        term = match.group(1)
        # Skip known API objects and common words
        if term in (
            "Kubernetes",
            "CoreDNS",
            "ResourceSlice",
            "ResourceClaims",
            "PodGroup",
            "StatefulSet",
            "EndpointSlice",
            "PersistentVolumeClaim",
            "PersistentVolume",
            "ConfigMap",
            "DaemonSet",
            "Deployment",
            "CronJob",
            "HorizontalPodAutoscaler",
            "PodDisruptionBudget",
            "CustomResourceDefinition",
            "IngressClass",
            "PodCertificateRequest",
            "VolumeAttachment",
            "PodGroupTemplate",
            "PodGroupState",
            "PodGroupInfo",
            "AllocationModeAll",
            "PrioritizedList",
            "ImageVolume",
            "ProcMountType",
            "WebSocket",
        ):
            continue
        # Likely a feature gate
        if len(term) > 10:
            issues.append(f"Feature gate `{term}` may need backticks")

    # Metric names: words with underscores that aren't in backticks
    metric_pattern = re.compile(r"(?<![`\w])(\w+_\w+(?:_\w+)*)(?![`\w])")
    for match in metric_pattern.finditer(content):
        term = match.group(1)
        if term.startswith("v1") or term.startswith("k8s"):
            continue
        if "_" in term and not term.startswith("@"):
            # Check it's not already inside backticks
            start = match.start()
            before = content[:start]
            if before.count("`") % 2 == 0:  # even = not inside backticks
                issues.append(f"Metric/identifier `{term}` may need backticks")

    # CLI flags (--foo, --foo-bar) that aren't in backticks
    flag_pattern = re.compile(r"(?<!`)--[a-zA-Z][a-zA-Z0-9-]*(?!`)")
    for match in flag_pattern.finditer(content):
        flag = match.group(0)
        start = match.start()
        before = content[:start]
        if before.count("`") % 2 == 0:  # not inside backticks
            issues.append(f"Flag `{flag}` should be wrapped in backticks")

    # Single-quoted terms that should be backticked
    single_quote_pattern = re.compile(r"'([^']+)'")
    for match in single_quote_pattern.finditer(content):
        term = match.group(1)
        if "_" in term or term.startswith("--") or term.startswith("/"):
            issues.append(f"'{term}' should use backticks instead of single quotes")

    return issues


def check_component_names(entry_text: str) -> list[str]:
    """Check for incorrect component name usage."""
    issues = []
    content = strip_bullet(entry_text)

    # coredns should be CoreDNS
    if re.search(r"\bcoredns\b", content, re.IGNORECASE):
        if "CoreDNS" not in content:
            issues.append("Use 'CoreDNS' instead of 'coredns'")

    # apiserver without kube- prefix (but not in compound like kube-apiserver)
    if re.search(r"(?<!\bkube-)\bapiserver\b", content):
        issues.append("Use 'kube-apiserver' instead of 'apiserver'")

    return issues


def check_version_format(entry_text: str) -> list[str]:
    """Check version numbers for missing v prefix or backticks.

    Catches patterns like: 1.36, 1.36.0, v1.36, v1.36.0, v1.36.0-rc.1
    and flags if they are missing backticks or a `v` prefix.

    Skips false positives from:
      - API group versions (v1, v1beta1, v1alpha2, v2)
      - Go versions (go1.23.4, Go 1.23)
      - IP addresses (127.0.0.1)
      - Small floating-point-like numbers (0.5, 2.0) where major < 1 or
        minor is a single digit with no patch — unlikely to be release versions
      - Versions already inside backticks or markdown link text
    """
    issues = []
    content = strip_bullet(entry_text)

    # Match version-like strings: optional v prefix, major.minor with optional
    # .patch and optional pre-release suffix (-alpha.0, -rc.1, -beta.2, etc.)
    ver_pattern = re.compile(
        r"(?<![`\w/\-.])"  # not preceded by backtick, word char, slash, dash, dot
        r"(v?)"  # group 1: optional v prefix
        r"(\d+\.\d+(?:\.\d+)?)"  # group 2: major.minor[.patch]
        r"((?:-(?:alpha|beta|rc)\.\d+)?)"  # group 3: optional pre-release tag
        r"(?![`\w/\-.])"  # not followed by backtick, word char, slash, dash, dot
    )

    for match in ver_pattern.finditer(content):
        v_prefix = match.group(1)
        ver_digits = match.group(2)
        prerelease = match.group(3)
        full = match.group(0)
        start = match.start()

        # --- False-positive filters ---

        # 1. IP addresses: 4 dot-separated octets (e.g. 127.0.0.1)
        #    If the match plus surrounding chars form an IP-like pattern, skip
        ip_region = content[max(0, start - 4) : match.end() + 4]
        if re.search(r"\d+\.\d+\.\d+\.\d+", ip_region):
            continue

        # 3. API group versions like v1, v2, v1beta1, v1alpha2, v2beta2
        #    These are Kubernetes API versions, not release versions
        after_end = content[match.end() : match.end() + 10]
        if v_prefix == "v" and re.match(r"^\d+$", ver_digits) and not prerelease:
            continue  # bare v1, v2 — API version
        if v_prefix == "v" and re.match(r"^\d+(alpha|beta)\d*", after_end):
            continue  # v1beta1, v2alpha1 etc.

        # 4. Small floating-point-like numbers that aren't release versions
        #    e.g. 0.5, 2.0 — skip when major is 0, or it looks like a plain decimal
        parts = ver_digits.split(".")
        major = int(parts[0])
        if major == 0:
            continue  # 0.x.x is not a Kubernetes release version

        # 5. Skip if inside a markdown link text [v1.36.0](url)
        #    Check for ] immediately after the match and ( after that
        after_match = content[match.end() : match.end() + 2]
        if after_match.startswith("]("):
            continue

        # 6. Skip if inside a markdown link URL — look for ](http before our position
        #    A rough heuristic: if the last "(" before us has no closing ")" and
        #    was preceded by "]"
        last_open_paren = content.rfind("(", 0, start)
        if last_open_paren > 0 and content[last_open_paren - 1] == "]":
            # We're likely inside the URL part of [text](url...version...)
            closing_paren = content.find(")", start)
            if closing_paren != -1:
                continue

        # --- Check backticks ---
        before = content[:start]
        inside_backticks = before.count("`") % 2 == 1

        missing_v = not v_prefix
        missing_backticks = not inside_backticks

        ver_with_pre = ver_digits + prerelease

        if missing_v and missing_backticks:
            issues.append(
                f"Version '{ver_with_pre}' should be '`v{ver_with_pre}`' "
                f"(missing both `v` prefix and backticks)"
            )
        elif missing_v:
            issues.append(
                f"Version `{ver_with_pre}` should be `v{ver_with_pre}` "
                f"(missing `v` prefix)"
            )
        elif missing_backticks:
            issues.append(f"Version '{full}' should be wrapped in backticks: `{full}`")

    # Second pass: catch versions inside backticks that are missing the v prefix.
    # The main regex excludes backtick-adjacent matches via its lookarounds,
    # so we need a dedicated pattern for the `1.36.0` -> `v1.36.0` case.
    backticked_ver_pattern = re.compile(
        r"`"
        r"(\d+\.\d+(?:\.\d+)?)"  # major.minor[.patch] without v
        r"((?:-(?:alpha|beta|rc)\.\d+)?)"  # optional pre-release
        r"`"
    )
    for match in backticked_ver_pattern.finditer(content):
        ver_digits = match.group(1)
        prerelease = match.group(2)
        parts = ver_digits.split(".")
        major = int(parts[0])
        if major == 0:
            continue
        ver_with_pre = ver_digits + prerelease
        issues.append(
            f"Version `{ver_with_pre}` should be `v{ver_with_pre}` "
            f"(missing `v` prefix)"
        )

    return issues


def find_contradictory_notes(entries: OrderedDict) -> list[tuple[str, str, str]]:
    """
    Find pairs of PRs that appear to contradict each other
    (e.g., add + revert, or multiple Go version bumps).
    Returns list of (pr1, pr2, reason).
    """
    contradictions = []
    texts = {pr: strip_bullet(text) for pr, text in entries.items()}

    # Look for REVERT notes
    for pr, text in texts.items():
        revert_match = re.search(
            r"(?:reverts?|REVERT)\s*(?:#|PR\s*#?)(\d+)", text, re.IGNORECASE
        )
        if revert_match:
            reverted_pr = revert_match.group(1)
            if reverted_pr in entries:
                contradictions.append(
                    (reverted_pr, pr, "Revert pair — net effect may be zero")
                )

    # Look for multiple Go version bumps
    go_versions = []
    for pr, text in texts.items():
        go_match = re.search(
            r"(?:built (?:with|using)|Go)\s+(?:`?v?)(\d+\.\d+\.\d+)", text
        )
        if go_match:
            go_versions.append((pr, go_match.group(1)))
    if len(go_versions) > 1:
        prs = [gv[0] for gv in go_versions]
        contradictions.append(
            (prs[0], prs[-1], f"Multiple Go version bumps — only latest should remain")
        )

    return contradictions


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    old_text: str,
    new_text: str,
    old_ref: str,
    new_ref: str,
    notes_path: str,
) -> str:
    """Generate the full markdown review report."""
    old_entries = extract_pr_entries(old_text)
    new_entries = extract_pr_entries(new_text)

    old_prs = set(old_entries.keys())
    new_prs = set(new_entries.keys())

    removed_prs = old_prs - new_prs
    added_prs = new_prs - old_prs
    common_prs = old_prs & new_prs

    # Classify modifications
    sig_only_changes = []
    content_changes = []
    unchanged_prs = []

    for pr in sorted(common_prs):
        old_text_pr = old_entries[pr].strip()
        new_text_pr = new_entries[pr].strip()
        if old_text_pr == new_text_pr:
            unchanged_prs.append(pr)
            continue

        old_no_sig = re.sub(r"\s*\[SIG [^\]]+\]\s*$", "", old_text_pr).strip()
        new_no_sig = re.sub(r"\s*\[SIG [^\]]+\]\s*$", "", new_text_pr).strip()

        if old_no_sig == new_no_sig:
            old_sig = re.search(r"\[SIG [^\]]+\]", old_text_pr)
            new_sig = re.search(r"\[SIG [^\]]+\]", new_text_pr)
            sig_only_changes.append(
                {
                    "pr": pr,
                    "old_sig": old_sig.group(0) if old_sig else "None",
                    "new_sig": new_sig.group(0) if new_sig else "None",
                }
            )
        else:
            content_changes.append(
                {
                    "pr": pr,
                    "old": old_text_pr,
                    "new": new_text_pr,
                }
            )

    # Detect reordering
    old_sections = extract_section_order(old_text)
    new_sections = extract_section_order(new_text)
    reordered_prs = []
    for section in set(old_sections.keys()) & set(new_sections.keys()):
        old_order = [p for p in old_sections[section] if p in new_prs]
        new_order = [p for p in new_sections[section] if p in old_prs]
        # Find PRs whose relative order changed
        common_in_section = [p for p in old_order if p in set(new_order)]
        new_common = [p for p in new_order if p in set(old_order)]
        if common_in_section != new_common:
            for p in common_in_section:
                if (
                    common_in_section.index(p) != new_common.index(p)
                    if p in new_common
                    else True
                ):
                    reordered_prs.append((p, section))

    # Guideline checks: missing SIG runs on ALL PRs in new version
    missing_sigs = []
    for pr in sorted(new_prs):
        text = new_entries[pr]
        if check_missing_sig(text):
            missing_sigs.append(pr)

    # Guideline checks on new entries
    missing_periods = []
    present_tense_issues = []
    backtick_issues = []
    component_issues = []
    version_issues = []

    for pr in sorted(added_prs):
        text = new_entries[pr]

        if check_missing_period(text):
            missing_periods.append(pr)

        tense = check_present_tense(text)
        if tense:
            present_tense_issues.append((pr, tense))

        bt = check_missing_backticks(text)
        if bt:
            backtick_issues.append((pr, bt))

        comp = check_component_names(text)
        if comp:
            component_issues.append((pr, comp))

        ver = check_version_format(text)
        if ver:
            version_issues.append((pr, ver))

    contradictions = find_contradictory_notes(new_entries)

    # Build report
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = []
    lines.append(f"# Release Notes Diff Review Report")
    lines.append(f"")
    lines.append(f"**Generated:** {now}")
    lines.append(f"**Old ref:** `{old_ref}` | **New ref:** `{new_ref}`")
    lines.append(f"**File:** `{notes_path}`")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # Summary
    lines.append(f"## Summary")
    lines.append(f"")
    lines.append(f"| Category | Count |")
    lines.append(f"|----------|-------|")
    lines.append(f"| PRs in old version | {len(old_prs)} |")
    lines.append(f"| PRs in new version | {len(new_prs)} |")
    lines.append(f"| Newly added PRs | {len(added_prs)} |")
    lines.append(f"| Removed PRs | {len(removed_prs)} |")
    lines.append(f"| Modified PRs (SIG tag only) | {len(sig_only_changes)} |")
    lines.append(f"| Modified PRs (content changed) | {len(content_changes)} |")
    lines.append(f"| Unchanged PRs | {len(unchanged_prs)} |")
    lines.append(f"| Reordered PRs | {len(reordered_prs)} |")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # Part 1: Removed PRs
    lines.append(f"## 1. Removed PRs")
    lines.append(f"")
    if removed_prs:
        for pr in sorted(removed_prs):
            text = old_entries[pr][:200].replace("\n", " ")
            lines.append(f"- **PR #{pr}**: {text}...")
    else:
        lines.append(f"None.")
    lines.append(f"")

    # Part 2: Content-modified PRs
    lines.append(f"## 2. Content-Modified PRs")
    lines.append(f"")
    if content_changes:
        for item in content_changes:
            lines.append(f"### PR #{item['pr']}")
            lines.append(f"")
            lines.append(f"**OLD:**")
            lines.append(f"```")
            lines.append(item["old"])
            lines.append(f"```")
            lines.append(f"**NEW:**")
            lines.append(f"```")
            lines.append(item["new"])
            lines.append(f"```")
            lines.append(f"")
    else:
        lines.append(f"None.")
    lines.append(f"")

    # Part 3: SIG-tag-only changes
    lines.append(f"## 3. SIG-Tag-Only Changes ({len(sig_only_changes)} PRs)")
    lines.append(f"")
    if sig_only_changes:
        lines.append(f"| PR | Old SIG | New SIG |")
        lines.append(f"|----|---------|---------|")
        for item in sig_only_changes:
            lines.append(f"| #{item['pr']} | {item['old_sig']} | {item['new_sig']} |")
    else:
        lines.append(f"None.")
    lines.append(f"")

    # Part 4: Reordered PRs
    lines.append(f"## 4. Reordered PRs")
    lines.append(f"")
    if reordered_prs:
        for pr, section in reordered_prs:
            lines.append(f"- PR #{pr} reordered within section: **{section}**")
    else:
        lines.append(f"None.")
    lines.append(f"")

    # Part 5: Newly added PRs
    lines.append(f"## 5. Newly Added PRs ({len(added_prs)})")
    lines.append(f"")
    for pr in sorted(added_prs):
        text = new_entries[pr][:200].replace("\n", " ")
        lines.append(f"- **PR #{pr}**: {text}")
    lines.append(f"")
    lines.append(f"---")
    lines.append(f"")

    # Part 6: Guideline violations
    lines.append(f"## 6. Guideline Violations")
    lines.append(f"")

    # 6.1 Missing SIG tags (checks ALL PRs in new version)
    lines.append(f"### 6.1 Missing `[SIG ...]` Suffix ({len(missing_sigs)} PRs)")
    lines.append(f"")
    if missing_sigs:
        lines.append(f"| # | PR | Description |")
        lines.append(f"|---|-----|-------------|")
        for i, pr in enumerate(missing_sigs, 1):
            desc_text = strip_bullet(new_entries[pr]).split("\n")[0]
            desc_match = re.match(r"^(.+?)\s*\(\[#\d+\]", desc_text)
            desc = desc_match.group(1) if desc_match else desc_text[:80]
            if len(desc) > 80:
                desc = desc[:77] + "..."
            pr_link = f"[#{pr}](https://github.com/kubernetes/kubernetes/pull/{pr})"
            lines.append(f"| {i} | {pr_link} | {desc} |")
    else:
        lines.append(f"None.")
    lines.append(f"")

    # 6.2 Missing periods (new PRs only)
    lines.append(f"### 6.2 Missing Trailing Period ({len(missing_periods)} PRs)")
    lines.append(f"")
    if missing_periods:
        for pr in missing_periods:
            text = strip_bullet(new_entries[pr]).split("\n")[0][:120]
            lines.append(f"- PR #{pr}: `{text}...`")
    else:
        lines.append(f"None.")
    lines.append(f"")

    # 6.3 Present tense
    lines.append(
        f"### 6.3 Present Tense Instead of Past Tense ({len(present_tense_issues)} PRs)"
    )
    lines.append(f"")
    if present_tense_issues:
        lines.append(f"| PR | Starts With |")
        lines.append(f"|----|-------------|")
        for pr, starter in present_tense_issues:
            lines.append(f"| #{pr} | `{starter}` |")
    else:
        lines.append(f"None.")
    lines.append(f"")

    # 6.4 Missing backticks
    lines.append(f"### 6.4 Missing Backticks ({len(backtick_issues)} PRs)")
    lines.append(f"")
    if backtick_issues:
        for pr, issues in backtick_issues:
            for issue in issues:
                lines.append(f"- PR #{pr}: {issue}")
    else:
        lines.append(f"None.")
    lines.append(f"")

    # 6.5 Component name issues
    lines.append(f"### 6.5 Component Name Issues ({len(component_issues)} PRs)")
    lines.append(f"")
    if component_issues:
        for pr, issues in component_issues:
            for issue in issues:
                lines.append(f"- PR #{pr}: {issue}")
    else:
        lines.append(f"None.")
    lines.append(f"")

    # 6.6 Version format issues
    lines.append(f"### 6.6 Version Format Issues ({len(version_issues)} PRs)")
    lines.append(f"")
    if version_issues:
        for pr, issues in version_issues:
            for issue in issues:
                lines.append(f"- PR #{pr}: {issue}")
    else:
        lines.append(f"None.")
    lines.append(f"")

    # 6.7 Contradictory notes
    lines.append(f"### 6.7 Contradictory/Duplicate Notes ({len(contradictions)} sets)")
    lines.append(f"")
    if contradictions:
        for pr1, pr2, reason in contradictions:
            lines.append(f"- PR #{pr1} ↔ PR #{pr2}: {reason}")
    else:
        lines.append(f"None.")
    lines.append(f"")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Review release notes diff between two git refs or files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--repo-dir",
        help="Path to the sig-release git repository",
        default=None,
    )
    parser.add_argument(
        "--old-ref",
        help="Old git ref (default: HEAD~)",
        default="HEAD~",
    )
    parser.add_argument(
        "--new-ref",
        help="New git ref (default: HEAD)",
        default="HEAD",
    )
    parser.add_argument(
        "--notes-path",
        help="Path to release-notes-draft.md within the repo",
        default="releases/release-1.36/release-notes/release-notes-draft.md",
    )
    parser.add_argument(
        "--old-file",
        help="Path to old release notes file (overrides --repo-dir + --old-ref)",
        default=None,
    )
    parser.add_argument(
        "--new-file",
        help="Path to new release notes file (overrides --repo-dir + --new-ref)",
        default=None,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path (default: stdout)",
        default=None,
    )

    args = parser.parse_args()

    # Load old and new texts
    if args.old_file and args.new_file:
        with open(args.old_file, "r") as f:
            old_text = f.read()
        with open(args.new_file, "r") as f:
            new_text = f.read()
        old_ref = args.old_file
        new_ref = args.new_file
    elif args.repo_dir:
        old_text = git_show_file(args.repo_dir, args.old_ref, args.notes_path)
        new_text = git_show_file(args.repo_dir, args.new_ref, args.notes_path)
        old_ref = args.old_ref
        new_ref = args.new_ref
        # Print git log for context
        print(f"Git log (recent):", file=sys.stderr)
        print(git_log_oneline(args.repo_dir), file=sys.stderr)
        print(file=sys.stderr)
    else:
        parser.error(
            "Either --repo-dir or both --old-file and --new-file are required."
        )

    report = generate_report(old_text, new_text, old_ref, new_ref, args.notes_path)

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"Report written to: {args.output}", file=sys.stderr)
    else:
        print(report)


if __name__ == "__main__":
    main()
