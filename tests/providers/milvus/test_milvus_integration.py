import sys

import pytest

pytest.importorskip("pymilvus")

import uuid

from vector_inspector.core.connections.milvus_connection import MilvusConnection


@pytest.fixture()
def connected_milvus(tmp_path):
    conn = MilvusConnection(path=str(tmp_path / "test.db"))
    assert conn.connect()
    yield conn
    conn.disconnect()


@pytest.mark.xfail(
    sys.platform == "win32",
    reason="Milvus Lite 3.x uses os.rename() which fails on Windows when the target exists; drop_collection fails",
    strict=False,
)
def test_milvus_connection_integration(tmp_path):
    """Full happy-path: connect, create, add, query, delete."""
    collection_name = f"test_collection_{uuid.uuid4().hex[:8]}"
    test_ids = ["id1", "id2"]
    test_vectors = [[0.1, 0.2], [0.3, 0.4]]
    test_docs = ["hello", "world"]
    test_metadata = [{"type": "greeting"}, {"type": "noun"}]

    db_path = str(tmp_path / "milvus_lite_test.db")
    conn = MilvusConnection(path=db_path)
    assert conn.connect()
    assert conn.is_connected
    assert conn.create_collection(collection_name, vector_size=2, distance="Cosine")

    success = conn.add_items(
        collection_name,
        documents=test_docs,
        metadatas=test_metadata,
        ids=test_ids,
        embeddings=test_vectors,
    )
    assert success

    assert collection_name in conn.list_collections()

    info = conn.get_collection_info(collection_name)
    assert info is not None
    assert info["count"] == 2
    assert info["vector_dimension"] == 2

    res = conn.get_all_items(collection_name, limit=10)
    assert res is not None
    assert len(res["documents"]) == 2

    assert conn.delete_collection(collection_name)
    assert collection_name not in conn.list_collections()

    conn.disconnect()
    assert not conn.is_connected


def test_get_vector_dimension_real(connected_milvus):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    assert connected_milvus.create_collection(collection_name, vector_size=2)
    assert connected_milvus._get_vector_dimension(collection_name) == 2


def test_ensure_collection_loaded_real(connected_milvus):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    assert connected_milvus.create_collection(collection_name, vector_size=2)
    assert connected_milvus._ensure_collection_loaded(collection_name) is True


def test_list_collections_multiple(connected_milvus):
    name_a = f"col_a_{uuid.uuid4().hex[:8]}"
    name_b = f"col_b_{uuid.uuid4().hex[:8]}"
    assert connected_milvus.create_collection(name_a, vector_size=2)
    assert connected_milvus.create_collection(name_b, vector_size=2)
    collections = connected_milvus.list_collections()
    assert name_a in collections
    assert name_b in collections


def test_get_collection_info_with_items(connected_milvus):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    assert connected_milvus.create_collection(collection_name, vector_size=2)
    assert connected_milvus.add_items(
        collection_name,
        documents=["a", "b", "c"],
        ids=["i1", "i2", "i3"],
        embeddings=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
    )
    info = connected_milvus.get_collection_info(collection_name)
    assert info is not None
    assert info["count"] == 3
    assert info["vector_dimension"] == 2


def test_count_collection_real(connected_milvus):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    assert connected_milvus.create_collection(collection_name, vector_size=2)
    assert connected_milvus.add_items(
        collection_name,
        documents=["a", "b", "c", "d"],
        ids=["i1", "i2", "i3", "i4"],
        embeddings=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6], [0.7, 0.8]],
    )
    assert connected_milvus.count_collection(collection_name) >= 4


def test_get_items_by_id_real(connected_milvus):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    assert connected_milvus.create_collection(collection_name, vector_size=2)
    assert connected_milvus.add_items(
        collection_name,
        documents=["hello world"],
        ids=["known_id"],
        embeddings=[[0.1, 0.9]],
    )
    result = connected_milvus.get_items(collection_name, ids=["known_id"])
    assert result is not None
    assert len(result["documents"]) == 1
    assert result["documents"][0] == "hello world"


def test_query_collection_real(connected_milvus):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    assert connected_milvus.create_collection(collection_name, vector_size=2)
    assert connected_milvus.add_items(
        collection_name,
        documents=["near", "far"],
        ids=["id1", "id2"],
        embeddings=[[0.5, 0.5], [0.9, 0.1]],
    )
    result = connected_milvus.query_collection(
        collection_name,
        query_embeddings=[[0.5, 0.5]],
        n_results=2,
    )
    assert result is not None
    assert "ids" in result
    assert "documents" in result
    assert "distances" in result


def test_get_all_items_with_limit_real(connected_milvus):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    assert connected_milvus.create_collection(collection_name, vector_size=2)
    assert connected_milvus.add_items(
        collection_name,
        documents=["a", "b", "c", "d", "e"],
        ids=["i1", "i2", "i3", "i4", "i5"],
        embeddings=[[0.1, 0.1], [0.2, 0.2], [0.3, 0.3], [0.4, 0.4], [0.5, 0.5]],
    )
    result = connected_milvus.get_all_items(collection_name, limit=3)
    assert result is not None
    assert len(result["ids"]) <= 3


def test_update_items_real(connected_milvus):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    assert connected_milvus.create_collection(collection_name, vector_size=2)
    assert connected_milvus.add_items(
        collection_name,
        documents=["original text"],
        ids=["upd_id"],
        embeddings=[[0.1, 0.2]],
    )
    assert connected_milvus.update_items(
        collection_name,
        ids=["upd_id"],
        documents=["updated text"],
        embeddings=[[0.8, 0.9]],
    )
    result = connected_milvus.get_items(collection_name, ids=["upd_id"])
    assert result is not None
    assert len(result["documents"]) == 1
    assert result["documents"][0] == "updated text"


def test_delete_items_by_id_real(connected_milvus):
    collection_name = f"test_{uuid.uuid4().hex[:8]}"
    assert connected_milvus.create_collection(collection_name, vector_size=2)
    assert connected_milvus.add_items(
        collection_name,
        documents=["keep", "delete me"],
        ids=["keep_id", "del_id"],
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
    )
    count_before = connected_milvus.count_collection(collection_name)
    assert connected_milvus.delete_items(collection_name, ids=["del_id"])
    assert connected_milvus.count_collection(collection_name) < count_before


def test_connect_with_directory_path(tmp_path):
    conn = MilvusConnection(path=str(tmp_path))
    assert conn.connect()
    conn.disconnect()


def test_connect_with_no_extension_path(tmp_path):
    conn = MilvusConnection(path=str(tmp_path / "mydb_no_ext"))
    assert conn.connect()
    conn.disconnect()
