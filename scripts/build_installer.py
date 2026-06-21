"""Build a standalone bootstrap installer executable with Nuitka.

Nuitka compiles bootstrap_installer.py into a single-file executable that runs on
a target system WITHOUT Python pre-installed. The compiled binary handles Python
detection, venv creation, and app installation.

Usage (run from repo root):

    pdm run python scripts/build_installer.py

Requirements
------------
- nuitka — auto-installed into the current environment if missing.
- questionary — bundled into the binary at build time so the interactive TUI setup
  wizard is always available without requiring the end user to install anything.
  Auto-installed into the current environment if missing (see _ensure_questionary()).

Both packages are installed via pip into the same interpreter that runs this script
so that Nuitka compiles with the correct site-packages visible.

Build on each target OS to produce the platform-specific executable.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SCRIPT_PATH = Path("scripts") / "bootstrap_installer.py"
OUTPUT_DIR = Path("build") / "bootstrap-installer"
VERSION_FILE = Path("src") / "vector_inspector" / "__init__.py"


def _read_version() -> str:
    """Parse __version__ from src/vector_inspector/__init__.py without importing it."""
    text = VERSION_FILE.read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.MULTILINE)
    if not m:
        raise RuntimeError(f"Could not find __version__ in {VERSION_FILE}")
    return m.group(1)


def _ensure_questionary() -> None:
    """Install questionary into the current environment if missing.

    Nuitka bundles packages from the build-time environment. questionary is
    imported inside a try/except in bootstrap_installer.py so Nuitka won't
    auto-detect it — we force-include it via --include-package=questionary,
    but it must be installed first so Nuitka can find the source.
    """
    try:
        import questionary  # noqa: F401
    except ImportError:
        print("Installing 'questionary' into build environment (required for bundling)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "questionary"])


def _ensure_nuitka() -> None:
    """Install nuitka with onefile extras into the current environment if missing.

    We use 'python -m nuitka' (same interpreter as this script) instead of
    'pipx run nuitka' so that Nuitka compiles against the same site-packages
    where questionary and other build-time deps are installed.

    The [onefile] extra includes zstandard for compressed executables.
    """
    try:
        import nuitka  # noqa: F401
    except ImportError:
        print("Installing 'nuitka[onefile]' into build environment (includes zstandard for compression)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "nuitka[onefile]"])


def main() -> int:
    if not SCRIPT_PATH.exists():
        print(f"Bootstrap script not found: {SCRIPT_PATH}")
        return 1

    _ensure_questionary()
    _ensure_nuitka()

    version = _read_version()

    # Determine platform identifier and file extension
    if sys.platform == "win32":
        platform = "windows"
        file_ext = ".exe"
    elif sys.platform == "darwin":
        platform = "macos"
        file_ext = ""
    else:
        platform = "linux"
        file_ext = ""

    exe_name = f"vector-inspector-installer-{platform}-v{version}{file_ext}"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    extra_args: list[str] = []
    if sys.platform == "win32":
        extra_args += ["--windows-console-mode=force"]
    elif sys.platform == "darwin":
        extra_args += ["--macos-app-name=VectorInspectorInstaller", "--static-libpython=no"]
    # Linux: no extra platform args needed for --onefile

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--onefile",
        "--assume-yes-for-downloads",
        "--include-package=vi_installer",  # Include our installer package
        "--include-package=questionary",
        "--follow-imports",  # Auto-discover imports
        f"--output-dir={OUTPUT_DIR}",
        f"--output-filename={exe_name}",
        *extra_args,
        str(SCRIPT_PATH),
    ]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    print("\nBuild complete.")
    print(f"  Version    : {version}")
    print(f"  Platform   : {sys.platform}")
    print(f"  Output dir : {OUTPUT_DIR}")
    print(f"  Executable : {OUTPUT_DIR / exe_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
