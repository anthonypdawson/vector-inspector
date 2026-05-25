# Release Notes (0.8.2) — May 25, 2026

Bootstrap package installer for systems without python (or users that do not want to use command line)

## Packaging & Distribution

- Added a pip-enabled Windows bootstrap installer flow via `scripts/bootstrap_installer.py`. It creates an app-local virtual environment, installs `vector-inspector` from pip, and writes app/pip launchers so users can install extras after setup.
- Added `scripts/build_bootstrap_exe.py` to build the bootstrap installer executable with Nuitka.

## Docs

- Added `docs/BOOTSTRAP_INSTALLER.md` documenting end-to-end build, install, update, pip usage, and troubleshooting for the new bootstrap installer flow.

---
