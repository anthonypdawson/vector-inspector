"""Virtual environment creation and package installation."""

import shutil
from collections.abc import Sequence
from pathlib import Path

from vi_installer.platform import PLATFORM, print_step
from vi_installer.python import run_command

APP_NAME_SLUG = "vector-inspector"


def venv_python_path(venv_dir: Path) -> Path:
    """Get the path to the Python executable inside a venv.

    Args:
        venv_dir: Virtual environment directory

    Returns:
        Path to python executable
    """
    if PLATFORM == "win32":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def venv_app_entry_path(venv_dir: Path) -> Path:
    """Get the path to the app entry point inside a venv.

    Args:
        venv_dir: Virtual environment directory

    Returns:
        Path to app executable/script
    """
    if PLATFORM == "win32":
        return venv_dir / "Scripts" / f"{APP_NAME_SLUG}.exe"
    return venv_dir / "bin" / APP_NAME_SLUG


def ensure_venv(base_python: Sequence[str], venv_dir: Path, recreate: bool) -> Path:
    """Create or verify a virtual environment.

    Args:
        base_python: Command to invoke base Python
        venv_dir: Directory for virtual environment
        recreate: If True, remove and recreate existing venv

    Returns:
        Path to Python executable in the venv
    """
    if recreate and venv_dir.exists():
        print_step(f"Removing existing environment: {venv_dir}")
        shutil.rmtree(venv_dir)

    python_in_venv = venv_python_path(venv_dir)
    if not python_in_venv.exists():
        venv_dir.parent.mkdir(parents=True, exist_ok=True)
        run_command([*base_python, "-m", "venv", str(venv_dir)])

    return python_in_venv


def build_package_spec(package: str, extras: list[str]) -> str:
    """Build a pip package specification with optional extras.

    Args:
        package: Base package name
        extras: List of extras to include

    Returns:
        Package spec like 'vector-inspector' or 'vector-inspector[chromadb,qdrant]'
    """
    if not extras:
        return package
    return f"{package}[{','.join(extras)}]"


def install_app(python_in_venv: Path, package_spec: str, upgrade: bool) -> None:
    """Install the app package into a venv.

    Args:
        python_in_venv: Path to Python in venv
        package_spec: Package specification (may include extras)
        upgrade: If True, upgrade existing installation
    """
    run_command([str(python_in_venv), "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    cmd = [str(python_in_venv), "-m", "pip", "install"]
    if upgrade:
        cmd.append("--upgrade")
    cmd.append(package_spec)
    run_command(cmd)
