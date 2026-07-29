---
name: k8s_release_notes_reviewer
description: A skill to thoroughly review Kubernetes release notes JSON draft files against the release notes guidelines, catching issues like backticked API kinds, forbidden words, and verifying correct formatting.
---

# Kubernetes Release Notes Reviewer

This skill automates and structures the review of `review-x.xx.json` files generated for Kubernetes release notes. It ensures all draft notes strictly adhere to the Kubernetes Release Notes Review Guide without losing the author's intended technical context.

## What it does
1. Parses the `review-x.xx.json` file.
2. Audits each draft note against the Kubernetes Release Notes Review Guide.
3. Automatically identifies issues such as:
   - Forbidden words ("we", "our", "new", "now", "e.g.", "i.e.").
   - Backticked API kinds (e.g., \`Pod\`, \`ResourceSlice\`) which should be verbatim PascalCase.
   - Backticked plain integer values (e.g., \`0600\`, \`2147483647\`).
   - Missing backticks on components, flags, or feature gates.
   - Improper verb usage (must be past-tense action verbs like Added, Fixed, Promoted).
4. Generates a list of suggested fixes or updates them directly via template scripts.
5. Sets `reviewDone: true` and updates the metadata count.

## Files Included
- `resources/release-notes-review-guide.md`: A copy of the Kubernetes Release Notes Review Guide for easy reference.
- `scripts/audit_notes.py`: Run this script against your `review-x.xx.json` file to perform a deep analysis and identify non-compliant notes.
- `scripts/apply_fixes.py`: A template script for applying corrections in bulk, updating the JSON file, and marking entries as reviewed.

## How to use it
You can integrate these tools into the `rn_review` pipeline. Use `audit_notes.py` as an automated linter for the drafts. When issues are identified, map the `prNumber` to the correct draft text in `apply_fixes.py` and execute it to apply your changes cleanly.
