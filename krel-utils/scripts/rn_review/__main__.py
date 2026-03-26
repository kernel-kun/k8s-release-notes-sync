#!/usr/bin/env python3
"""Entry point for running the package as a module.

Usage:
    python -m rn_review extract --version 1.36 --sig-release-dir ./sig-release
    python -m rn_review status --review-file review-1.36.json
    python -m rn_review generate-maps --review-file review-1.36.json --version 1.36 --sig-release-dir ./sig-release
"""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
