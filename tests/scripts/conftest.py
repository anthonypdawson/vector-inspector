"""Make scripts/ importable from tests/scripts/."""
import sys
from pathlib import Path

scripts_dir = Path(__file__).parent.parent.parent / "scripts"
if str(scripts_dir) not in sys.path:
    sys.path.insert(0, str(scripts_dir))
