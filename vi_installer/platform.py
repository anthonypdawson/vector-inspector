"""Platform-specific paths and utilities."""

import os
import sys
from pathlib import Path

PLATFORM = sys.platform  # "win32", "darwin", "linux"


def get_default_install_root() -> Path:
    """Get the default installation root directory for the current platform.

    Returns:
        Path to platform-appropriate install directory:
        - Windows: %LOCALAPPDATA%/VectorInspector
        - macOS: ~/Library/Application Support/VectorInspector
        - Linux: ~/.local/share/vectorinspector
    """
    if PLATFORM == "win32":
        local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return local_appdata / "VectorInspector"
    if PLATFORM == "darwin":
        return Path.home() / "Library" / "Application Support" / "VectorInspector"
    # Linux / other Unix
    xdg_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return xdg_data / "vectorinspector"


def get_desktop_dir() -> Path:
    """Return the user's Desktop directory, accounting for OneDrive on Windows.

    Returns:
        Path to user's Desktop directory
    """
    desktop = Path.home() / "Desktop"
    if PLATFORM == "win32":
        onedrive = Path(os.environ.get("OneDrive", "")) / "Desktop"
        if not desktop.exists() and onedrive.exists():
            return onedrive
    return desktop


def detect_shell_rc() -> str:
    """Detect the user's shell RC file path.

    Returns:
        String path to shell RC file (~/.zshrc, ~/.bashrc, etc.)
    """
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        return "~/.zshrc"
    if "fish" in shell:
        return "~/.config/fish/config.fish"
    if "nu" in shell:
        return "~/.config/nushell/config.nu"
    return "~/.bashrc"


def print_step(message: str) -> None:
    """Print a step message with [bootstrap] prefix.

    Args:
        message: Message to print
    """
    print(f"[bootstrap] {message}")


def print_header(message: str) -> None:
    """Print a formatted header with separator lines.

    Args:
        message: Header text to display
    """
    print(f"\n{'=' * 60}\n  {message}\n{'=' * 60}")


def print_path_instructions(bin_dir: Path) -> None:
    """Print platform-specific instructions for adding to PATH.

    Args:
        bin_dir: Directory containing launcher executable
    """
    print_header("Add to PATH")
    if PLATFORM == "win32":
        print(f"  Add this directory to your user PATH:\n\n    {bin_dir}\n")
        print("  Via System Properties → Environment Variables → User variables → Path → Edit")
        print("\n  Or run in PowerShell:\n")
        print('    [Environment]::SetEnvironmentVariable("Path",')
        print(f'      $env:Path + ";{bin_dir}", "User")')
    else:
        shell_rc = detect_shell_rc()
        print(f"  Add this line to {shell_rc}:\n")
        print(f'    export PATH="{bin_dir}:$PATH"\n')
        print(f"  Then run:  source {shell_rc}")
    print()
