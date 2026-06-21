"""Vector Inspector Bootstrap Installer Package.

Cross-platform installer for creating app-local virtual environments
with live pip access for Vector Inspector's optional provider model.

Main entry point:
    from vi_installer.ui import run_installer
    sys.exit(run_installer())

Modules:
    platform  - Platform-specific paths and utilities
    python    - Python discovery and version management
    venv      - Virtual environment creation and package installation
    shortcuts - Desktop shortcut creation
    state     - Install state management
    ui        - User interface (TUI/CLI) and main orchestration
"""

__version__ = "1.0.0"

# Export main entry point
from vi_installer.ui import run_installer

# Export submodules for internal use
from vi_installer import platform, python, venv, shortcuts, state, ui

__all__ = ["run_installer", "platform", "python", "venv", "shortcuts", "state", "ui"]
