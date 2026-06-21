import pytest

pytest.importorskip("pymilvus")

import uuid
from unittest.mock import MagicMock

from vector_inspector.core.connections.milvus_connection import MilvusConnection


def test_milvus_get_items_by_id(tmp_path):
    """Test retrieving items by ID."""
    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    docs = ["doc1", "doc2"]
    ids = ["id1", "id2"]
    embeddings = [[0.1, 0.2], [0.3, 0.4]]
    metadata = [{"idx": 1}, {"idx": 2}]

    assert conn.add_items(
        collection_name,
        documents=docs,
        ids=ids,
        embeddings=embeddings,
        metadatas=metadata,
    )

    res = conn.get_items(collection_name, ids=["id1"])
    assert res is not None
    assert "documents" in res
    assert len(res["documents"]) == 1

    conn.disconnect()


def test_milvus_count_collection(tmp_path):
    """Test counting items in a collection."""
    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    ids = ["idA", "idB", "idC"]
    docs = ["one", "two", "three"]
    vecs = [[0.1, 0.2], [0.2, 0.3], [0.3, 0.4]]

    assert conn.add_items(collection_name, documents=docs, ids=ids, embeddings=vecs)
    count = conn.count_collection(collection_name)
    assert isinstance(count, int)
    assert count >= 3

    conn.disconnect()


def test_milvus_delete_items_by_id(tmp_path):
    """Test deleting items by ID."""
    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    ids = ["id1", "id2", "id3"]
    docs = ["a", "b", "c"]
    vecs = [[0.1, 0.2], [0.2, 0.3], [0.3, 0.4]]

    assert conn.add_items(collection_name, documents=docs, ids=ids, embeddings=vecs)
    count_before = conn.count_collection(collection_name)

    assert conn.delete_items(collection_name, ids=["id2"])

    count_after = conn.count_collection(collection_name)
    assert count_after < count_before

    conn.disconnect()


def test_milvus_update_items(tmp_path):
    """Test updating items in a collection."""
    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    ids = ["x", "y"]
    docs = ["old1", "old2"]
    vecs = [[0.1, 0.1], [0.2, 0.2]]

    assert conn.add_items(collection_name, documents=docs, ids=ids, embeddings=vecs)

    updated = conn.update_items(
        collection_name,
        ids=["x"],
        documents=["new1"],
        embeddings=[[0.9, 0.9]],
    )
    assert isinstance(updated, bool)
    assert updated

    conn.disconnect()


def test_milvus_add_items_empty_lists(tmp_path):
    """Test adding empty lists returns True."""
    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    result = conn.add_items(collection_name, documents=[], ids=[], embeddings=[])
    assert result is True


def test_milvus_add_items_without_embeddings(tmp_path):
    """Test adding items without embeddings."""
    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    result = conn.add_items(
        collection_name,
        documents=["doc1", "doc2"],
        ids=["id1", "id2"],
        metadatas=[{"a": 1}, {"a": 2}],
    )
    assert isinstance(result, bool)

    conn.disconnect()


def test_milvus_add_duplicate_ids(tmp_path):
    """Test adding items with duplicate IDs."""
    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    result = conn.add_items(
        collection_name,
        documents=["doc1", "doc2"],
        ids=["id1", "id1"],  # duplicate ids
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
    )
    assert isinstance(result, bool)

    conn.disconnect()


def test_milvus_update_items_empty_ids(tmp_path):
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.update_items("any_collection", ids=[]) is True
    conn.disconnect()


def test_milvus_delete_items_by_where(tmp_path):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    assert conn.add_items(
        collection_name,
        documents=["keep", "remove"],
        ids=["k1", "r1"],
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
        metadatas=[{"tag": "keep"}, {"tag": "remove"}],
    )

    result = conn.delete_items(collection_name, where={"tag": "remove"})
    assert isinstance(result, bool)
    conn.disconnect()


def test_milvus_add_items_exception_returns_false(tmp_path):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    conn._client.insert = MagicMock(side_effect=RuntimeError("insert boom"))
    result = conn.add_items(collection_name, documents=["d"], ids=["i"], embeddings=[[0.1, 0.2]])
    assert result is False
    conn.disconnect()


def test_milvus_count_collection_exception_returns_zero(tmp_path):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    conn._client.get_collection_stats = MagicMock(side_effect=RuntimeError("stats boom"))
    conn._client.query = MagicMock(side_effect=RuntimeError("query boom"))
    result = conn.count_collection(collection_name)
    assert result == 0
    conn.disconnect()


def test_milvus_update_items_exception_returns_false(tmp_path):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    conn._client.upsert = MagicMock(side_effect=RuntimeError("upsert boom"))
    result = conn.update_items(collection_name, ids=["id1"], documents=["doc"], embeddings=[[0.1, 0.2]])
    assert result is False
    conn.disconnect()


def test_milvus_delete_items_exception_returns_false(tmp_path):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.create_collection(collection_name, vector_size=2)

    conn._client.delete = MagicMock(side_effect=RuntimeError("delete boom"))
    result = conn.delete_items(collection_name, ids=["id1"])
    assert result is False
    conn.disconnect()


def test_milvus_get_items_not_connected(tmp_path):
    db_path = str(tmp_path / "milvus.db")
    conn = MilvusConnection(path=db_path)
    result = conn.get_items("col", ids=["id1"])
    assert result == {"documents": [], "metadatas": [], "ids": []}


def test_milvus_add_items_dimension_inference_fails_returns_false():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    conn._get_vector_dimension = MagicMock(return_value=None)
    assert conn.add_items("col", documents=["doc1"], embeddings=None) is False


def test_milvus_get_items_ensure_loaded_fails_returns_empty():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    conn._ensure_collection_loaded = MagicMock(return_value=False)
    result = conn.get_items("col", ids=["id1"])
    assert result == {"documents": [], "metadatas": [], "ids": []}


def test_milvus_get_items_client_get_raises_returns_empty():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    conn._ensure_collection_loaded = MagicMock(return_value=True)
    mock_client.query.side_effect = RuntimeError("query boom")
    result = conn.get_items("col", ids=["id1"])
    assert result == {"documents": [], "metadatas": [], "ids": []}


def test_milvus_count_collection_no_client():
    conn = MilvusConnection(path="/fake/path.db")
    assert conn.count_collection("col") == 0


def test_milvus_count_collection_ensure_loaded_fails():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    conn._ensure_collection_loaded = MagicMock(return_value=False)
    assert conn.count_collection("col") == 0


def test_milvus_count_collection_no_row_count_fallback_query_empty():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    conn._ensure_collection_loaded = MagicMock(return_value=True)
    mock_client.get_collection_stats.return_value = {"other_key": 99}
    mock_client.query.return_value = []
    assert conn.count_collection("col") == 0


def test_milvus_update_items_no_client():
    conn = MilvusConnection(path="/fake/path.db")
    assert conn.update_items("col", ids=["id1"]) is False


def test_milvus_delete_items_no_client():
    conn = MilvusConnection(path="/fake/path.db")
    assert conn.delete_items("col", ids=["id1"]) is False


def test_milvus_delete_items_where_integer_value_unquoted_filter():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    result = conn.delete_items("col", where={"count": 42})
    assert result is True
    call_kwargs = mock_client.delete.call_args[1]
    assert call_kwargs["filter"] == 'metadata["count"] == 42'


def test_milvus_delete_items_where_string_value_quoted_filter():
    conn = MilvusConnection(path="/fake/path.db")
    conn._connected = True
    mock_client = MagicMock()
    conn._client = mock_client
    result = conn.delete_items("col", where={"tag": "remove"})
    assert result is True
    call_kwargs = mock_client.delete.call_args[1]
    assert call_kwargs["filter"] == 'metadata["tag"] == "remove"'
