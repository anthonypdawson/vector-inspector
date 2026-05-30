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

Build helper script: [scripts/build_bootstrap_exe.py](../scripts/build_bootstrap_exe.py)

Nuitka compiles `bootstrap_installer.py` into a standalone executable that runs
on a machine with **no Python pre-installed**. You must build on the target OS.

### Prerequisites

- [pipx](https://pipx.pypa.io) installed — Nuitka is run ephemerally via `pipx run nuitka`, so it does **not** need to be a project dependency.
- A C compiler available on the build machine (MSVC on Windows, Xcode CLT on macOS, gcc/clang on Linux).

Build the executable:

```sh
python scripts/build_bootstrap_exe.py
```

Output (varies by platform):

| Platform | Output file |
|----------|-------------|
| Windows  | `build/bootstrap-installer/bootstrap_installer.exe` |
| macOS    | `build/bootstrap-installer/bootstrap_installer` |
| Linux    | `build/bootstrap-installer/bootstrap_installer` |

## Use the bootstrap executable

Examples below use the Windows `.exe`; on macOS/Linux omit the `.exe`.

Default install (auto-detects platform paths):

```sh
./bootstrap_installer
```

Install with extras:

```sh
./bootstrap_installer --extras milvus,viz
```

Install to a custom location:

```sh
./bootstrap_installer --install-root /opt/VectorInspector
```

Add to PATH automatically:

```sh
./bootstrap_installer
```

Create a desktop shortcut:

```sh
./bootstrap_installer
```

Skip PATH registration:

```sh
./bootstrap_installer --no-add-to-path
```

Skip desktop shortcut:

```sh
./bootstrap_installer --no-shortcut
```

Recreate the environment from scratch:

```sh
./bootstrap_installer --recreate-venv
```

Install only (no immediate app launch):

```sh
./bootstrap_installer --no-launch
```

Disable winget fallback (Windows only):

```sh
./bootstrap_installer.exe --no-winget
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

Run the bootstrap installer again. It reuses the existing venv by default and upgrades Vector Inspector.

```powershell
.\bootstrap_installer.exe
```

To force a clean environment rebuild:

```powershell
.\bootstrap_installer.exe --recreate-venv
```

## Uninstall

Delete the install root folder (default `%LOCALAPPDATA%/VectorInspector`). This removes the app-local venv and launchers.

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

- Build the bootstrap executable on each target platform (Windows, macOS, Linux) to produce platform-specific binaries.
- The bootstrap executable is the primary distribution method for Vector Inspector — it does not require Python to be pre-installed.
- Because it installs from PyPI into a live venv, users always get the latest published release and can manage optional extras at any time.
