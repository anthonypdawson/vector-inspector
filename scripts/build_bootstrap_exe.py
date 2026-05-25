"""Build a standalone bootstrap installer executable with Nuitka.

Nuitka compiles bootstrap_installer.py into a single-file executable that runs on
a target system WITHOUT Python pre-installed. The compiled binary handles Python
detection, venv creation, and app installation.

Usage (run from repo root):

    python scripts/build_bootstrap_exe.py

Requires pipx (https://pipx.pypa.io). Nuitka is run ephemerally via
'pipx run nuitka' — no project dependency needed.
Build on each target OS to get the platform-specific executable.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path("scripts") / "bootstrap_installer.py"
OUTPUT_DIR = Path("build") / "bootstrap-installer"


def main() -> int:
    if not SCRIPT_PATH.exists():
        print(f"Bootstrap script not found: {SCRIPT_PATH}")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    extra_args: list[str] = []
    if sys.platform == "win32":
        extra_args += ["--windows-console-mode=force"]
    elif sys.platform == "darwin":
        extra_args += ["--macos-app-name=VectorInspectorInstaller"]
    # Linux: no extra platform args needed for --onefile

    cmd = [
        "pipx",
        "run",
        "nuitka",
        "--onefile",
        "--assume-yes-for-downloads",
        "--output-dir",
        str(OUTPUT_DIR),
        *extra_args,
        str(SCRIPT_PATH),
    ]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    exe_name = "bootstrap_installer.exe" if sys.platform == "win32" else "bootstrap_installer"
    print("\nBuild complete.")
    print(f"  Platform   : {sys.platform}")
    print(f"  Output dir : {OUTPUT_DIR}")
    print(f"  Executable : {OUTPUT_DIR / exe_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
