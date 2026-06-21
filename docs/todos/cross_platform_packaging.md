# Cross-Platform Packaging with pip-Accessible Runtime

## Purpose

Vector Inspector needs a distributable installer for Windows, macOS, and Linux that:

1. Works for non-developer end users (no Python pre-installed required)
2. Installs into a managed, app-local virtual environment
3. Keeps `pip` accessible so users can install optional provider extras
   (e.g. `vector-inspector[milvus]`, `vector-inspector[viz]`) after install

The key constraint is that typical frozen-app packagers (PyInstaller, Nuitka, Briefcase)
produce sealed runtimes — users cannot `pip install` into them. This app's optional
provider model requires a real, live Python environment.

## Current State

A Windows bootstrap installer exists (see `docs/BOOTSTRAP_INSTALLER.md`):
- Script: `scripts/bootstrap_installer.py`
- Build script: `scripts/build_bootstrap_exe.py` (Nuitka → `.exe`)
- Installs to `%LOCALAPPDATA%/VectorInspector/` with both app and pip launchers
- Handles Python detection, winget fallback, venv creation, and extras install

**macOS and Linux equivalents do not yet exist.**

## What Needs to Be Done

### macOS
- Port `bootstrap_installer.py` to handle macOS paths:
  - Install root: `~/Library/Application Support/VectorInspector/`
  - Launchers: `~/.local/bin/vector-inspector` and `vector-inspector-pip`
- Python detection: check `python3` on PATH, Homebrew, pyenv
- Build a distributable: either a `.app` bundle (via Briefcase or py2app) that
  runs the bootstrap, or a signed `.pkg` installer
- No winget — replace with Homebrew detection/suggestion

### Linux
- Same Python bootstrap approach, XDG paths:
  - Install root: `~/.local/share/vectorinspector/`
  - Launchers: `~/.local/bin/vector-inspector` and `vector-inspector-pip`
- Python detection: distro package manager hints (apt, dnf, pacman)
- Distribute as: AppImage, `.deb`, `.rpm`, or a plain shell script
- Shell script is the lowest-friction starting point

### Shared / Refactoring
- Refactor `bootstrap_installer.py` to share platform-agnostic logic
  (venv creation, pip upgrade, extras install, launcher generation) with
  platform-specific path/detection modules
- Add a CI job that builds and smoke-tests the installer on each platform
- Consider a unified `scripts/build_installer.py` entrypoint that dispatches
  to the right platform build

## Design Constraints

- The installer must NOT require the user to have Python pre-installed
- After install, `vector-inspector-pip install <extra>` must work from a terminal
- The app-local venv must be isolated from any system Python to avoid conflicts
- Updating the app means re-running the installer (reuses existing venv by default)

## Related Files

- `docs/BOOTSTRAP_INSTALLER.md` — full Windows bootstrap docs
- `scripts/bootstrap_installer.py` — Windows bootstrap implementation
- `scripts/build_bootstrap_exe.py` — Nuitka build for Windows `.exe`
- `pyproject.toml` `[project.optional-dependencies]` — defines installable extras
