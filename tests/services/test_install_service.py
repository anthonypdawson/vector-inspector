"""Tests for install_service."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from vector_inspector.services.install_service import (
    _PACKAGE_SPECS,
    _PACKAGES,
    _VALID_FEATURE_IDS,
    _VALID_IDS,
    _VALID_PROVIDER_IDS,
    get_install_command,
    get_uninstall_command,
    install,
    uninstall,
)

_TELEMETRY_PATH = "vector_inspector.services.install_service.TelemetryService.send_event"


def _make_fake_process(returncode: int, lines: list[str]):
    """Return a mock Popen that simulates pip output."""
    fake = MagicMock()
    fake.stdout.__iter__ = MagicMock(return_value=iter(lines))
    fake.returncode = returncode
    fake.wait = MagicMock()
    return fake


# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------


def test_valid_provider_ids_non_empty():
    assert len(_VALID_PROVIDER_IDS) > 0


def test_valid_feature_ids_non_empty():
    assert len(_VALID_FEATURE_IDS) > 0


def test_valid_ids_is_union():
    assert _VALID_IDS == _VALID_PROVIDER_IDS | _VALID_FEATURE_IDS


def test_provider_and_feature_ids_are_disjoint():
    assert _VALID_PROVIDER_IDS.isdisjoint(_VALID_FEATURE_IDS)


@pytest.mark.parametrize("item_id", ["viz", "embeddings", "clip", "documents"])
def test_valid_feature_ids_contain_expected(item_id):
    assert item_id in _VALID_FEATURE_IDS


@pytest.mark.parametrize("item_id", list(_VALID_IDS))
def test_package_specs_defined_for_all_ids(item_id):
    assert item_id in _PACKAGE_SPECS
    assert len(_PACKAGE_SPECS[item_id]) > 0


@pytest.mark.parametrize("item_id", list(_VALID_IDS))
def test_package_specs_contain_version_specifiers(item_id):
    for spec in _PACKAGE_SPECS[item_id]:
        assert ">=" in spec or "==" in spec, f"No version specifier in {spec!r}"


@pytest.mark.parametrize("item_id", list(_VALID_IDS))
def test_packages_derived_from_specs(item_id):
    spec_names = {s.split(">")[0].split("=")[0].split("<")[0].split("!")[0] for s in _PACKAGE_SPECS[item_id]}
    assert set(_PACKAGES[item_id]) == spec_names


# ---------------------------------------------------------------------------
# get_install_command
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("item_id", list(_VALID_IDS))
def test_get_install_command_all_known_ids(item_id):
    cmd = get_install_command(item_id)
    assert cmd[0] == sys.executable
    assert cmd[1:3] == ["-m", "pip"]
    assert f"vector-inspector[{item_id}]" in cmd[-1]


def test_get_install_command_unknown_raises():
    with pytest.raises(ValueError, match="Unknown provider or feature"):
        get_install_command("evil; rm -rf /")


def test_get_install_command_empty_string_raises():
    with pytest.raises(ValueError, match="Unknown provider or feature"):
        get_install_command("")


# ---------------------------------------------------------------------------
# get_uninstall_command
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("item_id", list(_VALID_IDS))
def test_get_uninstall_command_all_known_ids(item_id):
    cmd = get_uninstall_command(item_id)
    assert cmd[0] == sys.executable
    assert cmd[1:4] == ["-m", "pip", "uninstall"]
    assert "-y" in cmd
    for pkg in _PACKAGES[item_id]:
        assert pkg in cmd


def test_get_uninstall_command_unknown_raises():
    with pytest.raises(ValueError, match="Unknown provider or feature"):
        get_uninstall_command("not_a_thing")


def test_get_uninstall_command_empty_string_raises():
    with pytest.raises(ValueError, match="Unknown provider or feature"):
        get_uninstall_command("")


# ---------------------------------------------------------------------------
# install
# ---------------------------------------------------------------------------


def test_install_success():
    fake_proc = _make_fake_process(0, ["Successfully installed chromadb\n"])
    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
        with patch(_TELEMETRY_PATH):
            returncode, output = install("chromadb")
    assert returncode == 0
    assert "Successfully installed" in output
    cmd_used = mock_popen.call_args[0][0]
    assert cmd_used[0] == sys.executable
    assert "vector-inspector[chromadb]" in cmd_used[-1]


def test_install_feature_success():
    fake_proc = _make_fake_process(0, ["Successfully installed scikit-learn\n"])
    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
        with patch(_TELEMETRY_PATH):
            returncode, output = install("viz")
    assert returncode == 0
    cmd_used = mock_popen.call_args[0][0]
    assert "vector-inspector[viz]" in cmd_used[-1]


def test_install_failure():
    fake_proc = _make_fake_process(1, ["ERROR: some error\n"])
    with patch("subprocess.Popen", return_value=fake_proc):
        with patch(_TELEMETRY_PATH):
            returncode, output = install("qdrant")
    assert returncode == 1
    assert "ERROR" in output


def test_install_calls_on_output_callback():
    lines = ["line1\n", "line2\n"]
    fake_proc = _make_fake_process(0, lines)
    received: list[str] = []
    with patch("subprocess.Popen", return_value=fake_proc):
        with patch(_TELEMETRY_PATH):
            install("chromadb", on_output=received.append)
    assert received == lines


def test_install_unknown_raises():
    with pytest.raises(ValueError, match="Unknown provider or feature"):
        install("not_a_thing")


def test_install_popen_exception_returns_minus_one():
    with patch("subprocess.Popen", side_effect=OSError("not found")):
        returncode, output = install("chromadb")
    assert returncode == -1
    assert "Failed to launch pip" in output


def test_install_popen_exception_calls_on_output():
    collected: list[str] = []
    with patch("subprocess.Popen", side_effect=OSError("boom")):
        install("chromadb", on_output=collected.append)
    assert any("Failed to launch pip" in s for s in collected)


# ---------------------------------------------------------------------------
# uninstall
# ---------------------------------------------------------------------------


def test_uninstall_success():
    fake_proc = _make_fake_process(0, ["Successfully uninstalled chromadb\n"])
    with patch("subprocess.Popen", return_value=fake_proc) as mock_popen:
        with patch(_TELEMETRY_PATH):
            returncode, output = uninstall("chromadb")
    assert returncode == 0
    assert "Successfully uninstalled" in output
    cmd_used = mock_popen.call_args[0][0]
    assert cmd_used[0] == sys.executable
    assert "-y" in cmd_used


def test_uninstall_feature_success():
    fake_proc = _make_fake_process(0, ["Successfully uninstalled scikit-learn\n"])
    with patch("subprocess.Popen", return_value=fake_proc):
        with patch(_TELEMETRY_PATH):
            returncode, output = uninstall("viz")
    assert returncode == 0


def test_uninstall_failure():
    fake_proc = _make_fake_process(1, ["WARNING: Skipping chromadb\n"])
    with patch("subprocess.Popen", return_value=fake_proc):
        with patch(_TELEMETRY_PATH):
            returncode, _ = uninstall("chromadb")
    assert returncode == 1


def test_uninstall_calls_on_output_callback():
    lines = ["Uninstalling chromadb\n", "done\n"]
    fake_proc = _make_fake_process(0, lines)
    received: list[str] = []
    with patch("subprocess.Popen", return_value=fake_proc):
        with patch(_TELEMETRY_PATH):
            uninstall("chromadb", on_output=received.append)
    assert received == lines


def test_uninstall_unknown_raises():
    with pytest.raises(ValueError, match="Unknown provider or feature"):
        uninstall("not_a_thing")


def test_uninstall_popen_exception_returns_minus_one():
    with patch("subprocess.Popen", side_effect=OSError("gone")):
        returncode, output = uninstall("chromadb")
    assert returncode == -1
    assert "Failed to launch pip" in output


def test_uninstall_popen_exception_calls_on_output():
    collected: list[str] = []
    with patch("subprocess.Popen", side_effect=OSError("boom")):
        uninstall("chromadb", on_output=collected.append)
    assert any("Failed to launch pip" in s for s in collected)


# ---------------------------------------------------------------------------
# Telemetry — install
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider_id", list(_VALID_PROVIDER_IDS))
def test_install_provider_fires_telemetry_on_success(provider_id):
    fake_proc = _make_fake_process(0, [])
    with patch("subprocess.Popen", return_value=fake_proc):
        with patch(_TELEMETRY_PATH) as mock_send:
            install(provider_id)
    mock_send.assert_called_once_with(
        "provider.installed",
        {"metadata": {"provider_id": provider_id, "success": True}},
    )


@pytest.mark.parametrize("feature_id", list(_VALID_FEATURE_IDS))
def test_install_feature_fires_telemetry_on_success(feature_id):
    fake_proc = _make_fake_process(0, [])
    with patch("subprocess.Popen", return_value=fake_proc):
        with patch(_TELEMETRY_PATH) as mock_send:
            install(feature_id)
    mock_send.assert_called_once_with(
        "feature.installed",
        {"metadata": {"feature_id": feature_id, "success": True}},
    )


def test_install_fires_telemetry_on_pip_failure():
    fake_proc = _make_fake_process(1, ["ERROR\n"])
    with patch("subprocess.Popen", return_value=fake_proc):
        with patch(_TELEMETRY_PATH) as mock_send:
            install("chromadb")
    mock_send.assert_called_once_with(
        "provider.installed",
        {"metadata": {"provider_id": "chromadb", "success": False}},
    )


def test_install_no_telemetry_on_oserror():
    with patch("subprocess.Popen", side_effect=OSError("gone")):
        with patch(_TELEMETRY_PATH) as mock_send:
            install("chromadb")
    mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# Telemetry — uninstall
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("provider_id", list(_VALID_PROVIDER_IDS))
def test_uninstall_provider_fires_telemetry_on_success(provider_id):
    fake_proc = _make_fake_process(0, [])
    with patch("subprocess.Popen", return_value=fake_proc):
        with patch(_TELEMETRY_PATH) as mock_send:
            uninstall(provider_id)
    mock_send.assert_called_once_with(
        "provider.uninstalled",
        {"metadata": {"provider_id": provider_id, "success": True}},
    )


@pytest.mark.parametrize("feature_id", list(_VALID_FEATURE_IDS))
def test_uninstall_feature_fires_telemetry_on_success(feature_id):
    fake_proc = _make_fake_process(0, [])
    with patch("subprocess.Popen", return_value=fake_proc):
        with patch(_TELEMETRY_PATH) as mock_send:
            uninstall(feature_id)
    mock_send.assert_called_once_with(
        "feature.uninstalled",
        {"metadata": {"feature_id": feature_id, "success": True}},
    )


def test_uninstall_fires_telemetry_on_pip_failure():
    fake_proc = _make_fake_process(1, ["WARNING\n"])
    with patch("subprocess.Popen", return_value=fake_proc):
        with patch(_TELEMETRY_PATH) as mock_send:
            uninstall("chromadb")
    mock_send.assert_called_once_with(
        "provider.uninstalled",
        {"metadata": {"provider_id": "chromadb", "success": False}},
    )


def test_uninstall_no_telemetry_on_oserror():
    with patch("subprocess.Popen", side_effect=OSError("gone")):
        with patch(_TELEMETRY_PATH) as mock_send:
            uninstall("chromadb")
    mock_send.assert_not_called()
