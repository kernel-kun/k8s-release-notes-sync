#!/usr/bin/env python3
"""
Compare PR numbers from release-notes map files, release-notes-draft.json, and session files

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
    
    print(f"🔎 Analyzing release {release_version}")
    print(f"Maps directory: {maps_dir}")
    print(f"Sessions directory: {sessions_dir}")
    print(f"JSON file: {json_file}")
    print("=" * 80)
    
    # Extract PR numbers from all sources
    pr_from_maps = get_pr_numbers_from_maps(maps_dir)
    pr_from_draft_json = get_pr_numbers_from_draft_json(json_file)
    pr_from_sessions = get_pr_numbers_from_sessions(sessions_dir)
    
    # Calculate set differences and intersections
    all_prs = pr_from_maps | pr_from_draft_json | pr_from_sessions
    
    # Two-way comparisons
    maps_not_in_json = pr_from_maps - pr_from_draft_json
    json_not_in_maps = pr_from_draft_json - pr_from_maps
    
    sessions_not_in_json = pr_from_sessions - pr_from_draft_json
    json_not_in_sessions = pr_from_draft_json - pr_from_sessions
    
    sessions_not_in_maps = pr_from_sessions - pr_from_maps
    maps_not_in_sessions = pr_from_maps - pr_from_sessions
    
    # Three-way: only in one source
    only_in_maps = pr_from_maps - pr_from_draft_json - pr_from_sessions
    only_in_json = pr_from_draft_json - pr_from_maps - pr_from_sessions
    only_in_sessions = pr_from_sessions - pr_from_maps - pr_from_draft_json
    
    # In all three
    in_all_three = pr_from_maps & pr_from_draft_json & pr_from_sessions
    
    # Display results
    print(f"\n📊 SUMMARY:")
    print(f"  Total PRs in map files: {len(pr_from_maps)}")
    print(f"  Total PRs in draft JSON: {len(pr_from_draft_json)}")
    print(f"  Total PRs in session files: {len(pr_from_sessions)}")
    print(f"  Total unique PRs (all sources): {len(all_prs)}")
    print(f"  PRs in all three sources: {len(in_all_three)}")
    print()
    
    # Map files vs Draft JSON
    print("=" * 80)
    print(f"📁 MAP FILES vs 📄 DRAFT JSON:")
    print("=" * 80)
    
    print(f"\n🔍 PRs in MAP FILES but NOT in DRAFT JSON ({len(maps_not_in_json)}):")
    if maps_not_in_json:
        for pr in sorted(maps_not_in_json):
            print(f"  - PR #{pr}")
    else:
        print("  ✅ None - All map file PRs are in draft JSON")
    
    print(f"\n🔍 PRs in DRAFT JSON but NOT in MAP FILES ({len(json_not_in_maps)}):")
    if json_not_in_maps:
        for pr in sorted(json_not_in_maps):
            print(f"  - PR #{pr}")
    else:
        print("  ✅ None - All draft JSON PRs have map files")
    
    # Session files vs Draft JSON
    print("\n" + "=" * 80)
    print(f"📝 SESSION FILES vs 📄 DRAFT JSON:")
    print("=" * 80)
    
    print(f"\n🔍 PRs in SESSION FILES but NOT in DRAFT JSON ({len(sessions_not_in_json)}):")
    if sessions_not_in_json:
        for pr in sorted(sessions_not_in_json):
            print(f"  - PR #{pr}")
    else:
        print("  ✅ None - All session file PRs are in draft JSON")
    
    print(f"\n🔍 PRs in DRAFT JSON but NOT in SESSION FILES ({len(json_not_in_sessions)}):")
    if json_not_in_sessions:
        for pr in sorted(json_not_in_sessions):
            print(f"  - PR #{pr}")
    else:
        print("  ✅ None - All draft JSON PRs are in session files")
    
    # Map files vs Session files
    print("\n" + "=" * 80)
    print(f"📁 MAP FILES vs 📝 SESSION FILES:")
    print("=" * 80)
    
    print(f"\n🔍 PRs in MAP FILES but NOT in SESSION FILES ({len(maps_not_in_sessions)}):")
    if maps_not_in_sessions:
        for pr in sorted(maps_not_in_sessions):
            print(f"  - PR #{pr}")
    else:
        print("  ✅ None - All map file PRs are in session files")
    
    print(f"\n🔍 PRs in SESSION FILES but NOT in MAP FILES ({len(sessions_not_in_maps)}):")
    if sessions_not_in_maps:
        for pr in sorted(sessions_not_in_maps):
            print(f"  - PR #{pr}")
    else:
        print("  ✅ None - All session file PRs have map files")
    
    # Three-way unique PRs
    print("\n" + "=" * 80)
    print(f"🎯 UNIQUE TO EACH SOURCE:")
    print("=" * 80)
    
    print(f"\n📁 Only in MAP FILES ({len(only_in_maps)}):")
    if only_in_maps:
        for pr in sorted(only_in_maps):
            print(f"  - PR #{pr}")
    else:
        print("  ✅ None")
    
    print(f"\n📄 Only in DRAFT JSON ({len(only_in_json)}):")
    if only_in_json:
        for pr in sorted(only_in_json):
            print(f"  - PR #{pr}")
    else:
        print("  ✅ None")
    
    print(f"\n📝 Only in SESSION FILES ({len(only_in_sessions)}):")
    if only_in_sessions:
        for pr in sorted(only_in_sessions):
            print(f"  - PR #{pr}")
    else:
        print("  ✅ None")


if __name__ == "__main__":
    main()