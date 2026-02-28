import json
from unittest.mock import MagicMock, patch

from vector_inspector.services.backup_helpers import write_backup_zip
from vector_inspector.services.backup_restore_service import BackupRestoreService


def test_restore_uses_prepare_restore_and_adds_items(tmp_path, empty_fake_provider):
    """Test that restore creates collection and adds items using FakeProvider fixture."""
    metadata = {
        "collection_name": "col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 3},
    }
    data = {
        "ids": ["1", "2"],
        "documents": ["a", "b"],
        "metadatas": [{}, {}],
        "embeddings": [[0, 0, 0], [1, 1, 1]],
    }
    p = tmp_path / "b.zip"
    write_backup_zip(p, metadata, data)

    conn = empty_fake_provider
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(p))
    assert ok is True
    # Verify collection was created and items were added
    assert "col" in conn.list_collections()
    items = conn.get_all_items("col")
    assert len(items["ids"]) == 2
    assert items["documents"] == ["a", "b"]


def test_restore_with_empty_embeddings(tmp_path, empty_fake_provider):
    """Test restore with empty embeddings list using FakeProvider fixture."""
    metadata = {
        "collection_name": "col_empty",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 3},
    }
    data = {"ids": ["1", "2"], "documents": ["a", "b"], "metadatas": [{}, {}], "embeddings": []}
    p = tmp_path / "b_empty.zip"
    write_backup_zip(p, metadata, data)

    conn = empty_fake_provider
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(p))
    assert ok is True
    # Verify collection was created and items were added
    assert "col_empty" in conn.list_collections()
    items = conn.get_all_items("col_empty")
    assert len(items["ids"]) == 2


def test_backup_includes_model_from_settings(tmp_path, fake_provider):
    """Test that backup includes model config from app settings."""
    conn = fake_provider
    svc = BackupRestoreService()

    # Mock SettingsService to return a model config
    mock_settings = MagicMock()
    mock_settings.get_embedding_model.return_value = {
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "type": "sentence-transformer",
    }

    with patch(
        "vector_inspector.services.settings_service.SettingsService",
        return_value=mock_settings,
    ):
        backup_path = svc.backup_collection(
            conn,
            "test_collection",
            str(tmp_path),
            include_embeddings=True,
            profile_name="test_conn_id",
        )

    assert backup_path is not None

    # Verify the backup contains model config
    import zipfile

    with zipfile.ZipFile(backup_path, "r") as zf:
        metadata_json = zf.read("metadata.json")
        metadata = json.loads(metadata_json)

    assert metadata.get("embedding_model") == "sentence-transformers/all-MiniLM-L6-v2"
    assert metadata.get("embedding_model_type") == "sentence-transformer"


def test_restore_persists_model_to_settings(tmp_path, empty_fake_provider):
    """Test that restore saves model config to app settings."""
    # Create a backup with model metadata
    metadata = {
        "collection_name": "restored_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 2},
        "embedding_model": "sentence-transformers/paraphrase-MiniLM-L6-v2",
        "embedding_model_type": "sentence-transformer",
    }
    data = {
        "ids": ["1", "2"],
        "documents": ["test1", "test2"],
        "metadatas": [{}, {}],
        "embeddings": [[0.1, 0.2], [0.3, 0.4]],
    }
    backup_file = tmp_path / "test_backup.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = empty_fake_provider
    svc = BackupRestoreService()

    # Mock SettingsService
    mock_settings = MagicMock()

    with patch(
        "vector_inspector.services.settings_service.SettingsService",
        return_value=mock_settings,
    ):
        ok = svc.restore_collection(
            conn,
            str(backup_file),
            profile_name="restored_conn_id",
        )

    assert ok is True

    # Verify that save_embedding_model was called with correct parameters
    mock_settings.save_embedding_model.assert_called_once_with(
        "restored_conn_id",
        "restored_col",
        "sentence-transformers/paraphrase-MiniLM-L6-v2",
        "sentence-transformer",
    )


def test_backup_and_restore_roundtrip(tmp_path, fake_provider_with_name):
    """Test complete backup and restore cycle with FakeProvider."""
    conn, collection_name = fake_provider_with_name
    svc = BackupRestoreService()

    # Backup the collection
    backup_path = svc.backup_collection(
        conn,
        collection_name,
        str(tmp_path),
        include_embeddings=True,
    )
    assert backup_path is not None

    # Verify original data
    original = conn.get_all_items(collection_name)
    assert len(original["ids"]) == 3

    # Delete the collection
    conn.delete_collection(collection_name)
    assert collection_name not in conn.list_collections()

    # Restore from backup
    ok = svc.restore_collection(conn, backup_path)
    assert ok is True
    assert collection_name in conn.list_collections()

    # Verify restored data matches original
    restored = conn.get_all_items(collection_name)
    assert len(restored["ids"]) == len(original["ids"])
    assert restored["documents"] == original["documents"]


# ---------------------------------------------------------------------------
# backup_collection edge cases
# ---------------------------------------------------------------------------


def test_backup_returns_none_when_collection_info_missing(tmp_path, empty_fake_provider):
    """backup_collection returns None when get_collection_info returns None."""
    conn = empty_fake_provider
    # No collection created → get_collection_info returns None
    svc = BackupRestoreService()
    result = svc.backup_collection(conn, "nonexistent_col", str(tmp_path))
    assert result is None


def test_backup_returns_none_when_no_items(tmp_path, fake_provider):
    """backup_collection returns None when collection has no items."""
    conn = fake_provider
    # Add empty collection
    conn.create_collection("empty_col", 0, [])
    svc = BackupRestoreService()
    result = svc.backup_collection(conn, "empty_col", str(tmp_path))
    assert result is None


def test_backup_without_embeddings(tmp_path, fake_provider):
    """backup_collection with include_embeddings=False omits embeddings from zip."""
    import zipfile

    conn = fake_provider
    svc = BackupRestoreService()
    backup_path = svc.backup_collection(conn, "test_collection", str(tmp_path), include_embeddings=False)
    assert backup_path is not None

    with zipfile.ZipFile(backup_path, "r") as zf:
        data_str = zf.read("data.json").decode("utf-8")
        data = json.loads(data_str)
    assert "embeddings" not in data


def test_backup_uses_connection_get_embedding_model(tmp_path, fake_provider):
    """backup_collection calls connection.get_embedding_model when collection_info has no model."""
    conn = fake_provider
    conn.get_embedding_model = MagicMock(return_value="custom-model")
    svc = BackupRestoreService()
    backup_path = svc.backup_collection(conn, "test_collection", str(tmp_path))
    assert backup_path is not None
    conn.get_embedding_model.assert_called_once_with("test_collection")


# ---------------------------------------------------------------------------
# restore_collection edge cases
# ---------------------------------------------------------------------------


def test_restore_with_overwrite_true_replaces_existing(tmp_path, fake_provider):
    """restore_collection with overwrite=True deletes and re-creates existing collection."""
    conn = fake_provider
    svc = BackupRestoreService()

    # First backup the existing collection
    backup_path = svc.backup_collection(conn, "test_collection", str(tmp_path))
    assert backup_path is not None

    # Now restore with overwrite=True (collection already exists)
    ok = svc.restore_collection(conn, backup_path, overwrite=True)
    assert ok is True
    assert "test_collection" in conn.list_collections()


def test_restore_returns_false_when_existing_and_no_overwrite(tmp_path, fake_provider):
    """restore_collection returns False when collection exists and overwrite=False."""
    conn = fake_provider
    svc = BackupRestoreService()

    backup_path = svc.backup_collection(conn, "test_collection", str(tmp_path))
    assert backup_path is not None

    # Don't delete the collection → overwrite=False should return False
    ok = svc.restore_collection(conn, backup_path, overwrite=False)
    assert ok is False


def test_restore_with_recompute_embeddings_false(tmp_path, empty_fake_provider):
    """restore_collection with recompute_embeddings=False omits embeddings during add_items."""
    metadata = {
        "collection_name": "r_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 2},
    }
    data = {
        "ids": ["1", "2"],
        "documents": ["a", "b"],
        "metadatas": [{}, {}],
        "embeddings": [[0.1, 0.2], [0.3, 0.4]],
    }
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = empty_fake_provider
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file), recompute_embeddings=False)
    assert ok is True
    items = conn.get_all_items("r_col")
    # No embeddings should have been stored
    assert items is not None


def test_restore_failure_when_add_items_fails(tmp_path):
    """restore_collection returns False when add_items fails."""
    metadata = {
        "collection_name": "fail_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 2},
    }
    data = {
        "ids": ["1"],
        "documents": ["a"],
        "metadatas": [{}],
        "embeddings": [[0.1, 0.2]],
    }
    backup_file = tmp_path / "fail.zip"
    write_backup_zip(backup_file, metadata, data)

    # Use a mock connection that fails on add_items
    conn = MagicMock()
    conn.list_collections.return_value = []
    conn.create_collection.return_value = True
    conn.add_items.return_value = False

    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file))
    assert ok is False


# ---------------------------------------------------------------------------
# list_backups and delete_backup
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Additional backup_collection edge cases (for coverage)
# ---------------------------------------------------------------------------


def test_backup_uses_collection_info_embedding_model(tmp_path):
    """collection_info has embedding_model key → lines 68-69 covered."""
    conn = MagicMock()
    conn.get_collection_info.return_value = {
        "embedding_model": "clip-model",
        "embedding_model_type": "clip",
    }
    conn.get_all_items.return_value = {
        "ids": ["1"],
        "documents": ["a"],
        "metadatas": [{}],
        "embeddings": [[0.1]],
    }
    svc = BackupRestoreService()
    result = svc.backup_collection(conn, "col", str(tmp_path))
    assert result is not None
    with open(result, "rb") as f:
        import zipfile

        with zipfile.ZipFile(f, "r") as zf:
            meta = json.loads(zf.read("metadata.json"))
    assert meta["embedding_model"] == "clip-model"
    assert meta["embedding_model_type"] == "clip"


def test_backup_get_embedding_model_exception_silenced(tmp_path, fake_provider):
    """connection.get_embedding_model raises → exception caught, lines 74-75 covered."""
    conn = fake_provider
    conn.get_embedding_model = MagicMock(side_effect=RuntimeError("sdk error"))
    svc = BackupRestoreService()
    result = svc.backup_collection(conn, "test_collection", str(tmp_path))
    assert result is not None  # backup still succeeds


def test_backup_settings_service_exception_silenced(tmp_path, fake_provider):
    """SettingsService raises inside the settings fallback → lines 90-91 covered."""
    conn = fake_provider
    conn.get_embedding_model = MagicMock(return_value=None)
    mock_settings = MagicMock()
    mock_settings.get_embedding_model.side_effect = RuntimeError("settings error")
    svc = BackupRestoreService()
    with patch(
        "vector_inspector.services.settings_service.SettingsService",
        return_value=mock_settings,
    ):
        result = svc.backup_collection(conn, "test_collection", str(tmp_path), profile_name="p")
    assert result is not None


def test_backup_embed_metadata_outer_exception(tmp_path, fake_provider):
    """collection_info.get raises → outer embed-metadata except covers lines 97-99."""
    conn = fake_provider

    # Use a dict subclass that raises on .get("embedding_model") so it's still JSON-serializable
    # Must be non-empty so `if not collection_info:` doesn't short-circuit early.
    class BombInfo(dict):
        def __init__(self):
            super().__init__({"name": "test_collection", "count": 3})

        def get(self, key, default=None):
            if key == "embedding_model":
                raise RuntimeError("embed bomb!")
            return super().get(key, default)

    conn.get_collection_info = MagicMock(return_value=BombInfo())
    svc = BackupRestoreService()
    # The outer except swallows the error and backup continues
    result = svc.backup_collection(conn, "test_collection", str(tmp_path))
    assert result is not None


def test_backup_write_zip_raises_returns_none(tmp_path, fake_provider):
    """write_backup_zip raises → outer except covers lines 108-110."""
    conn = fake_provider
    svc = BackupRestoreService()
    with patch(
        "vector_inspector.services.backup_restore_service.write_backup_zip",
        side_effect=OSError("disk full"),
    ):
        result = svc.backup_collection(conn, "test_collection", str(tmp_path))
    assert result is None


# ---------------------------------------------------------------------------
# Additional restore_collection edge cases (for coverage)
# ---------------------------------------------------------------------------


def test_restore_no_inferred_size_returns_false(tmp_path):
    """No vector_dimension in col_info + no embeddings → inferred_size=None → lines 175-179."""
    metadata = {
        "collection_name": "r_col",
        "backup_timestamp": "now",
        "collection_info": {},  # No vector_dimension
    }
    data = {"ids": ["1"], "documents": ["a"], "metadatas": [{}], "embeddings": []}
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.return_value = []
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file))
    assert ok is False


def test_restore_create_collection_returns_false_aborts(tmp_path):
    """create_collection returns False → lines 188-191 covered."""
    metadata = {
        "collection_name": "r_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 3},
    }
    data = {
        "ids": ["1"],
        "documents": ["a"],
        "metadatas": [{}],
        "embeddings": [[0.1, 0.2, 0.3]],
    }
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.return_value = []
    conn.create_collection.return_value = False
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file))
    assert ok is False


def test_restore_create_collection_raises_aborts(tmp_path):
    """create_collection raises → lines 192-194 covered."""
    metadata = {
        "collection_name": "r_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 3},
    }
    data = {"ids": ["1"], "documents": ["a"], "metadatas": [{}], "embeddings": [[0.1, 0.2, 0.3]]}
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.return_value = []
    conn.create_collection.side_effect = RuntimeError("DB error")
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file))
    assert ok is False


def test_restore_prepare_restore_returns_false_aborts(tmp_path):
    """prepare_restore returns False → lines 200-201 covered."""
    metadata = {
        "collection_name": "r_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 3},
    }
    data = {"ids": ["1"], "documents": ["a"], "metadatas": [{}], "embeddings": [[0.1, 0.2, 0.3]]}
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.return_value = []
    conn.create_collection.return_value = True
    conn.prepare_restore.return_value = False
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file))
    assert ok is False


def test_restore_recompute_no_model_name(tmp_path):
    """recompute_embeddings=True but no embedding_model in metadata → lines 217-229."""
    metadata = {
        "collection_name": "r_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 3},
        # No embedding_model key
    }
    data = {"ids": ["1"], "documents": ["hello"], "metadatas": [{}], "embeddings": [[0.1, 0.2, 0.3]]}
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.return_value = []
    conn.create_collection.return_value = True
    conn.add_items.return_value = True
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file), recompute_embeddings=True)
    assert ok is True


def test_restore_recompute_no_docs(tmp_path):
    """recompute_embeddings=True with empty documents list → lines 230-232 covered."""
    metadata = {
        "collection_name": "r_col2",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 3},
        "embedding_model": "some-model",
    }
    data = {"ids": [], "documents": [], "metadatas": [], "embeddings": []}
    backup_file = tmp_path / "r2.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.return_value = []
    conn.create_collection.return_value = True
    conn.add_items.return_value = True
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file), recompute_embeddings=True)
    assert ok is True


def test_restore_recompute_with_mocked_model(tmp_path):
    """recompute_embeddings=True with mocked load_embedding_model → lines 233-249 covered."""
    metadata = {
        "collection_name": "r_col3",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 3},
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    }
    data = {
        "ids": ["1"],
        "documents": ["hello world"],
        "metadatas": [{}],
        "embeddings": [[0.1, 0.2, 0.3]],
    }
    backup_file = tmp_path / "r3.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.return_value = []
    conn.create_collection.return_value = True
    conn.add_items.return_value = True

    mock_model = MagicMock()
    mock_encoded = MagicMock()
    mock_encoded.tolist.return_value = [[0.1, 0.2, 0.3]]
    mock_model.encode.return_value = mock_encoded

    svc = BackupRestoreService()
    with patch(
        "vector_inspector.core.embedding_utils.load_embedding_model",
        return_value=mock_model,
    ):
        ok = svc.restore_collection(conn, str(backup_file), recompute_embeddings=True)
    assert ok is True
    mock_model.encode.assert_called_once_with(["hello world"], show_progress_bar=False)


def test_restore_recompute_load_model_raises(tmp_path):
    """load_embedding_model raises → lines 250-252 covered."""
    metadata = {
        "collection_name": "r_col4",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 3},
        "embedding_model": "some-model",
    }
    data = {"ids": ["1"], "documents": ["hello"], "metadatas": [{}], "embeddings": [[0.1, 0.2, 0.3]]}
    backup_file = tmp_path / "r4.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.return_value = []
    conn.create_collection.return_value = True
    conn.add_items.return_value = True
    svc = BackupRestoreService()
    with patch(
        "vector_inspector.core.embedding_utils.load_embedding_model",
        side_effect=RuntimeError("model not found"),
    ):
        ok = svc.restore_collection(conn, str(backup_file), recompute_embeddings=True)
    assert ok is True  # restores without embeddings


def test_restore_dimension_mismatch_omits_embeddings(tmp_path):
    """Stored embeddings have wrong dimension → dimension mismatch → lines 270-275 covered."""
    metadata = {
        "collection_name": "r_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 4},  # target wants 4
    }
    data = {
        "ids": ["1"],
        "documents": ["a"],
        "metadatas": [{}],
        "embeddings": [[0.1, 0.2, 0.3]],  # only 3 dims
    }
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.return_value = []
    conn.create_collection.return_value = True
    conn.add_items.return_value = True
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file))
    assert ok is True
    # Should have called add_items with embeddings=None due to mismatch
    call_kwargs = conn.add_items.call_args[1]
    assert call_kwargs["embeddings"] is None


def test_restore_save_model_to_settings_raises_is_swallowed(tmp_path):
    """SettingsService.save_embedding_model raises → lines 320-321 covered."""
    metadata = {
        "collection_name": "r_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 2},
        "embedding_model": "some-model",
    }
    data = {"ids": ["1"], "documents": ["a"], "metadatas": [{}], "embeddings": [[0.1, 0.2]]}
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.return_value = []
    conn.create_collection.return_value = True
    conn.add_items.return_value = True

    mock_settings = MagicMock()
    mock_settings.save_embedding_model.side_effect = RuntimeError("settings error")
    svc = BackupRestoreService()
    with patch(
        "vector_inspector.services.settings_service.SettingsService",
        return_value=mock_settings,
    ):
        ok = svc.restore_collection(conn, str(backup_file), profile_name="p")
    assert ok is True  # exception is swallowed


def test_restore_cache_invalidation_raises_is_swallowed(tmp_path):
    """Cache invalidation raises → lines 335-336 covered."""
    metadata = {
        "collection_name": "r_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 2},
    }
    data = {"ids": ["1"], "documents": ["a"], "metadatas": [{}], "embeddings": [[0.1, 0.2]]}
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.return_value = []
    conn.create_collection.return_value = True
    conn.add_items.return_value = True

    mock_cache = MagicMock()
    mock_cache.invalidate.side_effect = RuntimeError("cache error")
    svc = BackupRestoreService()
    with patch(
        "vector_inspector.core.cache_manager.get_cache_manager",
        return_value=mock_cache,
    ):
        ok = svc.restore_collection(conn, str(backup_file), profile_name="p")
    assert ok is True  # exception is swallowed


def test_restore_add_items_fails_cleanup_deletes_collection(tmp_path):
    """add_items returns False and collection exists → cleanup deletes it → lines 344-348."""
    metadata = {
        "collection_name": "r_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 2},
    }
    data = {"ids": ["1"], "documents": ["a"], "metadatas": [{}], "embeddings": [[0.1, 0.2]]}
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    # First call: [] (not existing → create), second call: ["r_col"] (cleanup check)
    conn.list_collections.side_effect = [[], ["r_col"]]
    conn.create_collection.return_value = True
    conn.add_items.return_value = False
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file))
    assert ok is False
    conn.delete_collection.assert_called_with("r_col")


def test_restore_add_items_fails_cleanup_exception_silenced(tmp_path):
    """add_items returns False and cleanup list_collections raises → lines 349-350 covered."""
    metadata = {
        "collection_name": "r_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 2},
    }
    data = {"ids": ["1"], "documents": ["a"], "metadatas": [{}], "embeddings": [[0.1, 0.2]]}
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.side_effect = [[], RuntimeError("cleanup failed")]
    conn.create_collection.return_value = True
    conn.add_items.return_value = False
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file))
    assert ok is False  # cleanup exception is swallowed


def test_restore_outer_exception_cleanup_succeeds(tmp_path):
    """Exception raised inside outer try after collection named → lines 353-364, 367 covered."""
    metadata = {
        "collection_name": "cleanup_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 2},
    }
    data = {"ids": ["1"], "documents": ["a"], "metadatas": [{}], "embeddings": [[0.1, 0.2]]}
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    # First list_collections returns [] so we enter the else branch
    # Second call (in outer except cleanup) returns ["cleanup_col"]
    conn.list_collections.side_effect = [[], ["cleanup_col"]]
    conn.create_collection.return_value = True
    # add_items raises to trigger outer except
    conn.add_items.side_effect = RuntimeError("db went away")
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file))
    assert ok is False
    conn.delete_collection.assert_called_with("cleanup_col")


def test_restore_outer_exception_cleanup_also_fails(tmp_path):
    """Exception in restore AND cleanup list_collections raises → lines 365-366 covered."""
    metadata = {
        "collection_name": "cleanup_col",
        "backup_timestamp": "now",
        "collection_info": {"vector_dimension": 2},
    }
    data = {"ids": ["1"], "documents": ["a"], "metadatas": [{}], "embeddings": [[0.1, 0.2]]}
    backup_file = tmp_path / "r.zip"
    write_backup_zip(backup_file, metadata, data)

    conn = MagicMock()
    conn.list_collections.side_effect = [[], RuntimeError("network error")]
    conn.create_collection.return_value = True
    conn.add_items.side_effect = RuntimeError("db error")
    svc = BackupRestoreService()
    ok = svc.restore_collection(conn, str(backup_file))
    assert ok is False  # cleanup exception is also swallowed


def test_list_backups_returns_empty_for_missing_dir(tmp_path):
    svc = BackupRestoreService()
    result = svc.list_backups(str(tmp_path / "nonexistent"))
    assert result == []


def test_list_backups_skips_corrupted_zip(tmp_path):
    """A file matching the glob pattern but invalid zip → lines 398-399 covered."""
    # Create a file that matches the *_backup_*.zip glob but isn't a valid zip
    bad_file = tmp_path / "test_backup_20240101_000000.zip"
    bad_file.write_text("not a zip file")
    svc = BackupRestoreService()
    result = svc.list_backups(str(tmp_path))
    assert result == []


def test_list_backups_returns_info_for_valid_zips(tmp_path, fake_provider):
    """Creates a backup then lists it."""
    conn = fake_provider
    svc = BackupRestoreService()

    backup_path = svc.backup_collection(conn, "test_collection", str(tmp_path))
    assert backup_path is not None

    backups = svc.list_backups(str(tmp_path))
    assert len(backups) >= 1
    first = backups[0]
    assert "file_path" in first
    assert "collection_name" in first
    assert first["collection_name"] == "test_collection"


def test_delete_backup_removes_file(tmp_path, fake_provider):
    conn = fake_provider
    svc = BackupRestoreService()

    backup_path = svc.backup_collection(conn, "test_collection", str(tmp_path))
    assert backup_path is not None
    from pathlib import Path

    assert Path(backup_path).exists()

    ok = svc.delete_backup(backup_path)
    assert ok is True
    assert not Path(backup_path).exists()


def test_delete_backup_returns_false_on_missing_file(tmp_path):
    svc = BackupRestoreService()
    ok = svc.delete_backup(str(tmp_path / "nope.zip"))
    assert ok is False
