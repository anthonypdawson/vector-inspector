import sys

import pytest

pytest.importorskip("pymilvus")

import uuid
from unittest.mock import MagicMock, patch

from vector_inspector.core.connections.milvus_connection import MilvusConnection


@pytest.mark.xfail(
    sys.platform == "win32",
    reason="Milvus Lite 3.x flush bug on Windows: collections may not persist after disconnect",
    strict=False,
)
def test_milvus_connection_disconnect_reconnect(tmp_path):
    """Test disconnect and reconnect."""
    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus_lite_test.db")

    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)
    conn.disconnect()
    assert not conn.is_connected

    # Reconnect to same DB
    conn2 = MilvusConnection(path=db_path)
    assert conn2.connect()
    # Collection should still exist
    assert collection_name in conn2.list_collections()
    conn2.disconnect()


def test_milvus_not_connected_operations(tmp_path):
    """Test operations on disconnected connection."""
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)

    # Without connecting
    assert not conn.is_connected
    assert conn.list_collections() == []
    assert conn.get_collection_info("test") is None
    assert conn.create_collection("test", 2) is False
    assert conn.add_items("test", documents=["a"]) is False


def test_milvus_connect_no_path_or_host():
    conn = MilvusConnection()
    assert conn.connect() is False
    assert not conn.is_connected


def test_milvus_connect_exception_returns_false(tmp_path):
    with patch("vector_inspector.core.connections.milvus_connection.MilvusClient", side_effect=Exception("fail")):
        conn = MilvusConnection(path=str(tmp_path / "test.db"))
        assert conn.connect() is False
        assert not conn.is_connected


def test_milvus_disconnect_clears_client_and_connected(tmp_path):
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.is_connected
    assert conn._client is not None

    conn.disconnect()
    assert not conn.is_connected
    assert conn._client is None


def test_milvus_connect_empty_path_defaults_to_milvus_db():
    with patch("vector_inspector.core.connections.milvus_connection.MilvusClient") as mock_cls:
        mock_cls.return_value = MagicMock()
        conn = MilvusConnection(path="")
        assert conn.connect()
        uri = mock_cls.call_args[1]["uri"]
        assert uri.endswith(".db")


def test_milvus_connect_path_without_extension_appends_db(tmp_path):
    with patch("vector_inspector.core.connections.milvus_connection.MilvusClient") as mock_cls:
        mock_cls.return_value = MagicMock()
        conn = MilvusConnection(path=str(tmp_path / "mydb_noext"))
        assert conn.connect()
        uri = mock_cls.call_args[1]["uri"]
        assert uri.endswith(".db")
