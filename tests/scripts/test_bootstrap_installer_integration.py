"""Integration tests for bootstrap installer.

These tests exercise the full install flow end-to-end, including:
- Virtual environment creation
- Package installation
- Launcher creation
- Rollback on failure
- Dry-run mode
"""

import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def installer_script():
    """Path to the bootstrap installer script."""
    return Path(__file__).parent.parent.parent / "scripts" / "bootstrap_installer.py"


@pytest.fixture
def temp_install_root(tmp_path):
    """Provide a temp install location and clean up after."""
    install_root = tmp_path / "test-install"
    yield install_root
    if install_root.exists():
        shutil.rmtree(install_root)


def test_dry_run_mode(installer_script):
    """Test that dry-run mode shows what would happen without making changes."""
    result = subprocess.run(
        [
            "python",
            str(installer_script),
            "--dry-run",
            "--extras",
            "chromadb",
            "--no-launch",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "[DRY RUN]" in result.stdout
    assert "Would: Use Python" in result.stdout
    assert "Would: Create virtual environment" in result.stdout
    assert "Would: Install package" in result.stdout
    assert "No changes made" in result.stdout


def test_full_install_flow(installer_script, temp_install_root):
    """Test complete installation flow."""
    result = subprocess.run(
        [
            "python",
            str(installer_script),
            "--install-root",
            str(temp_install_root),
            "--package",
            "vector-inspector",
            "--no-add-to-path",
            "--no-shortcut",
            "--no-launch",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0
    assert "Installation complete" in result.stdout

    # Verify structure created
    assert temp_install_root.exists()
    assert (temp_install_root / "runtime" / "venv").exists()
    assert (temp_install_root / "bin").exists()
    assert (temp_install_root / "bootstrap-state.json").exists()

    # Verify launcher created and executable
    launcher = temp_install_root / "bin" / "vector-inspector"
    assert launcher.exists()
    assert launcher.stat().st_mode & 0o111  # executable bit set

    # Verify venv has vector-inspector installed
    venv_python = temp_install_root / "runtime" / "venv" / "bin" / "python"
    result = subprocess.run(
        [str(venv_python), "-c", "import vector_inspector"],
        capture_output=True,
    )
    assert result.returncode == 0


def test_install_with_extras(installer_script, temp_install_root):
    """Test installation with extras."""
    result = subprocess.run(
        [
            "python",
            str(installer_script),
            "--install-root",
            str(temp_install_root),
            "--package",
            "vector-inspector",
            "--extras",
            "viz",
            "--no-add-to-path",
            "--no-shortcut",
            "--no-launch",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0

    # Verify viz extra packages installed
    venv_python = temp_install_root / "runtime" / "venv" / "bin" / "python"
    result = subprocess.run(
        [str(venv_python), "-c", "import sklearn, umap"],
        capture_output=True,
    )
    assert result.returncode == 0


def test_rollback_on_failure(installer_script, temp_install_root):
    """Test that rollback cleans up when installation fails."""
    result = subprocess.run(
        [
            "python",
            str(installer_script),
            "--install-root",
            str(temp_install_root),
            "--package",
            "nonexistent-package-xyz-123",
            "--no-add-to-path",
            "--no-shortcut",
            "--no-launch",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode != 0
    assert "Installation failed" in result.stdout
    assert "Rolling back" in result.stdout

    # Verify venv was cleaned up
    venv_dir = temp_install_root / "runtime" / "venv"
    assert not venv_dir.exists() or not any(venv_dir.iterdir())


def test_launcher_works(installer_script, temp_install_root):
    """Test that the created launcher actually runs."""
    # Install first
    subprocess.run(
        [
            "python",
            str(installer_script),
            "--install-root",
            str(temp_install_root),
            "--package",
            "vector-inspector",
            "--no-add-to-path",
            "--no-shortcut",
            "--no-launch",
        ],
        capture_output=True,
        timeout=120,
        check=True,
    )

    # Test launcher
    launcher = temp_install_root / "bin" / "vector-inspector"
    result = subprocess.run(
        [str(launcher), "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    assert result.returncode == 0
    assert "vector-inspector" in result.stdout
