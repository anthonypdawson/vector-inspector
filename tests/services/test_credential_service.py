"""Tests for CredentialService."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# With keyring mocked as available
# ---------------------------------------------------------------------------


def _make_service_with_keyring():
    """Create a CredentialService instance with a mocked keyring module."""
    fake_keyring = MagicMock()
    fake_keyring.set_password = MagicMock()
    fake_keyring.get_password = MagicMock(return_value=None)
    fake_keyring.delete_password = MagicMock()

    # PasswordDeleteError stub
    class FakePasswordDeleteError(Exception):
        pass

    with (
        patch.dict("sys.modules", {"keyring": fake_keyring, "keyring.errors": MagicMock()}),
        patch("keyring.errors.PasswordDeleteError", FakePasswordDeleteError, create=True),
    ):
        import vector_inspector.services.credential_service as cs_mod

        # Force re-instantiation with keyring available
        svc = cs_mod.CredentialService.__new__(cs_mod.CredentialService)
        svc._use_keyring = True
        svc._keyring = fake_keyring
        svc._PasswordDeleteError = FakePasswordDeleteError
        svc._memory_store = {}

    return svc, fake_keyring, FakePasswordDeleteError


def test_store_credentials_with_keyring():
    """store_credentials uses keyring.set_password when keyring is available."""
    svc, fake_keyring, _ = _make_service_with_keyring()
    creds = {"api_key": "MY_KEY"}

    result = svc.store_credentials("profile-1", creds)

    assert result is True
    fake_keyring.set_password.assert_called_once_with("vector-inspector", "profile:profile-1", json.dumps(creds))


def test_store_credentials_exception_returns_false():
    """store_credentials returns False when set_password raises."""
    svc, fake_keyring, _ = _make_service_with_keyring()
    fake_keyring.set_password.side_effect = RuntimeError("keyring error")

    result = svc.store_credentials("profile-1", {"api_key": "x"})
    assert result is False


def test_get_credentials_with_keyring_returns_value():
    """get_credentials retrieves and parses value from keyring."""
    svc, fake_keyring, _ = _make_service_with_keyring()
    stored = {"api_key": "SECRET"}
    fake_keyring.get_password.return_value = json.dumps(stored)

    result = svc.get_credentials("profile-1")
    assert result == stored


def test_get_credentials_with_keyring_not_found_returns_none():
    """get_credentials returns None when keyring has nothing."""
    svc, fake_keyring, _ = _make_service_with_keyring()
    fake_keyring.get_password.return_value = None

    result = svc.get_credentials("profile-1")
    assert result is None


def test_get_credentials_exception_returns_none():
    """get_credentials returns None when get_password raises."""
    svc, fake_keyring, _ = _make_service_with_keyring()
    fake_keyring.get_password.side_effect = RuntimeError("err")

    result = svc.get_credentials("profile-1")
    assert result is None


def test_delete_credentials_with_keyring():
    """delete_credentials calls keyring.delete_password."""
    svc, fake_keyring, FakePDE = _make_service_with_keyring()

    result = svc.delete_credentials("profile-1")

    assert result is True
    fake_keyring.delete_password.assert_called_once()


def test_delete_credentials_with_password_delete_error_suppressed():
    """delete_credentials silently ignores PasswordDeleteError."""
    svc, fake_keyring, FakePDE = _make_service_with_keyring()
    fake_keyring.delete_password.side_effect = FakePDE("already gone")

    result = svc.delete_credentials("profile-1")
    assert result is True  # Error is suppressed


def test_delete_credentials_exception_returns_false():
    """delete_credentials returns False on unexpected exception."""
    svc, fake_keyring, _ = _make_service_with_keyring()
    fake_keyring.delete_password.side_effect = RuntimeError("unexpected")
    svc._PasswordDeleteError = None  # disable suppress

    result = svc.delete_credentials("profile-1")
    assert result is False


def test_is_keyring_available_true():
    """is_keyring_available returns True when keyring is set up."""
    svc, _, _ = _make_service_with_keyring()
    assert svc.is_keyring_available() is True


def test_clear_all_credentials_keyring_path(capsys):
    """clear_all_credentials logs a warning when using keyring backend."""
    svc, _, _ = _make_service_with_keyring()
    svc.clear_all_credentials()  # Should not raise


# ---------------------------------------------------------------------------
# Without keyring (memory fallback) - already tested in other tests but add
# explicit keyring-unavailable path
# ---------------------------------------------------------------------------


def test_service_without_keyring_uses_memory_store():
    """CredentialService falls back to in-memory when keyring is unavailable."""
    with patch.dict("sys.modules", {"keyring": None}):
        import importlib

        import vector_inspector.services.credential_service as cs_mod

        importlib.reload(cs_mod)
        svc = cs_mod.CredentialService()

    assert svc.is_keyring_available() is False

    creds = {"api_key": "no-keyring"}
    assert svc.store_credentials("p1", creds) is True
    assert svc.get_credentials("p1") == creds
    assert svc.delete_credentials("p1") is True
    assert svc.get_credentials("p1") is None
