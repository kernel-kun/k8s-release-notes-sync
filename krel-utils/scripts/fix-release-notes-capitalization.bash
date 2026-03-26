#!/usr/bin/env bash
#
# fix-capitalization.bash
#
# Scans all pr-*-map.yaml files in a given maps directory and identifies
# release note `text` fields whose first letter is lowercase. Lists them
# for review, then prompts for confirmation before applying the fix.
#
# Usage:
#   bash fix-capitalization.bash <maps-directory>
#
# Example:
#   bash fix-capitalization.bash releases/release-1.36/release-notes/maps

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash fix-capitalization.bash <maps-directory>"
  echo "Example: bash fix-capitalization.bash releases/release-1.36/release-notes/maps"
  exit 1
fi

MAPS_DIR="$1"

if [[ ! -d "$MAPS_DIR" ]]; then
  echo "❌ Directory not found: $MAPS_DIR"
  exit 1
fi

# ── Phase 1: Scan & Report ──────────────────────────────────────────────────

echo "📁 Scanning: $MAPS_DIR"
echo "════════════════════════════════════════════════════════════════════════"

total=0
needs_fix=0
files_to_fix=()

for f in "$MAPS_DIR"/pr-*-map.yaml; do
  [[ -f "$f" ]] || continue
  total=$((total + 1))

  # Extract the first content line after "text: |-"
  text_line=$(sed -n '/^  text: |-$/{n;p}' "$f" | sed 's/^[[:space:]]*//')
  first_char="${text_line:0:1}"

  # Check if the first character is a lowercase letter
  if [[ "$first_char" =~ [a-z] ]]; then
    needs_fix=$((needs_fix + 1))
    files_to_fix+=("$f")
    echo "  ⚠️  $(basename "$f")"
    echo "     → ${text_line:0:120}"
  fi
done

echo "════════════════════════════════════════════════════════════════════════"
echo "📊 Total map files: $total"
echo "✅ Already capitalized: $((total - needs_fix))"
echo "⚠️  Need capitalization: $needs_fix"
echo ""

if [[ $needs_fix -eq 0 ]]; then
  echo "🎉 All text fields are already capitalized. Nothing to do!"
  exit 0
fi

# ── Phase 2: Prompt & Apply ─────────────────────────────────────────────────

read -rp "Apply capitalization to $needs_fix file(s)? [y/N] " answer

if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
  echo "❌ Aborted. No files were modified."
  exit 0
fi

echo ""
echo "Applying fixes..."

for f in "${files_to_fix[@]}"; do
  sed -i '/^  text: |-$/{n;s/^\(\s*\)\([a-z]\)/\1\u\2/}' "$f"
  echo "  ✅ Fixed: $(basename "$f")"
done

echo ""
echo "════════════════════════════════════════════════════════════════════════"
echo "🎉 Done! $needs_fix file(s) updated."
