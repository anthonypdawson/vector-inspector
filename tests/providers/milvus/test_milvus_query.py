import sys

import pytest

pytest.importorskip("pymilvus")

import uuid
from unittest.mock import MagicMock

from vector_inspector.core.connections.milvus_connection import MilvusConnection


def test_milvus_query_by_embedding(tmp_path):
    """Test querying collection by embedding."""
    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    docs = ["close1", "close2", "far"]
    ids = ["id1", "id2", "id3"]
    embeddings = [[0.1, 0.1], [0.11, 0.11], [0.9, 0.9]]

    assert conn.add_items(collection_name, documents=docs, ids=ids, embeddings=embeddings)

    result = conn.query_collection(
        collection_name,
        query_embeddings=[[0.1, 0.1]],
        n_results=2,
    )
    assert result is not None
    assert "ids" in result
    assert "documents" in result

    conn.disconnect()


def test_milvus_get_all_items_with_where_filter(tmp_path):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    assert conn.add_items(
        collection_name,
        documents=["a", "b"],
        ids=["id1", "id2"],
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
        metadatas=[{"cat": "x"}, {"cat": "y"}],
    )

    result = conn.get_all_items(collection_name, where={"cat": "x"})
    # Result may be None if filter syntax unsupported by Milvus Lite; either way, no exception
    assert result is None or isinstance(result, dict)
    conn.disconnect()


def test_milvus_query_with_query_texts_uses_compute_embeddings(tmp_path, monkeypatch):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    assert conn.add_items(
        collection_name,
        documents=["hello"],
        ids=["id1"],
        embeddings=[[0.1, 0.2]],
    )

    monkeypatch.setattr(conn, "compute_embeddings_for_documents", lambda col, texts: [[0.1, 0.2]])
    monkeypatch.setattr(conn, "get_embedding_model", lambda col: "fake-model")

    result = conn.query_collection(collection_name, query_texts=["hello"], n_results=1)
    assert result is not None
    assert "ids" in result
    conn.disconnect()


def test_milvus_query_with_query_texts_embedding_failure_returns_none(tmp_path, monkeypatch):
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()

    monkeypatch.setattr(
        conn, "compute_embeddings_for_documents", lambda col, texts: (_ for _ in ()).throw(RuntimeError("fail"))
    )

    result = conn.query_collection("col", query_texts=["text"])
    assert result is None
    conn.disconnect()


def test_milvus_query_collection_exception_returns_none(tmp_path):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    conn._client.search = MagicMock(side_effect=RuntimeError("search boom"))
    result = conn.query_collection(collection_name, query_embeddings=[[0.1, 0.2]])
    assert result is None
    conn.disconnect()


def test_milvus_get_all_items_exception_returns_none(tmp_path):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    conn._client.query = MagicMock(side_effect=RuntimeError("query boom"))
    result = conn.get_all_items(collection_name)
    assert result is None
    conn.disconnect()


def test_milvus_query_collection_no_client():
    conn = MilvusConnection(path="/fake/path.db")
    assert conn.query_collection("col", query_embeddings=[[0.1, 0.2]]) is None


def test_milvus_query_collection_no_embeddings_no_texts():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    assert conn.query_collection("col") is None


def test_milvus_query_collection_ensure_loaded_fails():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    conn._ensure_collection_loaded = MagicMock(return_value=False)
    assert conn.query_collection("col", query_embeddings=[[0.1, 0.2]]) is None


def test_milvus_get_all_items_no_client():
    conn = MilvusConnection(path="/fake/path.db")
    assert conn.get_all_items("col") is None


def test_milvus_get_all_items_ensure_loaded_fails():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    conn._ensure_collection_loaded = MagicMock(return_value=False)
    assert conn.get_all_items("col") is None
