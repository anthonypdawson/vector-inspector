"""Unit tests for bootstrap_installer.py pure logic functions.

These tests exercise only the deterministic, side-effect-free parts of the
installer.  Anything that touches subprocesses, the filesystem, or the
Windows registry is either mocked or tested at a light integration level
using tmp_path.
"""

import argparse
import json
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest

# Import from vi_installer package modules
from vi_installer import platform, python, venv, shortcuts, state, ui


# For compatibility with existing tests, create a simple namespace object
class MockBI:
    pass


bi = MockBI()

# Populate with module references
# Platform
bi.PLATFORM = platform.PLATFORM
bi.get_default_install_root = platform.get_default_install_root
bi._detect_shell_rc = platform.detect_shell_rc
bi.STATE_FILE_NAME = state.STATE_FILE_NAME
bi.APP_NAME = ui.APP_NAME
bi.APP_NAME_SLUG = ui.APP_NAME_SLUG

# Python
bi.parse_min_version = python.parse_min_version
bi.read_python_version = python.read_python_version
bi.discover_python_candidates = python.discover_python_candidates
bi.run_command = python.run_command

# Venv
bi.build_package_spec = venv.build_package_spec
bi.venv_python_path = venv.venv_python_path
bi.venv_app_entry_path = venv.venv_app_entry_path

# State
bi.write_state_file = state.write_state_file
bi.add_to_path_unix = state.add_to_path_unix
bi.write_launchers = state.write_launchers

# Shortcuts
bi.get_desktop_shortcut_path = shortcuts.get_desktop_shortcut_path
bi._get_desktop_shortcut_path = shortcuts.get_desktop_shortcut_path  # alias for old tests

# UI
bi.ensure_questionary = ui.ensure_questionary
bi.check_existing_install = ui.check_existing_install
bi.run_uninstall = ui.run_uninstall
bi.run_interactive_menu = ui.run_interactive_menu
bi.parse_args = ui.parse_args


# ---------------------------------------------------------------------------
# parse_min_version
# ---------------------------------------------------------------------------


def test_parse_min_version_valid():
    assert bi.parse_min_version("3.11") == (3, 11)
    assert bi.parse_min_version("3.12") == (3, 12)
    assert bi.parse_min_version(" 3.10 ") == (3, 10)


def test_parse_min_version_invalid_format():
    with pytest.raises(ValueError):
        bi.parse_min_version("3")

    with pytest.raises(ValueError):
        bi.parse_min_version("3.11.1")


def test_parse_min_version_non_numeric():
    with pytest.raises(ValueError):
        bi.parse_min_version("three.eleven")


# ---------------------------------------------------------------------------
# build_package_spec
# ---------------------------------------------------------------------------


def test_build_package_spec_no_extras():
    assert bi.build_package_spec("vector-inspector", []) == "vector-inspector"


def test_build_package_spec_single_extra():
    assert bi.build_package_spec("vector-inspector", ["chromadb"]) == "vector-inspector[chromadb]"


def test_build_package_spec_multiple_extras():
    result = bi.build_package_spec("vector-inspector", ["chromadb", "viz", "llm"])
    assert result == "vector-inspector[chromadb,viz,llm]"


# ---------------------------------------------------------------------------
# _detect_shell_rc
# ---------------------------------------------------------------------------


def test_detect_shell_rc_zsh():
    with patch.dict("os.environ", {"SHELL": "/bin/zsh"}):
        assert bi._detect_shell_rc() == "~/.zshrc"


def test_detect_shell_rc_fish():
    with patch.dict("os.environ", {"SHELL": "/usr/bin/fish"}):
        assert bi._detect_shell_rc() == "~/.config/fish/config.fish"


def test_detect_shell_rc_bash():
    with patch.dict("os.environ", {"SHELL": "/bin/bash"}):
        assert bi._detect_shell_rc() == "~/.bashrc"


def test_detect_shell_rc_unknown_falls_back_to_bash():
    with patch.dict("os.environ", {"SHELL": "/bin/sh"}):
        assert bi._detect_shell_rc() == "~/.bashrc"


# ---------------------------------------------------------------------------
# get_default_install_root
# ---------------------------------------------------------------------------


def test_get_default_install_root_darwin(tmp_path):
    with patch.object(platform, "PLATFORM", "darwin"), patch("pathlib.Path.home", return_value=tmp_path):
        root = bi.get_default_install_root()
    assert root == tmp_path / "Library" / "Application Support" / "VectorInspector"


def test_get_default_install_root_linux(tmp_path):
    with (
        patch.object(platform, "PLATFORM", "linux"),
        patch("pathlib.Path.home", return_value=tmp_path),
        patch.dict("os.environ", {}, clear=True),
    ):
        root = bi.get_default_install_root()
    assert root == tmp_path / ".local" / "share" / "vectorinspector"


def test_get_default_install_root_linux_respects_xdg(tmp_path):
    xdg = tmp_path / "custom_xdg"
    with (
        patch.object(platform, "PLATFORM", "linux"),
        patch.dict("os.environ", {"XDG_DATA_HOME": str(xdg)}),
    ):
        root = bi.get_default_install_root()
    assert root == xdg / "vectorinspector"


def test_get_default_install_root_windows(tmp_path):
    local_appdata = tmp_path / "LocalAppData"
    with (
        patch.object(platform, "PLATFORM", "win32"),
        patch.dict("os.environ", {"LOCALAPPDATA": str(local_appdata)}),
    ):
        root = bi.get_default_install_root()
    assert root == local_appdata / "VectorInspector"


# ---------------------------------------------------------------------------
# venv_python_path / venv_app_entry_path
# ---------------------------------------------------------------------------


def test_venv_python_path_unix(tmp_path):
    with patch.object(platform, "PLATFORM", "linux"):
        assert bi.venv_python_path(tmp_path) == tmp_path / "bin" / "python"


def test_venv_python_path_windows(tmp_path):
    with patch.object(venv, "PLATFORM", "win32"):
        assert bi.venv_python_path(tmp_path) == tmp_path / "Scripts" / "python.exe"


def test_venv_app_entry_path_unix(tmp_path):
    with patch.object(venv, "PLATFORM", "linux"):
        assert bi.venv_app_entry_path(tmp_path) == tmp_path / "bin" / "vector-inspector"


def test_venv_app_entry_path_windows(tmp_path):
    with patch.object(venv, "PLATFORM", "win32"):
        assert bi.venv_app_entry_path(tmp_path) == tmp_path / "Scripts" / "vector-inspector.exe"


# ---------------------------------------------------------------------------
# read_python_version
# ---------------------------------------------------------------------------


def test_read_python_version_success():
    fake_result = MagicMock()
    fake_result.stdout = "3.11\n"
    with patch.object(python, "run_command", return_value=fake_result):
        assert bi.read_python_version(["python3"]) == (3, 11)


def test_read_python_version_command_not_found():
    with patch.object(python, "run_command", side_effect=FileNotFoundError):
        assert bi.read_python_version(["no-such-python"]) is None


def test_read_python_version_subprocess_error():
    with patch.object(python, "run_command", side_effect=subprocess.CalledProcessError(1, "python")):
        assert bi.read_python_version(["python"]) is None


def test_read_python_version_unexpected_output():
    fake_result = MagicMock()
    fake_result.stdout = "not-a-version"
    with patch.object(python, "run_command", return_value=fake_result):
        assert bi.read_python_version(["python"]) is None


def test_read_python_version_empty_output():
    fake_result = MagicMock()
    fake_result.stdout = ""
    with patch.object(python, "run_command", return_value=fake_result):
        assert bi.read_python_version(["python"]) is None


# ---------------------------------------------------------------------------
# discover_python_candidates — deduplication
# ---------------------------------------------------------------------------


def test_discover_python_candidates_no_duplicates():
    with patch.object(platform, "PLATFORM", "linux"):
        candidates = bi.discover_python_candidates()
    seen: set[tuple[str, ...]] = set()
    for c in candidates:
        key = tuple(c)
        assert key not in seen, f"Duplicate candidate: {c}"
        seen.add(key)


def test_discover_python_candidates_includes_sys_executable():
    candidates = bi.discover_python_candidates()
    assert [sys.executable] in candidates


# ---------------------------------------------------------------------------
# write_state_file
# ---------------------------------------------------------------------------


def test_write_state_file_creates_valid_json(tmp_path):
    install_root = tmp_path / "vi"
    install_root.mkdir()

    with (
        patch.object(platform, "PLATFORM", "linux"),
        # Prevent the side-effect of writing to ~/.vector-inspector
        patch("pathlib.Path.home", return_value=tmp_path),
    ):
        bi.write_state_file(install_root, package_spec="vector-inspector[viz]", min_python_version=(3, 11))

    state_file = install_root / bi.STATE_FILE_NAME
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert data["app"] == bi.APP_NAME
    assert data["package_spec"] == "vector-inspector[viz]"
    assert data["min_python_version"] == "3.11"
    assert "venv" in data
    assert "launchers" in data


def test_write_state_file_writes_install_path_config(tmp_path):
    install_root = tmp_path / "vi"
    install_root.mkdir()

    with (
        patch.object(platform, "PLATFORM", "linux"),
        patch("pathlib.Path.home", return_value=tmp_path),
    ):
        bi.write_state_file(install_root, package_spec="vector-inspector", min_python_version=(3, 11))

    install_path_file = tmp_path / ".vector-inspector" / "install_path"
    assert install_path_file.exists()
    assert install_path_file.read_text().strip() == str(install_root)


# ---------------------------------------------------------------------------
# check_existing_install
# ---------------------------------------------------------------------------


def test_check_existing_install_no_config_file(tmp_path):
    with patch("pathlib.Path.home", return_value=tmp_path):
        path, mode = bi.check_existing_install()
    assert path is None
    assert mode is None


def test_check_existing_install_path_does_not_exist(tmp_path):
    config_dir = tmp_path / ".vector-inspector"
    config_dir.mkdir()
    (config_dir / "install_path").write_text(str(tmp_path / "nonexistent"), encoding="utf-8")

    with patch("pathlib.Path.home", return_value=tmp_path):
        path, mode = bi.check_existing_install()
    assert path is None
    assert mode is None


def test_check_existing_install_replace(tmp_path):
    install_root = tmp_path / "vi"
    install_root.mkdir()
    (install_root / "bootstrap-state.json").write_text(json.dumps({"app": "Vector Inspector"}), encoding="utf-8")
    config_dir = tmp_path / ".vector-inspector"
    config_dir.mkdir()
    (config_dir / "install_path").write_text(str(install_root), encoding="utf-8")

    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        patch.object(ui, "ensure_questionary", return_value=None),
        patch("builtins.input", return_value="1"),
        patch.object(sys, "argv", ["bootstrap_installer.py"]),
        patch("sys.stdin") as mock_stdin,
    ):
        mock_stdin.isatty.return_value = True
        _path, mode = bi.check_existing_install()

    assert mode == "replace"
    assert not install_root.exists()


def test_check_existing_install_update(tmp_path):
    install_root = tmp_path / "vi"
    install_root.mkdir()
    config_dir = tmp_path / ".vector-inspector"
    config_dir.mkdir()
    (config_dir / "install_path").write_text(str(install_root), encoding="utf-8")

    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        patch.object(ui, "ensure_questionary", return_value=None),
        patch("builtins.input", return_value="2"),
        patch.object(sys, "argv", ["bootstrap_installer.py"]),
        patch("sys.stdin") as mock_stdin,
    ):
        mock_stdin.isatty.return_value = True
        path, mode = bi.check_existing_install()

    assert mode == "update"
    assert path == install_root


def test_check_existing_install_uninstall(tmp_path):
    install_root = tmp_path / "vi"
    install_root.mkdir()
    config_dir = tmp_path / ".vector-inspector"
    config_dir.mkdir()
    (config_dir / "install_path").write_text(str(install_root), encoding="utf-8")

    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        patch.object(ui, "ensure_questionary", return_value=None),
        patch("builtins.input", return_value="3"),
        patch.object(sys, "argv", ["bootstrap_installer.py"]),
        patch("sys.stdin") as mock_stdin,
    ):
        mock_stdin.isatty.return_value = True
        path, mode = bi.check_existing_install()

    assert mode == "uninstall"
    assert path == install_root


def test_check_existing_install_cancel(tmp_path):
    install_root = tmp_path / "vi"
    install_root.mkdir()
    config_dir = tmp_path / ".vector-inspector"
    config_dir.mkdir()
    (config_dir / "install_path").write_text(str(install_root), encoding="utf-8")

    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        patch.object(ui, "ensure_questionary", return_value=None),
        patch("builtins.input", return_value="4"),
        patch.object(sys, "argv", ["bootstrap_installer.py"]),
        patch("sys.stdin") as mock_stdin,
        pytest.raises(SystemExit) as exc_info,
    ):
        mock_stdin.isatty.return_value = True
        bi.check_existing_install()

    assert exc_info.value.code == 0


def test_check_existing_install_strips_whitespace_in_path(tmp_path):
    install_root = tmp_path / "vi"
    config_dir = tmp_path / ".vector-inspector"
    config_dir.mkdir()
    # Write with trailing newline to simulate file written by write_state_file
    (config_dir / "install_path").write_text(str(install_root) + "\n", encoding="utf-8")

    with patch("pathlib.Path.home", return_value=tmp_path):
        path, mode = bi.check_existing_install()

    # install_root does not exist, so returns (None, None) — but no exception
    assert path is None
    assert mode is None


# ---------------------------------------------------------------------------
# run_uninstall
# ---------------------------------------------------------------------------


def test_run_uninstall_removes_install_root(tmp_path):
    install_root = tmp_path / "vi"
    install_root.mkdir()
    (install_root / "bootstrap-state.json").write_text(json.dumps({"app": "Vector Inspector"}), encoding="utf-8")
    config_dir = tmp_path / ".vector-inspector"
    config_dir.mkdir()
    install_path_file = config_dir / "install_path"
    install_path_file.write_text(str(install_root), encoding="utf-8")

    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        patch.object(ui, "ensure_questionary", return_value=None),
        patch.object(shortcuts, "get_desktop_shortcut_path", return_value=tmp_path / "nonexistent.shortcut"),
        patch("builtins.input", return_value="y"),
    ):
        rc = bi.run_uninstall(install_root)

    assert rc == 0
    assert not install_root.exists()
    assert not install_path_file.exists()


def test_run_uninstall_cancelled(tmp_path):
    install_root = tmp_path / "vi"
    install_root.mkdir()

    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        patch.object(ui, "ensure_questionary", return_value=None),
        patch.object(shortcuts, "get_desktop_shortcut_path", return_value=tmp_path / "nonexistent.shortcut"),
        patch("builtins.input", return_value="n"),
    ):
        rc = bi.run_uninstall(install_root)

    assert rc == 0
    assert install_root.exists()  # untouched


def test_run_uninstall_removes_desktop_shortcut(tmp_path):
    install_root = tmp_path / "vi"
    install_root.mkdir()
    (install_root / "bootstrap-state.json").write_text(json.dumps({"app": "Vector Inspector"}), encoding="utf-8")
    shortcut = tmp_path / "Vector Inspector.command"
    shortcut.write_text("#!/bin/sh\n", encoding="utf-8")
    config_dir = tmp_path / ".vector-inspector"
    config_dir.mkdir()
    (config_dir / "install_path").write_text(str(install_root), encoding="utf-8")

    with (
        patch("pathlib.Path.home", return_value=tmp_path),
        patch.object(ui, "ensure_questionary", return_value=None),
        patch.object(ui, "get_desktop_shortcut_path", return_value=shortcut),
        patch("builtins.input", return_value="y"),
    ):
        bi.run_uninstall(install_root)

    assert not shortcut.exists()


# ---------------------------------------------------------------------------
# --uninstall CLI flag
# ---------------------------------------------------------------------------


def test_parse_args_uninstall_flag():
    with patch("sys.argv", ["bootstrap_installer.py", "--uninstall"]):
        args = bi.parse_args()
    assert args.uninstall is True


# ---------------------------------------------------------------------------
# run_interactive_menu — lock_install_root
# ---------------------------------------------------------------------------


def test_run_interactive_menu_lock_install_root_does_not_change_path():
    """In Update mode, the install directory must not be changed by the menu."""
    args = argparse.Namespace(
        install_root="/original/path",
        extras="",
        add_to_path=True,
        create_shortcut=True,
        no_launch=False,
    )

    mock_q = MagicMock()
    # checkbox returns empty lists, confirm returns True
    mock_q.checkbox.return_value.ask.return_value = []
    mock_q.confirm.return_value.ask.return_value = True

    with (
        patch.object(ui, "ensure_questionary", return_value=mock_q),
        patch("sys.stdin.isatty", return_value=True),
        patch("sys.argv", ["bootstrap_installer.py"]),
    ):
        result = bi.run_interactive_menu(args, lock_install_root=True)

    assert result.install_root == "/original/path"
    mock_q.text.assert_not_called()


# ---------------------------------------------------------------------------
# add_to_path_unix
# ---------------------------------------------------------------------------


def test_add_to_path_unix_appends_export(tmp_path):
    rc_file = tmp_path / ".bashrc"
    rc_file.write_text("# existing\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"

    with patch.object(state, "detect_shell_rc", return_value=str(rc_file)):
        bi.add_to_path_unix(bin_dir)

    content = rc_file.read_text()
    assert str(bin_dir) in content
    assert "export PATH" in content


def test_add_to_path_unix_does_not_duplicate(tmp_path):
    bin_dir = tmp_path / "bin"
    rc_file = tmp_path / ".bashrc"
    rc_file.write_text(f'export PATH="{bin_dir}:$PATH"\n', encoding="utf-8")

    with patch.object(state, "detect_shell_rc", return_value=str(rc_file)):
        bi.add_to_path_unix(bin_dir)

    # Should still appear exactly once
    assert rc_file.read_text().count(str(bin_dir)) == 1


# ---------------------------------------------------------------------------
# write_launchers
# ---------------------------------------------------------------------------


def test_write_launchers_unix(tmp_path):
    install_root = tmp_path / "vi"
    with patch.object(platform, "PLATFORM", "linux"):
        launcher = bi.write_launchers(install_root)

    assert launcher.exists()
    assert launcher.name == bi.APP_NAME_SLUG
    content = launcher.read_text()
    assert "exec" in content
    assert bi.APP_NAME_SLUG in content


def test_write_launchers_windows(tmp_path):
    install_root = tmp_path / "vi"
    with patch.object(state, "PLATFORM", "win32"):
        launcher = bi.write_launchers(install_root)

    assert launcher.exists()
    assert launcher.suffix == ".cmd"
    content = launcher.read_text()
    assert bi.APP_NAME_SLUG in content
