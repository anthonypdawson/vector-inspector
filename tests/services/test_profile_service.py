"""Tests for ProfileService and ConnectionProfile."""

from unittest.mock import patch

import pytest

from vector_inspector.services.profile_service import ConnectionProfile, ProfileService

# ---------------------------------------------------------------------------
# Fixture: isolated ProfileService using a tmp_path
# ---------------------------------------------------------------------------


@pytest.fixture
def svc(tmp_path, qapp):
    """Return a fresh ProfileService whose storage is redirected to tmp_path."""
    service = ProfileService()
    service.profiles_dir = tmp_path / "profiles"
    service.profiles_file = service.profiles_dir / "profiles.json"
    service._profiles = {}
    service._last_active_connections = []
    return service


# ---------------------------------------------------------------------------
# ConnectionProfile
# ---------------------------------------------------------------------------


def test_connection_profile_to_dict():
    p = ConnectionProfile("id1", "My DB", "chromadb", {"host": "localhost"}, ["api_key"])
    d = p.to_dict()
    assert d["id"] == "id1"
    assert d["name"] == "My DB"
    assert d["provider"] == "chromadb"
    assert d["config"] == {"host": "localhost"}
    assert d["credential_fields"] == ["api_key"]


def test_connection_profile_from_dict():
    data = {
        "id": "abc",
        "name": "Test",
        "provider": "qdrant",
        "config": {"port": 6333},
        "credential_fields": ["key"],
    }
    p = ConnectionProfile.from_dict(data)
    assert p.id == "abc"
    assert p.name == "Test"
    assert p.provider == "qdrant"
    assert p.config == {"port": 6333}
    assert p.credential_fields == ["key"]


def test_connection_profile_from_dict_defaults():
    """from_dict handles missing optional fields."""
    data = {"id": "x", "name": "X", "provider": "chroma"}
    p = ConnectionProfile.from_dict(data)
    assert p.config == {}
    assert p.credential_fields == []


# ---------------------------------------------------------------------------
# ProfileService._load_profiles / _save_profiles
# ---------------------------------------------------------------------------


def test_load_profiles_when_no_file(svc):
    """_load_profiles with nonexistent file → empty _profiles."""
    svc._load_profiles()
    assert svc._profiles == {}


def test_save_and_reload_profiles(svc):
    """_save_profiles writes a JSON file, _load_profiles reads it back."""
    pid = svc.create_profile("DB1", "chromadb", {"host": "localhost"})
    svc._load_profiles()
    assert pid in svc._profiles


def test_save_profiles_creates_directory(svc, tmp_path):
    """_save_profiles creates the directory if it doesn't exist."""
    svc.profiles_dir = tmp_path / "new_dir" / "deep"
    svc.profiles_file = svc.profiles_dir / "profiles.json"
    svc.create_profile("X", "qdrant", {})
    assert svc.profiles_file.exists()


def test_load_profiles_corrupted_file(svc):
    """Corrupted JSON file → _load_profiles resets to empty state."""
    svc.profiles_dir.mkdir(parents=True)
    svc.profiles_file.write_text("not-json")
    svc._load_profiles()
    assert svc._profiles == {}


# ---------------------------------------------------------------------------
# create_profile
# ---------------------------------------------------------------------------


def test_create_profile_returns_id(svc):
    pid = svc.create_profile("My DB", "chromadb", {"host": "localhost"})
    assert isinstance(pid, str)
    assert len(pid) > 0


def test_create_profile_stores_profile(svc):
    pid = svc.create_profile("DB", "qdrant", {"port": 6333})
    assert pid in svc._profiles
    p = svc._profiles[pid]
    assert p.name == "DB"
    assert p.provider == "qdrant"


def test_create_profile_emits_signal(svc, qapp):
    received = []
    svc.profile_added.connect(lambda pid: received.append(pid))
    pid = svc.create_profile("DB", "chromadb", {})
    assert pid in received


def test_create_profile_with_credentials_stores_them(svc):
    creds = {"api_key": "secret"}
    with patch.object(svc.credential_service, "store_credentials") as mock_store:
        pid = svc.create_profile("DB", "pinecone", {}, credentials=creds)
    mock_store.assert_called_once_with(pid, creds)
    assert svc._profiles[pid].credential_fields == ["api_key"]


# ---------------------------------------------------------------------------
# get_profile / get_all_profiles
# ---------------------------------------------------------------------------


def test_get_profile_returns_profile(svc):
    pid = svc.create_profile("DB", "chromadb", {})
    p = svc.get_profile(pid)
    assert p is not None
    assert p.id == pid


def test_get_profile_unknown_returns_none(svc):
    assert svc.get_profile("nonexistent") is None


def test_get_all_profiles_empty(svc):
    assert svc.get_all_profiles() == []


def test_get_all_profiles_returns_all(svc):
    svc.create_profile("A", "chromadb", {})
    svc.create_profile("B", "qdrant", {})
    profiles = svc.get_all_profiles()
    assert len(profiles) == 2


# ---------------------------------------------------------------------------
# update_profile
# ---------------------------------------------------------------------------


def test_update_profile_name(svc):
    pid = svc.create_profile("Old", "chromadb", {})
    ok = svc.update_profile(pid, name="New")
    assert ok is True
    assert svc._profiles[pid].name == "New"


def test_update_profile_config(svc):
    pid = svc.create_profile("DB", "chromadb", {"host": "old"})
    ok = svc.update_profile(pid, config={"host": "new"})
    assert ok is True
    assert svc._profiles[pid].config == {"host": "new"}


def test_update_profile_credentials(svc):
    pid = svc.create_profile("DB", "chromadb", {})
    creds = {"api_key": "new_key"}
    with patch.object(svc.credential_service, "store_credentials") as mock_store:
        ok = svc.update_profile(pid, credentials=creds)
    assert ok is True
    mock_store.assert_called_once_with(pid, creds)


def test_update_profile_emits_signal(svc, qapp):
    pid = svc.create_profile("DB", "chromadb", {})
    received = []
    svc.profile_updated.connect(lambda pid: received.append(pid))
    svc.update_profile(pid, name="New")
    assert pid in received


def test_update_profile_not_found_returns_false(svc):
    assert svc.update_profile("nonexistent", name="X") is False


# ---------------------------------------------------------------------------
# delete_profile
# ---------------------------------------------------------------------------


def test_delete_profile_removes_it(svc):
    pid = svc.create_profile("DB", "chromadb", {})
    ok = svc.delete_profile(pid)
    assert ok is True
    assert pid not in svc._profiles


def test_delete_profile_emits_signal(svc, qapp):
    pid = svc.create_profile("DB", "chromadb", {})
    received = []
    svc.profile_deleted.connect(lambda pid: received.append(pid))
    svc.delete_profile(pid)
    assert pid in received


def test_delete_profile_removes_from_last_active(svc):
    pid = svc.create_profile("DB", "chromadb", {})
    svc._last_active_connections = [pid]
    svc.delete_profile(pid)
    assert pid not in svc._last_active_connections


def test_delete_profile_not_found_returns_false(svc):
    assert svc.delete_profile("nonexistent") is False


# ---------------------------------------------------------------------------
# duplicate_profile
# ---------------------------------------------------------------------------


def test_duplicate_profile(svc):
    pid = svc.create_profile("DB", "chromadb", {"host": "localhost"})
    with patch.object(svc.credential_service, "get_credentials", return_value=None):
        new_pid = svc.duplicate_profile(pid, "Copy of DB")
    assert new_pid is not None
    assert new_pid != pid
    assert svc._profiles[new_pid].name == "Copy of DB"
    assert svc._profiles[new_pid].config == {"host": "localhost"}


def test_duplicate_profile_not_found_returns_none(svc):
    assert svc.duplicate_profile("nonexistent", "Copy") is None


# ---------------------------------------------------------------------------
# get_profile_with_credentials
# ---------------------------------------------------------------------------


def test_get_profile_with_credentials(svc):
    pid = svc.create_profile("DB", "chromadb", {"host": "localhost"})
    with patch.object(svc.credential_service, "get_credentials", return_value={"key": "val"}):
        result = svc.get_profile_with_credentials(pid)
    assert result is not None
    assert result["id"] == pid
    assert result["credentials"] == {"key": "val"}


def test_get_profile_with_credentials_not_found(svc):
    assert svc.get_profile_with_credentials("nonexistent") is None


# ---------------------------------------------------------------------------
# export_profiles / import_profiles
# ---------------------------------------------------------------------------


def test_export_profiles_no_credentials(svc):
    svc.create_profile("DB", "chromadb", {"host": "localhost"})
    exported = svc.export_profiles()
    assert len(exported) == 1
    assert "credentials" not in exported[0]


def test_export_profiles_with_credentials(svc):
    pid = svc.create_profile("DB", "chromadb", {})
    with patch.object(svc.credential_service, "get_credentials", return_value={"key": "v"}):
        exported = svc.export_profiles(include_credentials=True)
    assert exported[0]["credentials"] == {"key": "v"}


def test_import_profiles_creates_profiles(svc):
    profiles_data = [
        {
            "id": "old-id",
            "name": "Imported DB",
            "provider": "chromadb",
            "config": {"host": "h"},
            "credential_fields": [],
        }
    ]
    mapping = svc.import_profiles(profiles_data)
    assert "old-id" in mapping
    new_id = mapping["old-id"]
    assert new_id in svc._profiles
    assert svc._profiles[new_id].name == "Imported DB"


def test_import_profiles_overwrite(svc):
    """With overwrite=True and non-existing ID, the original ID is preserved."""
    profiles_data = [
        {
            "id": "original-id",
            "name": "Imported",
            "provider": "chromadb",
            "config": {},
            "credential_fields": [],
        }
    ]
    mapping = svc.import_profiles(profiles_data, overwrite=True)
    assert mapping["original-id"] == "original-id"
    assert svc._profiles["original-id"].name == "Imported"


def test_import_profiles_with_credentials(svc):
    profiles_data = [
        {
            "id": "old",
            "name": "DB",
            "provider": "chromadb",
            "config": {},
            "credential_fields": ["api_key"],
            "credentials": {"api_key": "secret"},
        }
    ]
    with patch.object(svc.credential_service, "store_credentials") as mock_store:
        mapping = svc.import_profiles(profiles_data)
    new_id = mapping["old"]
    mock_store.assert_called_once_with(new_id, {"api_key": "secret"})


# ---------------------------------------------------------------------------
# save_last_active_connections / get_last_active_connections
# ---------------------------------------------------------------------------


def test_save_and_get_last_active_connections(svc):
    pid1 = svc.create_profile("A", "chromadb", {})
    pid2 = svc.create_profile("B", "qdrant", {})
    svc.save_last_active_connections([pid1, pid2])
    result = svc.get_last_active_connections()
    assert result == [pid1, pid2]


# ---------------------------------------------------------------------------
# migrate_legacy_connection
# ---------------------------------------------------------------------------


def test_migrate_legacy_persistent(svc):
    config = {"provider": "chromadb", "type": "persistent", "path": "/tmp/db"}
    pid = svc.migrate_legacy_connection(config)
    assert pid in svc._profiles
    assert "Persistent" in svc._profiles[pid].name


def test_migrate_legacy_http(svc):
    config = {"provider": "qdrant", "type": "http", "host": "my-server"}
    pid = svc.migrate_legacy_connection(config)
    assert "my-server" in svc._profiles[pid].name


def test_migrate_legacy_ephemeral(svc):
    config = {"provider": "chromadb", "type": "ephemeral"}
    pid = svc.migrate_legacy_connection(config)
    assert "Ephemeral" in svc._profiles[pid].name


def test_migrate_legacy_with_api_key(svc):
    config = {"provider": "pinecone", "type": "http", "host": "pinecone", "api_key": "secret"}
    with patch.object(svc.credential_service, "store_credentials") as mock_store:
        pid = svc.migrate_legacy_connection(config)
    mock_store.assert_called_once()
    # api_key should be removed from config
    assert "api_key" not in svc._profiles[pid].config
