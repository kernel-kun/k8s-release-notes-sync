#!/usr/bin/env python3
"""
Compare PR numbers from release-notes map files, release-notes-draft.json,
release-notes-draft.md, and session files.

Usage: python compare_pr_numbers.py <release-version>
Example: python compare_pr_numbers.py 1.35
"""

import os
import re
import json
import sys
from pathlib import Path


def extract_pr_from_filename(filename):
    """Extract PR number from filename like 'pr-<number>-map.yaml'"""
    match = re.match(r'pr-(\d+)-map\.yaml', filename)
    return int(match.group(1)) if match else None


def get_pr_numbers_from_maps(maps_dir):
    """Extract PR numbers from filenames in the maps directory"""
    pr_numbers = set()
    
    if not os.path.exists(maps_dir):
        print(f"Warning: Maps directory not found: {maps_dir}")
        return pr_numbers
    
    for filename in os.listdir(maps_dir):
        pr_num = extract_pr_from_filename(filename)
        if pr_num:
            pr_numbers.add(pr_num)
    
    return pr_numbers


def get_pr_numbers_from_draft_json(json_file):
    """Extract PR numbers from the release-notes-draft.json file (keys are PR numbers)"""
    pr_numbers = set()
    
    if not os.path.exists(json_file):
        print(f"Warning: JSON file not found: {json_file}")
        return pr_numbers
    
    with open(json_file, 'r') as f:
        data = json.load(f)
        # Keys are the PR numbers as strings, convert to int
        pr_numbers = {int(pr) for pr in data.keys()}
    
    return pr_numbers


def get_pr_numbers_from_draft_md(md_file):
    """Extract PR numbers from the release-notes-draft.md file.

    Matches the ([#12345](url)) pattern used in Kubernetes release notes.
    """
    pr_numbers = set()

    if not os.path.exists(md_file):
        print(f"Warning: Markdown file not found: {md_file}")
        return pr_numbers

    with open(md_file, 'r') as f:
        content = f.read()

    for match in re.finditer(r'\[#(\d+)\]', content):
        pr_numbers.add(int(match.group(1)))

    return pr_numbers


def get_pr_numbers_from_sessions(sessions_dir):
    """Extract PR numbers from all JSON files in the sessions directory"""
    pr_numbers = set()
    
    if not os.path.exists(sessions_dir):
        print(f"Warning: Sessions directory not found: {sessions_dir}")
        return pr_numbers
    
    # Iterate through all JSON files in sessions directory
    for filename in os.listdir(sessions_dir):
        if not filename.endswith('.json'):
            continue
        
        filepath = os.path.join(sessions_dir, filename)
        try:
            with open(filepath, 'r') as f:
                session_data = json.load(f)
                # Extract PR numbers from the 'prs' array
                if 'prs' in session_data and isinstance(session_data['prs'], list):
                    for pr_entry in session_data['prs']:
                        if 'nr' in pr_entry:
                            pr_numbers.add(int(pr_entry['nr']))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not read {filename}: {e}")
    
    return pr_numbers


def main():
    if len(sys.argv) != 2:
        print("Usage: python compare_pr_numbers.py <release-version>")
        print("Example: python compare_pr_numbers.py 1.35")
        sys.exit(1)
    
    release_version = sys.argv[1]
    
    # Construct paths based on release version
    base_dir = f"releases/release-{release_version}/release-notes"
    maps_dir = os.path.join(base_dir, "maps")
    sessions_dir = os.path.join(base_dir, "sessions")
    json_file = os.path.join(base_dir, "release-notes-draft.json")
    md_file = os.path.join(base_dir, "release-notes-draft.md")

    print(f"🔎 Analyzing release {release_version}")
    print(f"Maps directory: {maps_dir}")
    print(f"Sessions directory: {sessions_dir}")
    print(f"JSON file: {json_file}")
    print(f"Markdown file: {md_file}")
    print("=" * 80)

    # Extract PR numbers from all sources
    pr_from_maps = get_pr_numbers_from_maps(maps_dir)
    pr_from_draft_json = get_pr_numbers_from_draft_json(json_file)
    pr_from_draft_md = get_pr_numbers_from_draft_md(md_file)
    pr_from_sessions = get_pr_numbers_from_sessions(sessions_dir)

    sources = {
        "📁 MAP FILES": pr_from_maps,
        "📄 DRAFT JSON": pr_from_draft_json,
        "📝 DRAFT MD": pr_from_draft_md,
        "📋 SESSION FILES": pr_from_sessions,
    }
    # Calculate totals
    all_prs = pr_from_maps | pr_from_draft_json | pr_from_draft_md | pr_from_sessions
    in_all = pr_from_maps & pr_from_draft_json & pr_from_draft_md & pr_from_sessions

    # Display results
    print(f"\n📊 SUMMARY:")
    for name, prs in sources.items():
        print(f"  Total PRs in {name}: {len(prs)}")
    print(f"  Total unique PRs (all sources): {len(all_prs)}")
    print(f"  PRs in all four sources: {len(in_all)}")
    print()

    # All pairwise comparisons
    for i, (name_a, prs_a) in enumerate(sources.items()):
        for name_b, prs_b in list(sources.items())[i + 1:]:
            print("=" * 80)
            print(f"{name_a} vs {name_b}:")
            print("=" * 80)

            a_not_b = prs_a - prs_b
            b_not_a = prs_b - prs_a

            print(f"\n🔍 PRs in {name_a} but NOT in {name_b} ({len(a_not_b)}):")
            if a_not_b:
                for pr in sorted(a_not_b):
                    print(f"  - PR #{pr}")
            else:
                print(f"  ✅ None")

            print(f"\n🔍 PRs in {name_b} but NOT in {name_a} ({len(b_not_a)}):")
            if b_not_a:
                for pr in sorted(b_not_a):
                    print(f"  - PR #{pr}")
            else:
                print(f"  ✅ None")
            print()

    # Unique to each source
    print("=" * 80)
    print(f"🎯 UNIQUE TO EACH SOURCE:")
    print("=" * 80)

    for name, prs in sources.items():
        others = set()
        for other_name, other_prs in sources.items():
            if other_name != name:
                others |= other_prs
        only = prs - others
        print(f"\n{name} only ({len(only)}):")
        if only:
            for pr in sorted(only):
                print(f"  - PR #{pr}")
        else:
            print("  ✅ None")


if __name__ == "__main__":
    main()
