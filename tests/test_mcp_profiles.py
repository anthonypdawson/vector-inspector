"""Unit tests for GUI-profile loading and credential fallback.

Covers GuiProfiles (profiles.json -> ConnectionConfig) and the
env-first / keychain-second credential resolution in
ConnectionConfig.resolve_credentials. Keyring is monkeypatched so
no test touches the real OS keychain.
"""

import json
import os

import pytest

from vector_inspector.mcp.config import ConnectionConfig
from vector_inspector.mcp.profiles import GuiProfiles, load_profiles


def _write_profiles(path, profiles):
    path.write_text(json.dumps({"profiles": profiles}), encoding="utf-8")


def _chroma_profile(name="local", path="./chroma"):
    return {
        "id": "id-chroma",
        "name": name,
        "provider": "chromadb",
        "config": {"type": "persistent", "path": path},
        "credential_fields": [],
    }


def _pine_profile(name="pine"):
    return {
        "id": "id-pine",
        "name": name,
        "provider": "pinecone",
        "config": {},
        "credential_fields": ["api_key"],
    }


# --- GuiProfiles.load ------------------------------------------------------


def test_load_profiles_happy_path(tmp_path):
    path = tmp_path / "profiles.json"
    _write_profiles(path, [_chroma_profile(), _pine_profile()])
    configs = load_profiles(path)
    assert set(configs) == {"local", "pine"}
    local = configs["local"]
    assert local.provider == "chromadb"
    assert local.params == {"type": "persistent", "path": "./chroma"}
    assert local.credential_fields == ()
    assert local.profile_id == "id-chroma"
    pine = configs["pine"]
    assert pine.secret_env == {"api_key": "PINECONE_API_KEY"}
    assert pine.credential_fields == ("api_key",)
    assert pine.profile_id == "id-pine"


def test_load_profiles_missing_file(tmp_path):
    assert load_profiles(tmp_path / "profiles.json") == {}


def test_load_profiles_malformed_json(tmp_path):
    path = tmp_path / "profiles.json"
    path.write_text("{not json", encoding="utf-8")
    assert load_profiles(path) == {}


def test_load_profiles_skips_unknown_provider_and_malformed(tmp_path):
    path = tmp_path / "profiles.json"
    _write_profiles(
        path,
        [
            _chroma_profile(),
            {"id": "x", "name": "bad", "provider": "nosuchdb", "config": {}, "credential_fields": []},
            {"id": "y", "name": "", "provider": "chromadb", "config": {}},
            {"id": "z", "name": "noconfig", "provider": "chromadb"},
        ],
    )
    assert set(load_profiles(path)) == {"local"}


def test_load_profiles_duplicate_name_keeps_first(tmp_path):
    path = tmp_path / "profiles.json"
    _write_profiles(path, [_chroma_profile(path="./one"), _chroma_profile(path="./two")])
    configs = load_profiles(path)
    assert configs["local"].params["path"] == "./one"


def test_load_profiles_mtime_caching(tmp_path):
    path = tmp_path / "profiles.json"
    _write_profiles(path, [_chroma_profile()])
    store = GuiProfiles(path)
    first = store.load()
    assert store.load() is first
    _write_profiles(path, [_chroma_profile(), _pine_profile()])
    # Force a newer mtime so the cache is invalidated.
    os.utime(path, (1_000_000_000, 2_000_000_000))
    assert set(store.load()) == {"local", "pine"}


# --- resolve_credentials: env first, keychain second ------------------------


def test_resolve_env_wins_over_keychain(monkeypatch):
    monkeypatch.setenv("PINECONE_API_KEY", "env-key")
    monkeypatch.setattr(
        "vector_inspector.mcp.config.read_keychain_credentials",
        lambda profile_id: {"api_key": "keychain-key"},
    )
    cfg = ConnectionConfig(
        name="pine",
        provider="pinecone",
        secret_env={"api_key": "PINECONE_API_KEY"},
        credential_fields=("api_key",),
        profile_id="id-pine",
    )
    assert cfg.resolve_credentials() == {"api_key": "env-key"}


def test_resolve_keychain_fallback(monkeypatch):
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.setattr(
        "vector_inspector.mcp.config.read_keychain_credentials",
        lambda profile_id: {"api_key": "keychain-key"},
    )
    cfg = ConnectionConfig(
        name="pine",
        provider="pinecone",
        secret_env={"api_key": "PINECONE_API_KEY"},
        credential_fields=("api_key",),
        profile_id="id-pine",
    )
    assert cfg.resolve_credentials() == {"api_key": "keychain-key"}


def test_resolve_keychain_only_field(monkeypatch):
    """A credential field with no standard env var resolves from the keychain alone."""
    monkeypatch.setattr(
        "vector_inspector.mcp.config.read_keychain_credentials",
        lambda profile_id: {"token": "tok-123"},
    )
    cfg = ConnectionConfig(
        name="m",
        provider="milvus",
        credential_fields=("token",),
        profile_id="id-m",
    )
    assert cfg.resolve_credentials() == {"token": "tok-123"}


def test_resolve_neither_source_raises(monkeypatch):
    monkeypatch.delenv("PINECONE_API_KEY", raising=False)
    monkeypatch.setattr("vector_inspector.mcp.config.read_keychain_credentials", lambda profile_id: None)
    cfg = ConnectionConfig(
        name="pine",
        provider="pinecone",
        secret_env={"api_key": "PINECONE_API_KEY"},
        credential_fields=("api_key",),
        profile_id="id-pine",
    )
    with pytest.raises(ValueError, match="PINECONE_API_KEY"):
        cfg.resolve_credentials()


def test_resolve_spec_config_unchanged(monkeypatch):
    """Launch-spec configs (no profile) still resolve from env only."""
    monkeypatch.setenv("MY_API_KEY", "secret-value")
    cfg = ConnectionConfig(
        name="q",
        provider="qdrant",
        params={"type": "http", "host": "h"},
        secret_env={"api_key": "MY_API_KEY"},
    )
    assert cfg.resolve_credentials() == {"api_key": "secret-value"}
