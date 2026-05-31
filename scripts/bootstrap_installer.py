
"""Cross-platform bootstrap installer for Vector Inspector with app-local pip support.

Can be compiled to a standalone executable with Nuitka so no Python is required on
the target system:

    pdm run python scripts/build_bootstrap_exe.py

Or run directly with Python:

    python scripts/bootstrap_installer.py [options]

After installation, a 'vector-inspector' launcher is placed in <install_root>/bin/.
PATH registration and a desktop shortcut are created by default; use --no-add-to-path
or --no-shortcut to skip them. pip is used internally by the app to manage optional providers.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

APP_NAME = "Vector Inspector"
APP_NAME_SLUG = "vector-inspector"
DEFAULT_PACKAGE = "vector-inspector"
DEFAULT_MIN_VERSION = (3, 11)
STATE_FILE_NAME = "bootstrap-state.json"

PLATFORM = sys.platform  # "win32", "darwin", "linux"

# Extras shown in the interactive menu. Must match the [project.optional-dependencies]
# keys declared in vector-inspector's pyproject.toml.
KNOWN_PROVIDER_EXTRAS: list[str] = [
    "chromadb",
    "qdrant",
    "milvus",
    "pinecone",
    "lancedb",
    "pgvector",
    "weaviate",
]

KNOWN_FEATURE_EXTRAS: list[str] = [
    "embeddings",
    "clip",
    "viz",
    "documents",
    "llm",
]

KNOWN_BUNDLE_EXTRAS: list[str] = [
    "recommended",
    "starter",
    "cloud",
    "local",
    "all",
]


# ---------------------------------------------------------------------------
# Platform helpers
# ---------------------------------------------------------------------------


def get_default_install_root() -> Path:
    if PLATFORM == "win32":
        local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return local_appdata / "VectorInspector"
    if PLATFORM == "darwin":
        return Path.home() / "Library" / "Application Support" / "VectorInspector"
    # Linux / other Unix
    xdg_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return xdg_data / "vectorinspector"


def get_desktop_dir() -> Path:
    """Return the user's Desktop directory, accounting for OneDrive on Windows."""
    desktop = Path.home() / "Desktop"
    if PLATFORM == "win32":
        onedrive = Path(os.environ.get("OneDrive", "")) / "Desktop"
        if not desktop.exists() and onedrive.exists():
            return onedrive
    return desktop


def _detect_shell_rc() -> str:
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        return "~/.zshrc"
    if "fish" in shell:
        return "~/.config/fish/config.fish"
    return "~/.bashrc"


# ---------------------------------------------------------------------------
# Printing helpers
# ---------------------------------------------------------------------------


def print_step(message: str) -> None:
    print(f"[bootstrap] {message}")


def print_header(message: str) -> None:
    print(f"\n{'=' * 60}\n  {message}\n{'=' * 60}")


def print_path_instructions(bin_dir: Path) -> None:
    print_header("Add to PATH")
    if PLATFORM == "win32":
        print(f"  Add this directory to your user PATH:\n\n    {bin_dir}\n")
        print("  Via System Properties → Environment Variables → User variables → Path → Edit")
        print("\n  Or run in PowerShell:\n")
        print('    [Environment]::SetEnvironmentVariable("Path",')
        print(f'      $env:Path + ";{bin_dir}", "User")')
    else:
        shell_rc = _detect_shell_rc()
        print(f"  Add this line to {shell_rc}:\n")
        print(f'    export PATH="{bin_dir}:$PATH"\n')
        print(f"  Then run:  source {shell_rc}")
    print()


def run_command(
    cmd: Sequence[str],
    *,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    printable = " ".join(str(part) for part in cmd)
    print_step(f"Running: {printable}")
    return subprocess.run(
        list(cmd),
        check=check,
        text=True,
        capture_output=capture_output,
    )


def parse_min_version(value: str) -> tuple[int, int]:
    parts = value.strip().split(".")
    if len(parts) != 2:
        raise ValueError("--python-min-version must be in MAJOR.MINOR format, e.g. 3.11")
    major, minor = int(parts[0]), int(parts[1])
    return major, minor


def read_python_version(python_cmd: Sequence[str]) -> tuple[int, int] | None:
    try:
        result = run_command(
            [*python_cmd, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    text = (result.stdout or "").strip()
    if not text:
        return None
    parts = text.split(".")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def discover_python_candidates() -> list[list[str]]:
    candidates: list[list[str]] = []

    if sys.executable:
        candidates.append([sys.executable])

    if PLATFORM == "win32":
        candidates.extend(
            [
                ["py", "-3.12"],
                ["py", "-3.11"],
                ["python"],
                ["python3"],
            ]
        )
        local_programs = Path.home() / "AppData" / "Local" / "Programs" / "Python"
        for folder_name in ("Python312", "Python311", "Python310"):
            exe_path = local_programs / folder_name / "python.exe"
            if exe_path.exists():
                candidates.append([str(exe_path)])
    else:
        candidates.extend(
            [
                ["python3.12"],
                ["python3.11"],
                ["python3"],
                ["python"],
            ]
        )
        # Homebrew (macOS)
        if PLATFORM == "darwin":
            for version in ("3.12", "3.11"):
                for prefix in ("/opt/homebrew/bin", "/usr/local/bin"):
                    p = Path(prefix) / f"python{version}"
                    if p.exists():
                        candidates.append([str(p)])
        # pyenv (macOS + Linux)
        pyenv_root = Path(os.environ.get("PYENV_ROOT", Path.home() / ".pyenv"))
        for version in ("3.12", "3.11"):
            p = pyenv_root / "versions" / version / "bin" / "python3"
            if p.exists():
                candidates.append([str(p)])

    # Deduplicate while preserving order
    deduped: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for candidate in candidates:
        key = tuple(candidate)
        if key not in seen:
            deduped.append(candidate)
            seen.add(key)
    return deduped


def find_compatible_python(min_version: tuple[int, int]) -> list[str] | None:
    for candidate in discover_python_candidates():
        version = read_python_version(candidate)
        if version is not None and version >= min_version:
            print_step(f"Using Python {version[0]}.{version[1]} via: {' '.join(candidate)}")
            return candidate
    return None


def try_install_python_with_winget(min_version: tuple[int, int]) -> bool:
    if PLATFORM != "win32":
        return False
    if shutil.which("winget") is None:
        print_step("winget not found; cannot auto-install Python.")
        return False

    major, minor = min_version
    preferred_ids = [f"Python.Python.{major}.{minor}"]
    if (major, minor) != (3, 12):
        preferred_ids.append("Python.Python.3.12")
    if (major, minor) != (3, 11):
        preferred_ids.append("Python.Python.3.11")

    for package_id in preferred_ids:
        try:
            run_command(
                [
                    "winget",
                    "install",
                    "-e",
                    "--id",
                    package_id,
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                    "--silent",
                ]
            )
            print_step(f"Installed Python via winget: {package_id}")
            return True
        except subprocess.CalledProcessError:
            print_step(f"winget install failed for {package_id}; trying next.")
    return False


def suggest_python_install(min_version: tuple[int, int]) -> None:
    major, minor = min_version
    if PLATFORM == "win32":
        print_step("Install Python from https://python.org/downloads/ or the Microsoft Store.")
    elif PLATFORM == "darwin":
        print_step(f"Install Python via Homebrew:  brew install python@{major}.{minor}")
        print_step("Or download from https://python.org/downloads/")
    else:
        for mgr, cmd in (
            ("apt", f"sudo apt install python{major}.{minor}"),
            ("dnf", f"sudo dnf install python{major}.{minor}"),
            ("pacman", "sudo pacman -S python"),
        ):
            if shutil.which(mgr):
                print_step(f"Install Python: {cmd}")
                return
        print_step(f"Install Python {major}.{minor}+ from your package manager or https://python.org")


# ---------------------------------------------------------------------------
# Platform helpers (venv)
# ---------------------------------------------------------------------------


def venv_python_path(venv_dir: Path) -> Path:
    if PLATFORM == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def venv_app_entry_path(venv_dir: Path) -> Path:
    if PLATFORM == "win32":
        return venv_dir / "Scripts" / f"{APP_NAME_SLUG}.exe"
    return venv_dir / "bin" / APP_NAME_SLUG


# ---------------------------------------------------------------------------
# Venv and package install
# ---------------------------------------------------------------------------


def ensure_venv(base_python: Sequence[str], venv_dir: Path, recreate: bool) -> Path:
    if recreate and venv_dir.exists():
        print_step(f"Removing existing environment: {venv_dir}")
        shutil.rmtree(venv_dir)

    python_in_venv = venv_python_path(venv_dir)
    if not python_in_venv.exists():
        venv_dir.parent.mkdir(parents=True, exist_ok=True)
        run_command([*base_python, "-m", "venv", str(venv_dir)])

    return python_in_venv


def build_package_spec(package: str, extras: list[str]) -> str:
    if not extras:
        return package
    return f"{package}[{','.join(extras)}]"


def install_app(python_in_venv: Path, package_spec: str, upgrade: bool) -> None:
    run_command([str(python_in_venv), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    cmd = [str(python_in_venv), "-m", "pip", "install"]
    if upgrade:
        cmd.append("--upgrade")
    cmd.append(package_spec)
    run_command(cmd)


# ---------------------------------------------------------------------------
# Launcher generation
# ---------------------------------------------------------------------------


def write_launchers(install_root: Path) -> Path:
    bin_dir = install_root / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    if PLATFORM == "win32":
        app_launcher = bin_dir / f"{APP_NAME_SLUG}.cmd"
        app_launcher.write_text(
            f'@echo off\nsetlocal\n"%~dp0..\\runtime\\venv\\Scripts\\{APP_NAME_SLUG}.exe" %*\n',
            encoding="utf-8",
        )
    else:
        venv_bin = install_root / "runtime" / "venv" / "bin"
        app_launcher = bin_dir / APP_NAME_SLUG
        app_launcher.write_text(
            f'#!/usr/bin/env sh\nexec "{venv_bin}/{APP_NAME_SLUG}" "$@"\n',
            encoding="utf-8",
        )
        app_launcher.chmod(0o755)

    return app_launcher


# ---------------------------------------------------------------------------
# PATH integration
# ---------------------------------------------------------------------------


def add_to_path_windows(bin_dir: Path) -> bool:
    """Append bin_dir to the user PATH in the Windows registry."""
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Environment",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        ) as key:
            try:
                current, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current = ""
            bin_str = str(bin_dir)
            if bin_str.lower() not in current.lower():
                new_value = f"{current};{bin_str}" if current else bin_str
                winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_value)
                print_step("Added to user PATH in registry.")
                # Broadcast WM_SETTINGCHANGE so open shells pick it up immediately
                import ctypes

                HWND_BROADCAST = 0xFFFF
                WM_SETTINGCHANGE = 0x001A
                ctypes.windll.user32.SendMessageTimeoutW(
                    HWND_BROADCAST,
                    WM_SETTINGCHANGE,
                    0,
                    "Environment",
                    2,
                    5000,
                    None,
                )
            else:
                print_step("Already in user PATH; skipping.")
        return True
    except Exception as exc:
        print_step(f"Could not update PATH in registry: {exc}")
        return False


def add_to_path_unix(bin_dir: Path) -> None:
    """Append an export line to the user's shell RC file."""
    rc_file = Path(_detect_shell_rc()).expanduser()
    export_line = f'\nexport PATH="{bin_dir}:$PATH"  # added by Vector Inspector installer\n'
    try:
        existing = rc_file.read_text(encoding="utf-8") if rc_file.exists() else ""
        if str(bin_dir) not in existing:
            with rc_file.open("a", encoding="utf-8") as f:
                f.write(export_line)
            print_step(f"Added PATH export to {rc_file}")
            print_step(f"Run 'source {rc_file}' or open a new terminal to apply.")
        else:
            print_step(f"Already found in {rc_file}; skipping PATH update.")
    except OSError as exc:
        print_step(f"Could not update {rc_file}: {exc}")


# ---------------------------------------------------------------------------
# Desktop shortcut
# ---------------------------------------------------------------------------


def create_desktop_shortcut_windows(install_root: Path) -> None:
    """Create a .lnk shortcut on the Windows Desktop via PowerShell."""
    desktop = get_desktop_dir()
    shortcut_path = desktop / f"{APP_NAME}.lnk"
    target = install_root / "runtime" / "venv" / "Scripts" / f"{APP_NAME_SLUG}.exe"
    ps_script = (
        "$WshShell = New-Object -ComObject WScript.Shell; "
        f"$S = $WshShell.CreateShortcut('{shortcut_path}'); "
        f"$S.TargetPath = '{target}'; "
        f"$S.IconLocation = '{target},0'; "
        f"$S.Description = '{APP_NAME}'; "
        "$S.Save()"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], check=True)
        print_step(f"Desktop shortcut created: {shortcut_path}")
    except subprocess.CalledProcessError as exc:
        print_step(f"Could not create desktop shortcut: {exc}")


def create_desktop_shortcut_macos(install_root: Path) -> None:
    """Create a .command launcher on the macOS Desktop."""
    desktop = get_desktop_dir()
    shortcut = desktop / f"{APP_NAME}.command"
    target = install_root / "runtime" / "venv" / "bin" / APP_NAME_SLUG
    shortcut.write_text(
        f'#!/usr/bin/env sh\nexec "{target}"\n',
        encoding="utf-8",
    )
    shortcut.chmod(0o755)
    print_step(f"Desktop shortcut created: {shortcut}")


def create_desktop_shortcut_linux(install_root: Path) -> None:
    """Create a .desktop file on the Linux Desktop."""
    desktop = get_desktop_dir()
    desktop.mkdir(parents=True, exist_ok=True)
    shortcut = desktop / f"{APP_NAME_SLUG}.desktop"
    target = install_root / "runtime" / "venv" / "bin" / APP_NAME_SLUG

    # Try to find a bundled icon
    icon = ""
    for candidate in (
        install_root / "runtime" / "venv" / "share" / APP_NAME_SLUG / "icon.png",
        install_root
        / "runtime"
        / "venv"
        / "lib"
        / "python3"
        / "site-packages"
        / "vector_inspector"
        / "assets"
        / "icon.png",
    ):
        if candidate.exists():
            icon = str(candidate)
            break

    shortcut.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_NAME}\n"
        f"Exec={target}\n"
        f"Icon={icon}\n"
        "Terminal=false\n"
        "Categories=Utility;Science;\n",
        encoding="utf-8",
    )
    shortcut.chmod(0o755)
    print_step(f"Desktop shortcut created: {shortcut}")


def create_desktop_shortcut(install_root: Path) -> None:
    if PLATFORM == "win32":
        create_desktop_shortcut_windows(install_root)
    elif PLATFORM == "darwin":
        create_desktop_shortcut_macos(install_root)
    else:
        create_desktop_shortcut_linux(install_root)


# ---------------------------------------------------------------------------
# State file
# ---------------------------------------------------------------------------


def write_state_file(
    install_root: Path,
    *,
    package_spec: str,
    min_python_version: tuple[int, int],
) -> None:
    ext = ".cmd" if PLATFORM == "win32" else ""
    state_file = install_root / STATE_FILE_NAME
    data = {
        "app": APP_NAME,
        "platform": PLATFORM,
        "package_spec": package_spec,
        "min_python_version": f"{min_python_version[0]}.{min_python_version[1]}",
        "venv": str((install_root / "runtime" / "venv").resolve()),
        "launchers": {
            "app": str((install_root / "bin" / f"{APP_NAME_SLUG}{ext}").resolve()),
        },
    }
    state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # Also write the install root to ~/.vector-inspector/install_path for uninstaller
    try:
        config_dir = Path.home() / ".vector-inspector"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "install_path").write_text(str(install_root), encoding="utf-8")
    except Exception as exc:
        print_step(f"Warning: Could not write install path config: {exc}")


# ---------------------------------------------------------------------------
# Interactive console menu (questionary)
# ---------------------------------------------------------------------------


def _try_import_questionary():
    """Attempt to import questionary; return the module or None."""
    try:
        import questionary  # type: ignore[import-untyped]
        return questionary
    except ImportError:
        return None


def ensure_questionary():
    """Return the questionary module, prompting to install it if missing.

    Returns None if unavailable and the user declined or stdin is not a TTY.
    """
    q = _try_import_questionary()
    if q is not None:
        return q
    print_step("'questionary' not found — interactive setup wizard is unavailable.")
    if not sys.stdin.isatty():
        return None
    resp = input("Would you like to install 'questionary' now to enable the setup wizard? [Y/n]: ").strip().lower()
    if resp not in ("", "y", "yes"):
        print_step("Continuing without interactive setup wizard.")
        return None
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "questionary"])
    except Exception as exc:
        print_step(f"Failed to install questionary: {exc}")
        return None
    q = _try_import_questionary()
    if q is not None:
        print_step("'questionary' installed successfully. Launching setup wizard...\n")
    else:
        print_step("'questionary' still not importable after install.")
    return q


def run_interactive_menu(args: argparse.Namespace, *, lock_install_root: bool = False) -> argparse.Namespace:
    """Show an interactive installation menu when running in a TTY with no CLI args.

    Falls back silently if *questionary* is not importable or stdin is not a TTY.
    Exits cleanly on Ctrl+C.

    When *lock_install_root* is True (Update mode), the install directory prompt
    is skipped — only features/extras and launch options can be changed.
    """
    if not sys.stdin.isatty():
        return args
    # Only show the menu when the user ran the installer with no arguments
    # (e.g. double-clicked the executable).  Explicit CLI flags bypass it.
    if len(sys.argv) > 1:
        return args

    questionary = ensure_questionary()
    if questionary is None:
        return args


    print_header(f"{APP_NAME} Setup")
    print("  Use arrow keys to navigate, Space to toggle checkboxes, Enter to confirm.")
    print("  Press Ctrl+C at any time to cancel.\n")

    try:
        if lock_install_root:
            print_step(f"Updating existing install at: {args.install_root}")
        else:
            install_root = questionary.text(
                "Install root:",
                default=args.install_root,
            ).ask()
            if install_root is None:
                sys.exit(0)
            args.install_root = install_root

        selected_providers = questionary.checkbox(
            "Database providers:",
            choices=KNOWN_PROVIDER_EXTRAS,
            instruction="(Space to select, Enter to confirm — leave empty for core only)",
        ).ask()
        if selected_providers is None:
            sys.exit(0)

        selected_features = questionary.checkbox(
            "Features:",
            choices=KNOWN_FEATURE_EXTRAS,
            instruction="(Space to select, Enter to confirm)",
        ).ask()
        if selected_features is None:
            sys.exit(0)

        selected_bundles = questionary.checkbox(
            "Convenience bundles (optional — override individual selections above):",
            choices=KNOWN_BUNDLE_EXTRAS,
            instruction="(Space to select, Enter to confirm — leave empty to skip)",
        ).ask()
        if selected_bundles is None:
            sys.exit(0)

        all_extras = selected_providers + selected_features + selected_bundles
        args.extras = ",".join(all_extras)

        add_to_path = questionary.confirm(
            "Add launcher to PATH?",
            default=args.add_to_path,
        ).ask()
        if add_to_path is None:
            sys.exit(0)
        args.add_to_path = add_to_path

        create_shortcut = questionary.confirm(
            "Create desktop shortcut?",
            default=args.create_shortcut,
        ).ask()
        if create_shortcut is None:
            sys.exit(0)
        args.create_shortcut = create_shortcut

        launch_after_install = questionary.confirm(
            "Launch after install?",
            default=not args.no_launch,
        ).ask()
        if launch_after_install is None:
            sys.exit(0)
        args.no_launch = not launch_after_install

    except KeyboardInterrupt:
        print("\nInstallation cancelled.")
        sys.exit(0)

    print()
    return args


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    default_root = get_default_install_root()
    parser = argparse.ArgumentParser(
        description=f"Install {APP_NAME} into an app-local virtual environment with pip access.",
    )
    parser.add_argument(
        "--install-root",
        default=str(default_root),
        help=f"Install root directory (default: {default_root})",
    )
    parser.add_argument(
        "--package",
        default=DEFAULT_PACKAGE,
        help=f"Base package to install from pip (default: {DEFAULT_PACKAGE})",
    )
    parser.add_argument(
        "--extras",
        default="",
        help="Comma-separated extras to install (e.g. 'recommended' or 'milvus,viz')",
    )
    parser.add_argument(
        "--python-min-version",
        default=f"{DEFAULT_MIN_VERSION[0]}.{DEFAULT_MIN_VERSION[1]}",
        help="Minimum required Python version in MAJOR.MINOR format (default: 3.11)",
    )
    parser.add_argument(
        "--recreate-venv",
        action="store_true",
        help="Recreate the virtual environment from scratch.",
    )
    parser.add_argument(
        "--no-upgrade",
        action="store_true",
        help="Do not pass --upgrade when installing the package.",
    )
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Install only; do not launch the app after install.",
    )
    if PLATFORM == "win32":
        parser.add_argument(
            "--no-winget",
            action="store_true",
            help="Do not use winget to auto-install Python when missing.",
        )
    parser.add_argument(
        "--no-add-to-path",
        dest="add_to_path",
        action="store_false",
        default=True,
        help=(
            "Skip adding the launcher bin directory to the user PATH "
            "(registry on Windows, shell RC file on macOS/Linux)."
        ),
    )
    parser.add_argument(
        "--no-shortcut",
        dest="create_shortcut",
        action="store_false",
        default=True,
        help="Skip creating a desktop shortcut for Vector Inspector.",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall Vector Inspector and remove all created files.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------------


def _get_desktop_shortcut_path() -> Path:
    desktop = get_desktop_dir()
    if PLATFORM == "win32":
        return desktop / f"{APP_NAME}.lnk"
    if PLATFORM == "darwin":
        return desktop / f"{APP_NAME}.command"
    return desktop / f"{APP_NAME_SLUG}.desktop"


def run_uninstall(install_root: Path) -> int:
    """Remove the installed app, launcher, desktop shortcut, and config file."""
    config_dir = Path.home() / ".vector-inspector"
    install_path_file = config_dir / "install_path"
    shortcut = _get_desktop_shortcut_path()

    print_header(f"Uninstall {APP_NAME}")
    print(f"  Install directory : {install_root}")
    print(f"  Desktop shortcut  : {shortcut}")
    print(f"  Config file       : {install_path_file}")
    print()

    q = ensure_questionary()
    if q is not None:
        confirmed = q.confirm("Proceed with uninstall?", default=False).ask()
        if not confirmed:
            print_step("Uninstall cancelled.")
            return 0
    else:
        resp = input("Proceed with uninstall? [y/N]: ").strip().lower()
        if resp not in ("y", "yes"):
            print_step("Uninstall cancelled.")
            return 0

    if install_root.exists():
        shutil.rmtree(install_root)
        print_step(f"Removed: {install_root}")
    else:
        print_step(f"Not found (skipped): {install_root}")

    if shortcut.exists():
        shortcut.unlink()
        print_step(f"Removed: {shortcut}")
    else:
        print_step(f"Not found (skipped): {shortcut}")

    if install_path_file.exists():
        install_path_file.unlink()
        print_step(f"Removed: {install_path_file}")
    try:
        config_dir.rmdir()  # only removes if empty
    except OSError:
        pass

    print_step(f"{APP_NAME} has been uninstalled.")
    return 0


# ---------------------------------------------------------------------------
# Existing install check
# ---------------------------------------------------------------------------


def check_existing_install():
    """Check for an existing install and prompt user for action if found."""
    config_dir = Path.home() / ".vector-inspector"
    install_path_file = config_dir / "install_path"
    if install_path_file.exists():
        try:
            existing_path = Path(install_path_file.read_text(encoding="utf-8").strip()).expanduser().resolve()
        except Exception:
            return None, None
        if existing_path.exists():
            def ask_action():
                q = ensure_questionary()
                if q is not None:
                    return q.select(
                        f"Existing installation found at {existing_path}. What would you like to do?",
                        choices=[
                            "Replace (clean install)",
                            "Update (change features/extras)",
                            "Uninstall",
                            "Cancel",
                        ],
                    ).ask()
                print(f"Existing installation found at {existing_path}.")
                print("[1] Replace (clean install)")
                print("[2] Update (change features/extras)")
                print("[3] Uninstall")
                print("[4] Cancel")
                resp = input("Enter choice [1-4]: ").strip()
                if resp == "1":
                    return "Replace (clean install)"
                elif resp == "2":
                    return "Update (change features/extras)"
                elif resp == "3":
                    return "Uninstall"
                else:
                    return "Cancel"
            action = ask_action()
            if action == "Replace (clean install)":
                print_step(f"Removing previous install at {existing_path}...")
                try:
                    shutil.rmtree(existing_path)
                except Exception as exc:
                    print_step(f"Failed to remove previous install: {exc}")
                    sys.exit(1)
                return existing_path, "replace"
            elif action == "Update (change features/extras)":
                return existing_path, "update"
            elif action == "Uninstall":
                return existing_path, "uninstall"
            else:
                print_step("Cancelled.")
                sys.exit(0)
    return None, None

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _print_installer_tip() -> None:
    print()
    print_header(f"Managing your {APP_NAME} installation")
    print("  Re-run this installer at any time to:")
    print("    - Update installed database providers or feature extras")
    print("    - Add or remove the launcher from your PATH")
    print("    - Create or remove the desktop shortcut")
    print("    - Change whether the app launches after install")
    print("    - Uninstall completely")
    print()
    print("  Or use CLI flags directly:")
    print(f"    --uninstall          Remove {APP_NAME} and all created files")
    print(f"    --extras <list>      Change installed extras, e.g. 'chromadb,viz'")
    print(f"    --no-add-to-path     Skip PATH registration")
    print(f"    --no-shortcut        Skip desktop shortcut")
    print(f"    --no-launch          Install without launching")
    print()


def main() -> int:
    args = parse_args()

    # --uninstall flag: read install path from config and uninstall directly
    if getattr(args, "uninstall", False):
        config_dir = Path.home() / ".vector-inspector"
        install_path_file = config_dir / "install_path"
        if not install_path_file.exists():
            print_step("No install path config found. Cannot determine what to uninstall.")
            return 1
        install_root = Path(install_path_file.read_text(encoding="utf-8").strip()).expanduser().resolve()
        return run_uninstall(install_root)

    existing_path, install_mode = check_existing_install()

    if install_mode == "uninstall" and existing_path is not None:
        return run_uninstall(existing_path)

    if install_mode == "update" and existing_path is not None:
        args.install_root = str(existing_path)
        args = run_interactive_menu(args, lock_install_root=True)
    else:
        args = run_interactive_menu(args)

    try:
        min_version = parse_min_version(args.python_min_version)
    except ValueError as exc:
        print_step(str(exc))
        return 2

    install_root = Path(args.install_root).expanduser().resolve()
    extras = [p.strip() for p in args.extras.split(",") if p.strip()]
    package_spec = build_package_spec(args.package, extras)

    print_step(f"Platform    : {PLATFORM} ({platform.machine()})")
    print_step(f"Install root: {install_root}")
    print_step(f"Package spec: {package_spec}")

    python_cmd = find_compatible_python(min_version)
    if python_cmd is None:
        no_winget = getattr(args, "no_winget", True)
        if PLATFORM == "win32" and not no_winget:
            print_step("No compatible Python found. Attempting winget install...")
            if try_install_python_with_winget(min_version):
                python_cmd = find_compatible_python(min_version)

    if python_cmd is None:
        print_step("No compatible Python interpreter found.")
        suggest_python_install(min_version)
        return 1

    venv_dir = install_root / "runtime" / "venv"
    python_in_venv = ensure_venv(python_cmd, venv_dir, recreate=args.recreate_venv)

    install_app(python_in_venv, package_spec=package_spec, upgrade=not args.no_upgrade)

    app_launcher = write_launchers(install_root)
    print_step(f"App launcher : {app_launcher}")

    bin_dir = install_root / "bin"
    if args.add_to_path:
        if PLATFORM == "win32":
            add_to_path_windows(bin_dir)
        else:
            add_to_path_unix(bin_dir)
    else:
        print_path_instructions(bin_dir)

    if args.create_shortcut:
        create_desktop_shortcut(install_root)

    write_state_file(install_root, package_spec=package_spec, min_python_version=min_version)

    if args.no_launch:
        print_step("Installation complete. Launch skipped by request.")
        _print_installer_tip()
        return 0

    entry = venv_app_entry_path(venv_dir)
    if not entry.exists():
        print_step(f"Expected app entry not found: {entry}")
        print_step(f"You can still launch via: {python_in_venv} -m vector_inspector")
        return 1

    print_step(f"Launching {APP_NAME}...")
    _print_installer_tip()
    subprocess.Popen([str(entry)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
