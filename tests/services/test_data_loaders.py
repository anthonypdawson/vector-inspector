"""Tests for data_loaders.py — CollectionLoader, VectorLoader, MetadataLoader."""

from unittest.mock import MagicMock

from vector_inspector.services.data_loaders import (
    CollectionLoader,
    MetadataLoader,
    VectorLoader,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _conn_with_items(ids=None, docs=None, metadatas=None, embeddings=None):
    """Return a MagicMock connection whose get_all_items returns structured data."""
    conn = MagicMock()
    conn.get_all_items.return_value = {
        "ids": ids or ["1", "2"],
        "documents": docs or ["a", "b"],
        "metadatas": metadatas or [{}, {}],
        "embeddings": embeddings or [[0.1, 0.2], [0.3, 0.4]],
    }
    return conn


# ---------------------------------------------------------------------------
# CollectionLoader
# ---------------------------------------------------------------------------


def test_collection_loader_no_connection_returns_none():
    loader = CollectionLoader()
    assert loader.load_all("col") is None


def test_collection_loader_with_connection_returns_data():
    conn = _conn_with_items()
    loader = CollectionLoader(conn)
    result = loader.load_all("col")
    assert result is not None
    assert result["ids"] == ["1", "2"]
    conn.get_all_items.assert_called_once_with(collection_name="col", limit=None, offset=0)


def test_collection_loader_with_limit_and_offset():
    conn = _conn_with_items()
    loader = CollectionLoader(conn)
    loader.load_all("col", limit=5, offset=10)
    conn.get_all_items.assert_called_once_with(collection_name="col", limit=5, offset=10)


def test_collection_loader_no_get_all_items_returns_none():
    """Connection has no get_all_items attribute → returns None."""
    conn = MagicMock(spec=[])  # spec=[] means no attributes
    loader = CollectionLoader(conn)
    result = loader.load_all("col")
    assert result is None


def test_collection_loader_get_all_items_raises_returns_none():
    conn = MagicMock()
    conn.get_all_items.side_effect = RuntimeError("db error")
    loader = CollectionLoader(conn)
    result = loader.load_all("col")
    assert result is None


def test_collection_loader_set_connection():
    loader = CollectionLoader()
    assert loader.connection is None
    conn = MagicMock()
    loader.set_connection(conn)
    assert loader.connection is conn


def test_collection_loader_load_page():
    conn = _conn_with_items()
    loader = CollectionLoader(conn)
    loader.load_page("col", page=3, page_size=10)
    # page 3, page_size 10 → offset = 20
    conn.get_all_items.assert_called_once_with(collection_name="col", limit=10, offset=20)


def test_get_count_no_connection():
    loader = CollectionLoader()
    assert loader.get_count("col") == 0


def test_get_count_uses_count_method():
    conn = MagicMock()
    conn.count.return_value = 42
    loader = CollectionLoader(conn)
    assert loader.get_count("col") == 42


def test_get_count_uses_get_collection_count_fallback():
    """Connection has no 'count' but has 'get_collection_count'."""
    conn = MagicMock(spec=["get_collection_count"])
    conn.get_collection_count.return_value = 7
    loader = CollectionLoader(conn)
    assert loader.get_count("col") == 7


def test_get_count_neither_method_returns_zero():
    conn = MagicMock(spec=[])  # no count or get_collection_count
    loader = CollectionLoader(conn)
    assert loader.get_count("col") == 0


def test_get_count_raises_returns_zero():
    conn = MagicMock()
    conn.count.side_effect = RuntimeError("db error")
    loader = CollectionLoader(conn)
    assert loader.get_count("col") == 0


# ---------------------------------------------------------------------------
# VectorLoader
# ---------------------------------------------------------------------------


def test_vector_loader_no_connection_returns_none():
    loader = VectorLoader()
    assert loader.load_vectors("col") is None


def test_vector_loader_set_connection():
    loader = VectorLoader()
    conn = MagicMock()
    loader.set_connection(conn)
    assert loader.connection is conn


def test_vector_loader_returns_data():
    conn = _conn_with_items()
    loader = VectorLoader(conn)
    result = loader.load_vectors("col")
    assert result is not None
    assert result["ids"] == ["1", "2"]


def test_vector_loader_with_sample_size():
    conn = _conn_with_items()
    loader = VectorLoader(conn)
    loader.load_vectors("col", sample_size=5)
    conn.get_all_items.assert_called_once_with(collection_name="col", limit=5)


def test_vector_loader_no_get_all_items_returns_none():
    conn = MagicMock(spec=[])
    loader = VectorLoader(conn)
    result = loader.load_vectors("col")
    assert result is None


def test_vector_loader_raises_returns_none():
    conn = MagicMock()
    conn.get_all_items.side_effect = RuntimeError("err")
    loader = VectorLoader(conn)
    assert loader.load_vectors("col") is None


def test_vector_loader_filters_none_embeddings():
    """Items with None embeddings are filtered out."""
    conn = MagicMock()
    conn.get_all_items.return_value = {
        "ids": ["1", "2", "3"],
        "documents": ["a", "b", "c"],
        "metadatas": [{}, {}, {}],
        "embeddings": [[0.1, 0.2], None, [0.3, 0.4]],
    }
    loader = VectorLoader(conn)
    result = loader.load_vectors("col")
    assert result is not None
    assert result["ids"] == ["1", "3"]
    assert len(result["embeddings"]) == 2


def test_vector_loader_all_none_embeddings():
    """All embeddings are None → returns empty lists."""
    conn = MagicMock()
    conn.get_all_items.return_value = {
        "ids": ["1", "2"],
        "documents": ["a", "b"],
        "metadatas": [{}, {}],
        "embeddings": [None, None],
    }
    loader = VectorLoader(conn)
    result = loader.load_vectors("col")
    assert result is not None
    assert result["ids"] == []


def test_vector_loader_filter_no_embeddings_key():
    """Data has no 'embeddings' key → returned as-is."""
    conn = MagicMock()
    conn.get_all_items.return_value = {
        "ids": ["1"],
        "documents": ["a"],
        "metadatas": [{}],
    }
    loader = VectorLoader(conn)
    result = loader.load_vectors("col")
    # No filtering applied since no embeddings key
    assert result["ids"] == ["1"]


def test_vector_loader_returns_none_data_from_connection():
    """Connection returns None → loader returns None."""
    conn = MagicMock()
    conn.get_all_items.return_value = None
    loader = VectorLoader(conn)
    result = loader.load_vectors("col")
    assert result is None


# ---------------------------------------------------------------------------
# MetadataLoader
# ---------------------------------------------------------------------------


def test_metadata_loader_no_connection_returns_none():
    loader = MetadataLoader()
    assert loader.load_metadata("col") is None


def test_metadata_loader_set_connection():
    loader = MetadataLoader()
    conn = MagicMock()
    loader.set_connection(conn)
    assert loader.connection is conn


def test_metadata_loader_loads_all():
    conn = _conn_with_items(
        metadatas=[{"key": "val1"}, {"key": "val2"}],
        embeddings=[[0.1], [0.2]],
    )
    loader = MetadataLoader(conn)
    result = loader.load_metadata("col")
    assert result is not None
    assert "metadatas" in result
    assert "embeddings" not in result  # embeddings stripped


def test_metadata_loader_loads_by_ids():
    conn = MagicMock()
    conn.get_by_ids.return_value = {
        "ids": ["1"],
        "metadatas": [{"key": "v"}],
        "documents": ["doc"],
    }
    loader = MetadataLoader(conn)
    result = loader.load_metadata("col", item_ids=["1"])
    assert result is not None
    conn.get_by_ids.assert_called_once_with("col", ["1"])


def test_metadata_loader_no_get_by_ids_returns_none():
    conn = MagicMock(spec=["get_all_items"])
    # spec omits get_by_ids, so hasattr returns False
    conn.get_all_items.return_value = None
    loader = MetadataLoader(conn)
    result = loader.load_metadata("col", item_ids=["1"])
    assert result is None


def test_metadata_loader_no_get_all_items_returns_none():
    """Connection has no get_all_items → returns None when loading all."""
    conn = MagicMock(spec=[])
    loader = MetadataLoader(conn)
    result = loader.load_metadata("col")
    assert result is None


def test_metadata_loader_raises_returns_none():
    conn = MagicMock()
    conn.get_all_items.side_effect = RuntimeError("db error")
    loader = MetadataLoader(conn)
    result = loader.load_metadata("col")
    assert result is None


def test_get_metadata_fields_empty_data():
    loader = MetadataLoader()
    assert loader.get_metadata_fields({}) == []
    assert loader.get_metadata_fields(None) == []
    assert loader.get_metadata_fields({"metadatas": []}) == []


def test_get_metadata_fields_returns_sorted_unique_keys():
    loader = MetadataLoader()
    data = {
        "metadatas": [
            {"name": "a", "tag": "x"},
            {"name": "b", "score": 1.0},
        ]
    }
    fields = loader.get_metadata_fields(data)
    assert fields == ["name", "score", "tag"]


def test_get_metadata_fields_skips_non_dict_metadata():
    loader = MetadataLoader()
    data = {
        "metadatas": [
            {"key": "val"},
            None,  # Non-dict metadata
        ]
    }
    fields = loader.get_metadata_fields(data)
    assert "key" in fields
