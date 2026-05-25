import sys

import pytest

pytest.importorskip("pymilvus")

import uuid
from unittest.mock import MagicMock

from vector_inspector.core.connections.milvus_connection import MilvusConnection


def test_milvus_get_collection_info_nonexistent(tmp_path):
    """Test getting info for nonexistent collection."""
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()

    info = conn.get_collection_info("nonexistent_collection")
    assert info is None or info.get("count", 0) == 0

    conn.disconnect()


def test_milvus_delete_collection_nonexistent(tmp_path):
    """Test deleting nonexistent collection doesn't raise."""
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()

    # Should not raise
    result = conn.delete_collection("nonexistent_collection")
    assert isinstance(result, bool)

    conn.disconnect()


def test_milvus_list_collections_empty(tmp_path):
    """Test listing collections on empty database."""
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()

    collections = conn.list_collections()
    assert isinstance(collections, list)

    conn.disconnect()


def test_milvus_distance_metrics(tmp_path):
    """Test creating collections with different distance metrics."""
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()

    for metric in ["Cosine", "L2", "IP"]:
        collection_name = f"test_{metric}_{uuid.uuid4().hex[:6]}"
        result = conn.create_collection(collection_name, vector_size=2, distance=metric)
        assert result is True
        assert collection_name in conn.list_collections()

    conn.disconnect()


def test_milvus_list_collections_exception_returns_empty(tmp_path):
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()

    conn._client.list_collections = MagicMock(side_effect=RuntimeError("list boom"))
    result = conn.list_collections()
    assert result == []
    conn.disconnect()


def test_milvus_delete_collection_exception_returns_false(tmp_path):
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()

    conn._client.drop_collection = MagicMock(side_effect=RuntimeError("drop boom"))
    result = conn.delete_collection("nonexistent")
    assert result is False
    conn.disconnect()


def test_milvus_get_vector_dimension_no_client():
    conn = MilvusConnection(path="/fake/path.db")
    assert conn._get_vector_dimension("col") is None


def test_milvus_get_vector_dimension_non_dict_field_skipped():
    conn = MilvusConnection(path="/fake/path.db")
    mock_client = MagicMock()
    conn._client = mock_client
    mock_client.describe_collection.return_value = {"fields": ["not_a_dict", 42]}
    assert conn._get_vector_dimension("col") is None


def test_milvus_get_vector_dimension_describe_raises_returns_none():
    conn = MilvusConnection(path="/fake/path.db")
    mock_client = MagicMock()
    conn._client = mock_client
    mock_client.describe_collection.side_effect = RuntimeError("describe boom")
    assert conn._get_vector_dimension("col") is None


def test_milvus_ensure_collection_loaded_no_client():
    conn = MilvusConnection(path="/fake/path.db")
    assert conn._ensure_collection_loaded("col") is False


def test_milvus_ensure_collection_loaded_load_raises_returns_false():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    mock_client.load_collection.side_effect = RuntimeError("load boom")
    assert conn._ensure_collection_loaded("col") is False


def test_milvus_list_collections_tuple_response():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    mock_client.list_collections.return_value = ("col_a", "col_b")
    assert conn.list_collections() == ["col_a", "col_b"]


def test_milvus_list_collections_dict_with_collections_key():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    mock_client.list_collections.return_value = {"collections": ["col_x", "col_y"]}
    assert conn.list_collections() == ["col_x", "col_y"]


def test_milvus_list_collections_arbitrary_iterable():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    mock_client.list_collections.return_value = (name for name in ["col_1", "col_2"])
    assert conn.list_collections() == ["col_1", "col_2"]


def test_milvus_get_collection_info_stats_exception_count_zero():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    mock_client.describe_collection.return_value = {"fields": []}
    mock_client.get_collection_stats.side_effect = RuntimeError("stats boom")
    info = conn.get_collection_info("test_col")
    assert info is not None
    assert info["count"] == 0


def test_milvus_create_collection_client_raises_returns_false():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    mock_client.create_collection.side_effect = RuntimeError("create boom")
    assert conn.create_collection("test_col", vector_size=4) is False
