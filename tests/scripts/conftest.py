"""Make scripts/ and project root importable from tests/scripts/."""

import sys
from pathlib import Path

# Add repo root for vi_installer package
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Add scripts/ for bootstrap_installer.py
scripts_dir = repo_root / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
