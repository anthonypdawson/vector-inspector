"""User interface (TUI/CLI) and main orchestration logic."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Import from our other modules
from vi_installer.platform import (
    PLATFORM,
    detect_shell_rc,
    get_default_install_root,
    print_header,
    print_path_instructions,
    print_step,
)
from vi_installer.python import (
    find_compatible_python,
    parse_min_version,
    suggest_python_install,
    try_install_python_with_winget,
)
from vi_installer.shortcuts import create_desktop_shortcut, get_desktop_shortcut_path
from vi_installer.state import (
    STATE_FILE_NAME,
    add_to_path_unix,
    add_to_path_windows,
    write_launchers,
    write_state_file,
)
from vi_installer.venv import (
    build_package_spec,
    ensure_venv,
    install_app,
    venv_app_entry_path,
)

# Constants
APP_NAME = "Vector Inspector"
APP_NAME_SLUG = "vector-inspector"
DEFAULT_PACKAGE = "vector-inspector"
DEFAULT_MIN_VERSION = (3, 11)
STATE_FILE_NAME = "bootstrap-state.json"


# ---------------------------------------------------------------------------
# Rollback Support


class InstallRollback:
    """Track installation artifacts for rollback on failure.

    Usage:
        rollback = InstallRollback()
        try:
            venv_dir = install_root / "runtime" / "venv"
            ensure_venv(...)
            rollback.track_directory(venv_dir)
            # ... more operations ...
            rollback.commit()  # Success - don't clean up
        except Exception:
            rollback.rollback()  # Failure - clean up
            raise
    """

    def __init__(self):
        self.directories: list[Path] = []
        self.files: list[Path] = []
        self.committed = False

    def track_directory(self, path: Path) -> None:
        """Track a directory to remove on rollback."""
        if path.exists():
            self.directories.append(path)

    def track_file(self, path: Path) -> None:
        """Track a file to remove on rollback."""
        if path.exists():
            self.files.append(path)

    def commit(self) -> None:
        """Mark installation as successful - skip rollback."""
        self.committed = True

    def rollback(self) -> None:
        """Remove all tracked artifacts."""
        if self.committed:
            return

        print_step("Installation failed. Rolling back...")

        for file in self.files:
            try:
                if file.exists():
                    file.unlink()
                    print_step(f"  Removed file: {file}")
            except Exception as exc:
                print_step(f"  Warning: Could not remove {file}: {exc}")

        for directory in self.directories:
            try:
                if directory.exists():
                    shutil.rmtree(directory)
                    print_step(f"  Removed directory: {directory}")
            except Exception as exc:
                print_step(f"  Warning: Could not remove {directory}: {exc}")

        print_step("Rollback complete.")

# Extras shown in the interactive menu
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

def _is_frozen() -> bool:
    """Return True when running inside a compiled (Nuitka/PyInstaller) binary.

    In a frozen binary sys.executable is the binary itself, so we cannot pip-install
    new packages into it, and newly installed packages would not be importable anyway.
    """
    # Nuitka onefile sets sys.frozen; PyInstaller sets sys._MEIPASS
    return getattr(sys, "frozen", False) or hasattr(sys, "_MEIPASS")


def _try_import_questionary():
    """Attempt to import questionary; return the module or None."""
    try:
        import questionary  # type: ignore[import-untyped]
        return questionary
    except ImportError:
        return None


def ensure_questionary():
    """Return the questionary module, prompting to install it if missing.

    In a frozen/compiled binary questionary is always bundled, so the import
    succeeds immediately. When running from source and questionary is absent,
    offers to pip-install it; falls back to plain input() prompts otherwise.
    """
    q = _try_import_questionary()
    if q is not None:
        return q
    if _is_frozen():
        # Should not happen — questionary is bundled at build time.
        return None
    if not sys.stdin.isatty():
        return None
    print_step("'questionary' not found — the arrow-key setup wizard is unavailable.")
    resp = input("Install 'questionary' now to enable it? [Y/n]: ").strip().lower()
    if resp not in ("", "y", "yes"):
        print_step("Continuing with plain-text prompts.")
        return None
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "questionary"])
    except Exception as exc:
        print_step(f"Failed to install questionary: {exc}")
        return None
    q = _try_import_questionary()
    if q is not None:
        print_step("'questionary' installed. Launching setup wizard...\n")
    else:
        print_step("'questionary' still not importable — using plain-text prompts.")
    return q

def _prompt_bool(question: str, default: bool) -> bool:
    """Simple y/n prompt with a default."""
    hint = "[Y/n]" if default else "[y/N]"
    while True:
        try:
            resp = input(f"{question} {hint}: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nInstallation cancelled.")
            sys.exit(0)
        if resp == "":
            return default
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("  Please enter y or n.")


def _prompt_choices(question: str, choices: list[str]) -> list[str]:
    """Print a numbered list and return the user-selected items."""
    print(f"\n{question}")
    for i, choice in enumerate(choices, 1):
        print(f"  {i:2d}. {choice}")
    print("  Enter numbers separated by commas, or press Enter to skip.")
    try:
        resp = input("  Selection: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nInstallation cancelled.")
        sys.exit(0)
    if not resp:
        return []
    selected = []
    for part in resp.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(choices):
                selected.append(choices[idx])
    return selected

def _run_cli_menu(args: argparse.Namespace, *, lock_install_root: bool = False) -> argparse.Namespace:
    """Plain input() fallback when questionary is unavailable."""
    print_header(f"{APP_NAME} Setup")
    print("  Answer each prompt and press Enter. Defaults are shown in [brackets].\n")

    try:
        if lock_install_root:
            print_step(f"Updating existing install at: {args.install_root}")
        else:
            try:
                resp = input(f"Install root [{args.install_root}]: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nInstallation cancelled.")
                sys.exit(0)
            if resp:
                args.install_root = resp

        providers = _prompt_choices("Database providers (optional):", KNOWN_PROVIDER_EXTRAS)
        features = _prompt_choices("Features (optional):", KNOWN_FEATURE_EXTRAS)
        bundles = _prompt_choices("Convenience bundles (optional):", KNOWN_BUNDLE_EXTRAS)
        all_extras = providers + features + bundles
        args.extras = ",".join(all_extras)

        args.add_to_path = _prompt_bool("Add launcher to PATH?", args.add_to_path)
        args.create_shortcut = _prompt_bool("Create desktop shortcut?", args.create_shortcut)
        launch = _prompt_bool("Launch after install?", not args.no_launch)
        args.no_launch = not launch

    except KeyboardInterrupt:
        print("\nInstallation cancelled.")
        sys.exit(0)

    print()
    return args

def run_interactive_menu(args: argparse.Namespace, *, lock_install_root: bool = False) -> argparse.Namespace:
    """Show an interactive installation menu when running in a TTY with no CLI args.

    Uses questionary (arrow-key TUI) when available; falls back to plain input()
    prompts otherwise. Exits cleanly on Ctrl+C.

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
        return _run_cli_menu(args, lock_install_root=lock_install_root)


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


def parse_args() -> argparse.Namespace:
    default_root = get_default_install_root()
    parser = argparse.ArgumentParser(
        description=f"Install {APP_NAME} into an app-local virtual environment with pip access.",
        epilog=f"Requires Python {DEFAULT_MIN_VERSION[0]}.{DEFAULT_MIN_VERSION[1]}+ (configurable via --python-min-version).",
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
# Install Check


def check_existing_install() -> tuple[Path | None, str | None]:
    """Check for an existing install and prompt user for action if found.

    Returns (None, None) immediately when running non-interactively (explicit
    CLI args present, or stdin is not a TTY) so scripted/automated runs are
    never blocked by an interactive prompt.

    Returns:
        Tuple of (install_path, mode) where mode is 'replace', 'update', 'uninstall', or None
    """
    if len(sys.argv) > 1 or not sys.stdin.isatty():
        return None, None
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
                # Validate this is a Vector Inspector install before deleting
                state_file = existing_path / STATE_FILE_NAME
                valid = False
                try:
                    data = json.loads(state_file.read_text(encoding="utf-8"))
                    valid = data.get("app") == APP_NAME
                except Exception:
                    pass
                if not valid:
                    print_step(
                        f"ERROR: {existing_path} does not appear to be a {APP_NAME} install "
                        "(missing or invalid bootstrap-state.json). Aborting to avoid data loss."
                    )
                    sys.exit(1)
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
# Uninstall


def run_uninstall(install_root: Path) -> int:
    """Remove the installed app, launcher, desktop shortcut, and config file."""
    config_dir = Path.home() / ".vector-inspector"
    install_path_file = config_dir / "install_path"
    shortcut = get_desktop_shortcut_path()

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
        # Validate this is actually a Vector Inspector install before deleting
        state_file = install_root / STATE_FILE_NAME
        valid = False
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            valid = data.get("app") == APP_NAME
        except Exception:
            pass
        if not valid:
            print_step(
                f"ERROR: {install_root} does not appear to be a {APP_NAME} install "
                "(missing or invalid bootstrap-state.json). Aborting to avoid data loss."
            )
            return 1
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

    # Warn about manual cleanup needed
    bin_dir = install_root / "bin"
    print()
    print("⚠️  Manual cleanup may be needed:")
    if PLATFORM == "win32":
        print(f"   • Windows PATH may still contain: {bin_dir}")
        print(f"     Remove via: System Properties → Environment Variables → Edit PATH")
    else:
        rc_file = detect_shell_rc()
        print(f"   • Shell RC file ({rc_file}) may still contain PATH export")
        print(f"     Remove the line: export PATH=\"{bin_dir}:$PATH\"")
    print()

    return 0


# ---------------------------------------------------------------------------
# Existing install check

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

    # Use rollback context to clean up on failure
    rollback = InstallRollback()
    try:
        venv_dir = install_root / "runtime" / "venv"
        python_in_venv = ensure_venv(python_cmd, venv_dir, recreate=args.recreate_venv)
        rollback.track_directory(venv_dir)

        install_app(python_in_venv, package_spec=package_spec, upgrade=not args.no_upgrade)

        app_launcher = write_launchers(install_root)
        rollback.track_file(app_launcher)
        print_step(f"App launcher : {app_launcher}")

        bin_dir = install_root / "bin"
        rollback.track_directory(bin_dir)

        if args.add_to_path:
            if PLATFORM == "win32":
                add_to_path_windows(bin_dir)
            else:
                add_to_path_unix(bin_dir)
        else:
            print_path_instructions(bin_dir)

        if args.create_shortcut:
            shortcut = get_desktop_shortcut_path()
            create_desktop_shortcut(install_root)
            rollback.track_file(shortcut)

        write_state_file(install_root, package_spec=package_spec, min_python_version=min_version)
        state_file = install_root / STATE_FILE_NAME
        rollback.track_file(state_file)

        # Success - commit and skip rollback
        rollback.commit()

    except Exception as exc:
        rollback.rollback()
        print_step(f"Installation failed: {exc}")
        return 1

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


def run_installer() -> int:
    """Main entry point for the installer.
    
    Returns:
        Exit code (0 for success)
    """
    return main()


if __name__ == "__main__":
    sys.exit(run_installer())
