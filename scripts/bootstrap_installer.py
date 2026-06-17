#!/usr/bin/env python3
"""Cross-platform bootstrap installer for Vector Inspector - Entry Point.

This is a thin wrapper that imports the installer package.
The actual implementation is in the installer/ package.

Can be compiled to a standalone executable with Nuitka:
    python scripts/build_installer.py

Or run directly with Python:
    python scripts/bootstrap_installer.py [options]
"""

import sys
from pathlib import Path

# Require Python 3.10+ to run the installer itself
# (The installed app requires 3.11+ by default, configurable via --python-min-version)
MIN_INSTALLER_PYTHON = (3, 10)
if sys.version_info < MIN_INSTALLER_PYTHON:
    print(
        f"Error: This installer requires Python {'.'.join(map(str, MIN_INSTALLER_PYTHON))} or higher.\n"
        f"You are running Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}.\n"
        f"Please upgrade Python and try again."
    )
    sys.exit(1)

# Add repo root to path for development mode
# (In production/Nuitka build, installer package is bundled)
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from vi_installer.ui import run_installer

if __name__ == "__main__":
    sys.exit(run_installer())
