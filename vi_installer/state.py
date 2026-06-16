"""Install state management and PATH integration."""

import json
from pathlib import Path

from vi_installer.platform import PLATFORM, detect_shell_rc, print_step

APP_NAME = "Vector Inspector"
APP_NAME_SLUG = "vector-inspector"
STATE_FILE_NAME = "bootstrap-state.json"


def write_launchers(install_root: Path) -> Path:
    """Create launcher scripts in <install_root>/bin.

    Args:
        install_root: Installation root directory

    Returns:
        Path to the created launcher script
    """
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


def add_to_path_windows(bin_dir: Path) -> bool:
    """Append bin_dir to the user PATH in the Windows registry.

    Args:
        bin_dir: Directory to add to PATH

    Returns:
        True if successful, False otherwise
    """
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
            current_entries = [e.lower() for e in current.split(";") if e]
            if bin_str.lower() not in current_entries:
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
    """Append an export line to the user's shell RC file.

    Args:
        bin_dir: Directory to add to PATH
    """
    rc_file = Path(detect_shell_rc()).expanduser()
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


def write_state_file(
    install_root: Path,
    *,
    package_spec: str,
    min_python_version: tuple[int, int],
) -> None:
    """Write installation state to a JSON file.

    Args:
        install_root: Installation root directory
        package_spec: Package specification that was installed
        min_python_version: Minimum Python version required
    """
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


def check_existing_install() -> Path | None:
    """Check for an existing installation.

    Returns:
        Path to existing install root, or None if not found
    """
    config_dir = Path.home() / ".vector-inspector"
    install_path_file = config_dir / "install_path"
    if not install_path_file.exists():
        return None
    try:
        install_root = Path(install_path_file.read_text(encoding="utf-8").strip())
        if install_root.exists():
            return install_root
    except Exception:
        pass
    return None
