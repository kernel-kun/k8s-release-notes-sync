#!/usr/bin/env bash
# Convenience wrapper for the release notes sync tool
# Usage: ./sync validate --release 1.35 --global

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Run the sync tool using uv
cd "$SCRIPT_DIR"
uv run python sync_tool.py "$@"
