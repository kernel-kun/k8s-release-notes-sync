#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["rich>=13"]
# ///
"""
Show the ```release-note``` block for every PR merged between two git refs.

Use it to catch PRs krel may have missed: give it the range that a tag covers
(e.g. previous-tag..this-tag) and it lists each merged PR's declared release
note, so you can spot ones that need a map entry.

How it works: along the first-parent history of `base..head`, every merge commit
is a bot "Merge pull request #N from ..." (verified against k/k). We parse those
PR numbers and look up each PR body via the `gh` CLI. Auth, rate-limit backoff,
and retries are delegated to `gh`, so there is no token to pass and no `requests`
dependency.

Refs may be SHAs, branches, or tags.

Output is grouped: PRs with a real release note (number + note), then PRs whose
block is NONE/empty, then PRs with no block at all.

With --live-dir pointing at a release's notes dir
(sig-release/releases/release-1.37/release-notes), it also reads which PRs krel
already knows -- the keys of release-notes-draft.json plus every prs[].nr across
sessions/*.json -- and flags any PR that we found a release note for but krel
never picked up. Those are the ones worth a manual map entry.

Usage:
    ./show_release_notes.py v1.37.0-alpha.1 v1.37.0-alpha.2
    ./show_release_notes.py --repo-dir ~/k8s/kubernetes v1.37.0-alpha.1 HEAD
    ./show_release_notes.py -o json v1.37.0-alpha.1 v1.37.0-alpha.2 > notes.json
    ./show_release_notes.py --live-dir \
        ~/kubernetes-oss/sig-release/releases/release-1.37/release-notes \
        v1.37.0-alpha.1 v1.37.0-alpha.2
    ./show_release_notes.py --self-test
"""

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext

# PR-number extractors mirroring krel's prsNumForCommitFromMessage
# (pkg/notes/notes.go): tried in order against each commit's full message,
# first match wins. Covers Prow merges, bot cherry-picks, reverts, and
# squash-merged PRs (the last, bare `(#N)`, is what `--merges` alone misses).
PR_PATTERNS = [
    re.compile(r"Merge pull request #(\d+)"),
    re.compile(r"automated-cherry-pick-of-#(\d+)"),
    re.compile(r"\(#(\d+)\)\s*\n\nThis reverts commit"),
    re.compile(r"\(#(\d+)\)"),
]

# Mirror of krel's empty-block check (pkg/notes/notes.go noteTextFromString):
# a release-note fence with only whitespace inside.
EMPTY_NOTE = re.compile(r"(?i)```release-notes?\s*```")

# Note extractors, tried in order, first match wins. The first four mirror
# krel's own regexes (CRLF normalized to LF up front, so its separate \r\n / \n
# patterns collapse into one each). The last is our own broader fallback: it
# catches inline ```release-note ...``` blocks that krel misses because krel
# requires a newline right after the opening fence -- which is the whole point
# of this script.
# Python has no (?U) flag; krel's ungreedy `.+` becomes non-greedy `.+?` here.
NOTE_EXPS = [
    re.compile(r"(?s)```release-notes?\n(?P<note>.+?)\n```"),   # release-note(s)
    re.compile(r"(?s)```dev-release-notes?\n(?P<note>.+?)(?:\n```|$)"),  # dev-release-note(s)
    re.compile(r"(?s)```\n(?P<note>.+?)\n```"),                 # bare fence
    re.compile(r"(?si)```release-notes?\b(?P<note>.+?)```"),    # ours: inline tolerant
]


def git(repo_dir, *args):
    proc = subprocess.run(["git", "-C", repo_dir, *args],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout


def pr_from_message(msg):
    """First PR number in a commit message, trying PR_PATTERNS in order (or None)."""
    for pat in PR_PATTERNS:
        if (m := pat.search(msg)):
            return int(m.group(1))
    return None


def prs_between(repo_dir, base, head):
    """PR numbers from first-parent commits in merge-base(base,head)..head, oldest first.

    Mirrors krel's listLeftParentCommits (pkg/notes/notes.go): it stops at the
    merge base of the two refs and pulls a PR number from *every* commit on the
    first-parent chain -- squash merges, cherry-picks, and reverts included --
    not just merge commits. Bodies (%B) are needed so the multi-line revert and
    squash patterns match. Records are split on \\x1e so embedded newlines don't.
    """
    stop = git(repo_dir, "merge-base", base, head).strip()
    out = git(repo_dir, "log", "--first-parent", "--reverse",
              "--format=%x1e%B", f"{stop}..{head}")
    prs = [pr for rec in out.split("\x1e")
           if rec.strip() and (pr := pr_from_message(rec)) is not None]
    return list(dict.fromkeys(prs))  # de-dupe, preserve order


def extract_release_note(body):
    """Return the release-note text, "NONE", or None if no block is present.

    CRLF is normalized to LF first so the krel-mirrored patterns match k8s PR
    bodies (which arrive CRLF over the API) the same way krel does.
    """
    s = (body or "").replace("\r\n", "\n")
    if EMPTY_NOTE.search(s):
        return "NONE"
    for exp in NOTE_EXPS:
        m = exp.search(s)
        if not m:
            continue
        note = m.group("note").strip()
        return "NONE" if note.lower() in ("none", "n/a", "na", "") else note
    return None


def fetch_pr(repo, pr):
    """Fetch (body, labels) for a PR via `gh api`. Raises RuntimeError on failure."""
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/pulls/{pr}",
         "--jq", '{body: (.body // ""), labels: [.labels[].name]}'],
        capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"gh exited {proc.returncode}")
    data = json.loads(proc.stdout)
    return data["body"], data["labels"]


def _safe(fn, pr):
    """Run fn(pr) in a worker, returning its result or the RuntimeError raised."""
    try:
        return fn(pr)
    except RuntimeError as e:
        return e


def note_for_pr(body, labels):
    """Release note for a PR, honoring krel's release-note-none label exclusion.

    krel skips note extraction entirely when the PR carries release-note-none
    (pkg/notes/notes.go MatchesExcludeFilter), so we do too -- otherwise the
    bare ``` fence pattern false-positives on ordinary code blocks in the body.
    """
    if "release-note-none" in labels:
        return "NONE"
    return extract_release_note(body)


def label_note_conflict(body, labels):
    """Body note for a release-note-none PR that nonetheless carries a real note.

    note_for_pr trusts the release-note-none label and returns "NONE", but krel
    sometimes still picks up the body's fence. Return that body note (so it can
    be flagged as a possible false positive), or None when there's no conflict.
    """
    if "release-note-none" not in labels:
        return None
    note = extract_release_note(body)
    return note if note and note != "NONE" else None


def krel_known_prs(live_dir):
    """PRs krel has already processed for a release.

    Reads the live release-notes dir (e.g.
    sig-release/releases/release-1.37/release-notes) and returns
    (draft_prs, session_prs): PR numbers in release-notes-draft.json (keyed by
    PR) and across every sessions/*.json (each prs[].nr).
    """
    from pathlib import Path

    live = Path(live_dir)
    draft_prs, session_prs = set(), set()

    draft = live / "release-notes-draft.json"
    if draft.exists():
        draft_prs = {int(k) for k in json.loads(draft.read_text())}
    else:
        print(f"warning: no {draft}", file=sys.stderr)

    sessions = live / "sessions"
    if sessions.is_dir():
        for f in sorted(sessions.glob("*.json")):
            try:
                data = json.loads(f.read_text())
            except json.JSONDecodeError as e:
                print(f"warning: bad session {f.name}: {e}", file=sys.stderr)
                continue
            for entry in data.get("prs") or []:
                if "nr" in entry:
                    session_prs.add(int(entry["nr"]))
    else:
        print(f"warning: no {sessions}/", file=sys.stderr)

    return draft_prs, session_prs


def make_progress():
    """A rich progress bar (count, bar, M/N, elapsed) drawn on stderr."""
    from rich.console import Console
    from rich.progress import (BarColumn, MofNCompleteColumn, Progress,
                               TextColumn, TimeElapsedColumn)
    return Progress(
        TextColumn("[cyan]{task.description}"), BarColumn(),
        MofNCompleteColumn(), TimeElapsedColumn(),
        console=Console(stderr=True), transient=True)


def render_table(rng, with_note, none_empty, no_block, conflicts, repo,
                 live_dir, draft_prs, session_prs, missed):
    """Render results as rich tables: column widths and wrapping are automatic."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    def link(pr):  # clickable #NNN -> github PR page (OSC 8, falls back to text)
        return f"[link=https://github.com/{repo}/pull/{pr}]#{pr}[/link]"

    t = Table(title=f"Release notes ({len(with_note)})  {rng}",
              show_lines=True, expand=True, title_justify="left")
    t.add_column("PR", style="cyan", no_wrap=True, justify="right")
    t.add_column("Release note", ratio=1)  # takes remaining width, wraps
    for pr in sorted(with_note):
        t.add_row(link(pr), with_note[pr])
    console.print(t)

    def refs(nums):
        return "  ".join(link(n) for n in nums) if nums else "[dim]-[/dim]"
    console.print(f"\n[bold]NONE / empty[/bold] ({len(none_empty)})")
    console.print(refs(none_empty), soft_wrap=False)
    console.print(f"\n[bold]No release-note block[/bold] ({len(no_block)})")
    console.print(refs(no_block), soft_wrap=False)

    if conflicts:
        known = draft_prs | session_prs
        ct = Table(title=f"⚠ release-note-none but body has a note "
                         f"({len(conflicts)}) — possible false positives",
                   show_lines=True, expand=True, title_justify="left",
                   title_style="yellow")
        ct.add_column("PR", style="cyan", no_wrap=True, justify="right")
        ct.add_column("Body note", ratio=1)
        if live_dir:
            ct.add_column("krel picked up?", no_wrap=True)
        for pr in sorted(conflicts):
            row = [link(pr), conflicts[pr]]
            if live_dir:
                row.append("[red]YES[/red]" if pr in known else "[green]no[/green]")
            ct.add_row(*row)
        console.print(ct)

    if live_dir:
        console.print(f"\n[bold]krel coverage[/bold] (live: {live_dir})")
        console.print(f"  krel knew {len(draft_prs | session_prs)} PRs "
                      f"(draft.json: {len(draft_prs)}, sessions: {len(session_prs)})")
        if missed:
            mt = Table(title=f"⚠ {len(missed)} PR(s) with a release note krel "
                             f"did NOT pick up", show_lines=True, expand=True,
                       title_justify="left", title_style="yellow")
            mt.add_column("PR", style="cyan", no_wrap=True, justify="right")
            mt.add_column("Release note (first line)", ratio=1)
            for pr in missed:
                mt.add_row(link(pr), with_note[pr].splitlines()[0])
            console.print(mt)
        else:
            console.print("  [green]every PR with a release note is known to "
                          "krel[/green]")


def categorize(results):
    """Split {pr: note} into (with_note, none_or_empty, no_block)."""
    with_note, none_empty, no_block = {}, [], []
    for pr, note in results.items():
        if note is None:
            no_block.append(pr)
        elif note == "NONE":
            none_empty.append(pr)
        else:
            with_note[pr] = note
    return with_note, sorted(none_empty), sorted(no_block)


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("base", nargs="?", help="starting ref (exclusive)")
    p.add_argument("head", nargs="?", help="ending ref (inclusive)")
    p.add_argument("--repo-dir", default="/home/fico/personal/kubernetes-oss/kubernetes",
                   help="local clone to read merge history from")
    p.add_argument("--repo", default="kubernetes/kubernetes",
                   help="owner/repo to query PR bodies from")
    p.add_argument("--live-dir",
                   help="release-notes dir (with release-notes-draft.json + "
                        "sessions/) to reconcile against; flags PRs that have a "
                        "release note but krel never picked up")
    p.add_argument("-o", "--output", choices=("table", "json"), default="table",
                   help="output format (default: table, a rich-rendered TUI view)")
    p.add_argument("-j", "--jobs", type=int, default=5,
                   help="parallel gh fetches (default: 5)")
    p.add_argument("-d", "--debug", action="count", default=0,
                   help="trace fetch progress to stderr; repeat (-dd) to also "
                        "dump each PR body")
    p.add_argument("--self-test", action="store_true",
                   help="run offline self-checks and exit")
    args = p.parse_args()

    if args.self_test:
        _self_test()
        return
    if not args.base or not args.head:
        p.error("base and head refs are required")

    try:
        prs = prs_between(args.repo_dir, args.base, args.head)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)

    if not prs:
        print(f"no merged PRs found in {args.base}..{args.head}", file=sys.stderr)
        sys.exit(1)
    print(f"{len(prs)} merged PRs in {args.base}..{args.head}", file=sys.stderr)

    results = {}
    conflicts = {}  # PR -> body note, for release-note-none PRs that still have one
    failures = 0
    total = len(prs)

    def work(pr):
        body, labels = fetch_pr(args.repo, pr)
        return (pr, body, labels, note_for_pr(body, labels),
                label_note_conflict(body, labels))

    # Live progress bar unless --debug (its per-PR stderr lines would fight it).
    bar = make_progress() if not args.debug and sys.stderr.isatty() else nullcontext()

    done = 0
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool, bar as prog:
        task = prog.add_task("fetching PRs", total=total) if prog else None
        for fut in pool.map(lambda pr: (pr, _safe(work, pr)), prs):
            pr, outcome = fut
            done += 1
            if prog:
                prog.advance(task)
            if isinstance(outcome, RuntimeError):
                msg = f"[{done}/{total}] #{pr}: error: {outcome}"
                prog.console.print(msg) if prog else print(msg, file=sys.stderr)
                failures += 1
                continue
            _, body, labels, note, conflict = outcome
            results[pr] = note
            if conflict:
                conflicts[pr] = conflict
            if args.debug:
                cat = ("no-block" if note is None
                       else "NONE" if note == "NONE" else "note")
                first = "" if note is None else note.splitlines()[0]
                print(f"[{done}/{total}] #{pr} {cat} "
                      f"labels={','.join(labels) or '-'}"
                      + (f" :: {first}" if first else ""), file=sys.stderr)
            if args.debug >= 2:
                print(f"----- #{pr} body -----\n{body}\n----- end #{pr} -----",
                      file=sys.stderr)

    with_note, none_empty, no_block = categorize(results)

    missed = []
    draft_prs = session_prs = set()
    if args.live_dir:
        draft_prs, session_prs = krel_known_prs(args.live_dir)
        known = draft_prs | session_prs
        missed = sorted(pr for pr in with_note if pr not in known)

    if args.output == "json":
        out = {
            "range": f"{args.base}..{args.head}",
            "with_note": {str(k): v for k, v in sorted(with_note.items())},
            "none_or_empty": none_empty,
            "no_block": no_block,
            "labeled_none_with_note":
                {str(k): v for k, v in sorted(conflicts.items())},
        }
        if args.live_dir:
            out["krel_missed"] = missed
        json.dump(out, sys.stdout, indent=2)
        print()
    else:
        render_table(f"{args.base}..{args.head}", with_note, none_empty, no_block,
                     conflicts, args.repo, args.live_dir, draft_prs, session_prs, missed)

    if failures:
        sys.exit(1)


def _self_test():
    assert prs_between.__doc__  # smoke
    # PR extraction mirrors krel's four patterns, in priority order
    assert pr_from_message("Merge pull request #137255 from pohly/x") == 137255
    assert pr_from_message("automated-cherry-pick-of-#137240 onto release-1.36") == 137240
    assert pr_from_message('Revert "thing" (#138900)\n\nThis reverts commit abc') == 138900
    assert pr_from_message("kubectl: strict check for exec command (#138214)") == 138214
    assert pr_from_message("CHANGELOG: Update directory for v1.36.0-alpha.1 release") is None
    # merge-commit subject wins over a (#N) that may appear later in the body
    assert pr_from_message("Merge pull request #100 from x\n\ntitle (#200)") == 100
    assert extract_release_note("x\n```release-note\nhello\n```\ny") == "hello"
    assert extract_release_note("```release-notes\nNONE\n```") == "NONE"
    assert extract_release_note("```RELEASE-NOTE\n  spaced  \n```") == "spaced"
    assert extract_release_note("```release-note\n\n```") == "NONE"
    assert extract_release_note("```release-note\nN/A\n```") == "NONE"
    assert extract_release_note("no block") is None
    # CRLF (how k8s PR bodies actually arrive)
    assert extract_release_note("```release-note\r\nhi there\r\n```") == "hi there"
    # ungreedy: a trailing docs block must not be swallowed
    assert extract_release_note("```release-note\nkeep\n```\n```docs\ndrop\n```") == "keep"
    # krel extras
    assert extract_release_note("```dev-release-note\ndev stuff\n```") == "dev stuff"
    assert extract_release_note("```\nbare fence\n```") == "bare fence"
    # ours beyond krel: inline content with no newline after the fence
    assert extract_release_note("```release-note inline note```") == "inline note"
    # release-note-none label wins even if the body has a stray ``` code block
    assert note_for_pr("```\nsome test output\n```", ["release-note-none"]) == "NONE"
    assert note_for_pr("```release-note\nreal\n```", ["kind/bug"]) == "real"
    # conflict: release-note-none label, but body still carries a real note
    assert label_note_conflict("```release-note\nactual\n```",
                               ["release-note-none"]) == "actual"
    assert label_note_conflict("```release-note\nNONE\n```",
                               ["release-note-none"]) is None
    assert label_note_conflict("```release-note\nreal\n```", ["kind/bug"]) is None
    assert label_note_conflict("no block", ["release-note-none"]) is None
    # categorize splits the three buckets
    wn, ne, nb = categorize({1: "real note", 2: "NONE", 3: None, 4: "another"})
    assert wn == {1: "real note", 4: "another"} and ne == [2] and nb == [3]
    print("self-test ok")


if __name__ == "__main__":
    main()
