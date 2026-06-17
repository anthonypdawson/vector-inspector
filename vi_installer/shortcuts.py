"""Desktop shortcut creation for all platforms."""

import subprocess
from pathlib import Path

from vi_installer.platform import PLATFORM, get_desktop_dir, print_step

APP_NAME = "Vector Inspector"
APP_NAME_SLUG = "vector-inspector"


def get_desktop_shortcut_path() -> Path:
    """Get the expected path to the desktop shortcut.

    Returns:
        Path to desktop shortcut file
    """
    desktop = get_desktop_dir()
    if PLATFORM == "win32":
        return desktop / f"{APP_NAME}.lnk"
    elif PLATFORM == "darwin":
        return desktop / f"{APP_NAME}.command"
    else:
        return desktop / f"{APP_NAME_SLUG}.desktop"


def create_desktop_shortcut_windows(install_root: Path) -> None:
    """Create a .lnk shortcut on the Windows Desktop via PowerShell.

    Args:
        install_root: Installation root directory
    """
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
    """Create a .command launcher on the macOS Desktop.

    Args:
        install_root: Installation root directory
    """
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
    """Create a .desktop file on the Linux Desktop.

    Args:
        install_root: Installation root directory
    """
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
    """Create a platform-appropriate desktop shortcut.

    Args:
        install_root: Installation root directory
    """
    if PLATFORM == "win32":
        create_desktop_shortcut_windows(install_root)
    elif PLATFORM == "darwin":
        create_desktop_shortcut_macos(install_root)
    else:
        create_desktop_shortcut_linux(install_root)
