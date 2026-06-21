"""Python discovery and version management."""

import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from vi_installer.platform import PLATFORM, print_step


def run_command(
    cmd: Sequence[str],
    *,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a command and print it for visibility.

    Args:
        cmd: Command and arguments to run
        check: Raise CalledProcessError on non-zero exit
        capture_output: Capture stdout/stderr

    Returns:
        CompletedProcess instance
    """
    printable = " ".join(str(part) for part in cmd)
    print_step(f"Running: {printable}")
    return subprocess.run(
        list(cmd),
        check=check,
        text=True,
        capture_output=capture_output,
    )


def parse_min_version(value: str) -> tuple[int, int]:
    """Parse a version string like '3.11' into (major, minor) tuple.

    Args:
        value: Version string in MAJOR.MINOR format

    Returns:
        Tuple of (major, minor) integers

    Raises:
        ValueError: If format is invalid
    """
    parts = value.strip().split(".")
    if len(parts) != 2:
        raise ValueError("--python-min-version must be in MAJOR.MINOR format, e.g. 3.11")
    major, minor = int(parts[0]), int(parts[1])
    return major, minor


def read_python_version(python_cmd: Sequence[str]) -> tuple[int, int] | None:
    """Read the Python version from a Python executable.

    Args:
        python_cmd: Command to invoke Python (e.g., ['python'] or ['py', '-3.11'])

    Returns:
        Tuple of (major, minor) or None if unable to determine
    """
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
    """Discover potential Python executables on the system.

    Returns:
        List of command arrays that might invoke Python
        Example: [['python3'], ['py', '-3.11'], ['/usr/bin/python3.12']]
    """
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
    """Find a Python executable that meets the minimum version requirement.

    Args:
        min_version: Minimum required (major, minor) version

    Returns:
        Command array to invoke Python, or None if not found
    """
    for candidate in discover_python_candidates():
        version = read_python_version(candidate)
        if version is not None and version >= min_version:
            print_step(f"Using Python {version[0]}.{version[1]} via: {' '.join(candidate)}")
            return candidate
    return None


def try_install_python_with_winget(min_version: tuple[int, int]) -> bool:
    """Attempt to install Python via winget on Windows.

    Args:
        min_version: Minimum required (major, minor) version

    Returns:
        True if successfully installed, False otherwise
    """
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
    """Print platform-specific instructions for installing Python.

    Args:
        min_version: Required (major, minor) version
    """
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
