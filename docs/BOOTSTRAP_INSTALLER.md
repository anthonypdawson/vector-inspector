# Bootstrap Installer (cross-platform, pip-enabled runtime)

This document describes the bootstrap installer process for Vector Inspector.
It creates an app-local virtual environment so Vector Inspector can use pip
internally to install and manage optional provider dependencies.

## Why this exists

Frozen-app bundlers (Briefcase, PyInstaller, etc.) ship a sealed runtime with no
access to pip. Vector Inspector's optional provider model requires a live Python
environment so the app can install extras at runtime.

The bootstrap installer solves that by creating an app-local virtual environment
and installing Vector Inspector from PyPI into it.

## What gets installed

Default install roots by platform:

| Platform | Install root |
|----------|--------------|
| Windows  | `%LOCALAPPDATA%\VectorInspector\` |
| macOS    | `~/Library/Application Support/VectorInspector/` |
| Linux    | `~/.local/share/vectorinspector/` |

Files created under the install root:

- `runtime/venv/` — app-local virtual environment
- `bin/vector-inspector` (`.cmd` on Windows) — app launcher
- `bootstrap-state.json` — install metadata

pip is available inside `runtime/venv` for the app's internal use.

## Runtime behavior

The bootstrap flow is implemented in [scripts/bootstrap_installer.py](../scripts/bootstrap_installer.py).

When run, it:

1. Detects the current platform (Windows / macOS / Linux).
2. Finds a compatible Python interpreter (3.11+ by default).
   - Windows: checks `py` launcher, `%LOCALAPPDATA%\Programs\Python`, then winget fallback.
   - macOS: checks PATH, Homebrew (`/opt/homebrew`, `/usr/local`), pyenv.
   - Linux: checks PATH, pyenv, and suggests the distro package manager.
3. Creates (or reuses) an app-local virtual environment.
4. Upgrades pip/setuptools/wheel inside that environment.
5. Installs `vector-inspector` (and optional extras if requested).
6. Creates a platform-appropriate app launcher in `bin/`.
7. Optionally registers `bin/` in the user PATH (`--add-to-path`).
8. Optionally creates a desktop shortcut (`--create-shortcut`).
9. Optionally launches Vector Inspector.

## Build the bootstrap executable with Nuitka

Build helper script: [scripts/build_installer.py](../scripts/build_installer.py)

Nuitka compiles `bootstrap_installer.py` into a standalone executable that runs
on a machine with **no Python pre-installed**. You must build on the target OS.

### Prerequisites

- A C compiler on the build machine (MSVC on Windows, Xcode CLT on macOS, gcc/clang on Linux).
- `nuitka` and `questionary` are **auto-installed** into the current environment by the build script if missing — no manual setup required.

Build the executable:

```sh
pdm run python scripts/build_installer.py
```

The version is read from `src/vector_inspector/__init__.py` automatically.

Output (varies by platform):

| Platform | Output file |
|----------|-------------|
| Windows  | `build/bootstrap-installer/vector-inspector-vX.Y.Z-installer.exe` |
| macOS    | `build/bootstrap-installer/vector-inspector-vX.Y.Z-installer` |
| Linux    | `build/bootstrap-installer/vector-inspector-vX.Y.Z-installer` |

The GitHub Actions workflow (`.github/workflows/build-installer.yml`) builds all three platform
binaries automatically when a release is published and attaches them to the release as assets.

## Use the bootstrap installer

Examples below use the versioned filename (replace `X.Y.Z` with the actual version).
On macOS/Linux omit the `.exe` suffix.

### Interactive mode (recommended)

Double-click the file or run it with no arguments to launch the interactive setup wizard.
If `questionary` is bundled (it is in official releases), you get an arrow-key TUI;
otherwise a plain-text prompt flow is used automatically.

```sh
./vector-inspector-vX.Y.Z-installer
```

On a subsequent run the wizard detects an existing install and offers:
- **Replace** — clean reinstall to the same location
- **Update** — change extras/features without moving the install
- **Uninstall** — remove the install and desktop shortcut
- **Cancel**

### Non-interactive / scripted mode

All options can be passed as CLI flags to bypass the wizard:

```sh
# Install with extras
./vector-inspector-vX.Y.Z-installer --extras milvus,viz

# Install to a custom location
./vector-inspector-vX.Y.Z-installer --install-root /opt/VectorInspector

# Skip PATH registration
./vector-inspector-vX.Y.Z-installer --no-add-to-path

# Skip desktop shortcut
./vector-inspector-vX.Y.Z-installer --no-shortcut

# Recreate the venv from scratch
./vector-inspector-vX.Y.Z-installer --recreate-venv

# Install only, do not launch after
./vector-inspector-vX.Y.Z-installer --no-launch

# Disable winget Python fallback (Windows only)
./vector-inspector-vX.Y.Z-installer.exe --no-winget
```

## Using pip after installation

pip is used internally by the app to install optional providers at runtime.
To manually install or upgrade extras, use the venv python directly:

**Windows:**
```powershell
%LOCALAPPDATA%\VectorInspector\runtime\venv\Scripts\python.exe -m pip install vector-inspector[milvus]
```

**macOS:**
```sh
"$HOME/Library/Application Support/VectorInspector/runtime/venv/bin/python" -m pip install vector-inspector[milvus]
```

**Linux:**
```sh
~/.local/share/vectorinspector/runtime/venv/bin/python -m pip install vector-inspector[milvus]
```

## Updating an existing install

Run the installer again. It detects the existing install and presents a menu:
- Choose **Update** to change extras/features while keeping the install location.
- Choose **Replace** for a clean reinstall to the same location.

```sh
./vector-inspector-vX.Y.Z-installer
```

To force a clean environment rebuild non-interactively:

```sh
./vector-inspector-vX.Y.Z-installer --recreate-venv
```

## Uninstall

Run the installer and choose **Uninstall** from the menu, or pass `--uninstall` directly:

```sh
./vector-inspector-vX.Y.Z-installer --uninstall
```

This removes the install directory, desktop shortcut, and the installer's own config file.
Alternatively, delete the install root folder manually (`%LOCALAPPDATA%\VectorInspector` on Windows,
`~/Library/Application Support/VectorInspector` on macOS, `~/.local/share/vectorinspector` on Linux).

## Troubleshooting

### No compatible Python found

- **Windows:** Install Python 3.11+ from https://python.org or the Microsoft Store, or allow winget fallback by omitting `--no-winget`.
- **macOS:** `brew install python@3.11` or download from https://python.org.
- **Linux:** Use your distro package manager (e.g. `sudo apt install python3.11`).

### pip install fails for optional extras

Some extras include native dependencies and may need build tools or compatible wheels.

Recommended approach:

1. Start with core install.
2. Add only the extras you need.
3. Upgrade pip first, then retry — see [Using pip after installation](#using-pip-after-installation).

### Launcher exists but app does not start

Launch from the venv python directly to see error output:

**Windows:**
```powershell
%LOCALAPPDATA%\VectorInspector\runtime\venv\Scripts\vector-inspector.exe
```

**macOS/Linux:**
```sh
<install_root>/runtime/venv/bin/vector-inspector
```

## Notes for release engineering

- Platform-specific binaries are built automatically by `.github/workflows/build-installer.yml` when a GitHub release is published. No manual build step is needed for releases.
- To build locally (e.g. for testing), run `pdm run python scripts/build_installer.py` from the repo root on the target OS.
- The installer binary does not require Python to be pre-installed on the end-user's machine.
- Because it installs from PyPI into a live venv, users always get the latest published release and can manage optional extras at any time.
- The `questionary` TUI library is bundled into the binary at build time — end users do not need to install it.
