from unittest.mock import MagicMock

from vector_inspector.core.connections.template_connection import TemplateConnection


def _make_concrete() -> TemplateConnection:
    """Return a minimal concrete subclass of TemplateConnection."""

    class ConcreteTemplate(TemplateConnection):
        def connect(self) -> bool:
            return super().connect()

        def disconnect(self):
            return super().disconnect()

        @property
        def is_connected(self) -> bool:
            return super().is_connected

        def list_collections(self) -> list[str]:
            return super().list_collections()

        def get_collection_info(self, name: str):
            return super().get_collection_info(name)

        def create_collection(self, name: str, vector_size: int, distance: str = "Cosine") -> bool:
            return True

        def add_items(self, collection_name: str, documents, metadatas=None, ids=None, embeddings=None) -> bool:
            return super().add_items(collection_name, documents, metadatas, ids, embeddings)

        def get_items(self, name: str, ids: list[str]):
            return {"documents": [], "metadatas": []}

        def delete_collection(self, name: str) -> bool:
            return super().delete_collection(name)

        def count_collection(self, name: str) -> int:
            return 0

        def query_collection(self, *args, **kwargs):
            return super().query_collection(*args, **kwargs)

        def get_all_items(self, *args, **kwargs):
            return super().get_all_items(*args, **kwargs)

        def update_items(self, *args, **kwargs):
            return super().update_items(*args, **kwargs)

        def delete_items(self, *args, **kwargs):
            return super().delete_items(*args, **kwargs)

    return ConcreteTemplate()


def test_template_defaults():
    conn = _make_concrete()
    # connect() returns True (best-effort) even though no client is created
    assert conn.connect() is True
    # Not actually connected because _client remains None
    assert conn.is_connected is False

    # Methods that require a client should return empty / falsy values
    assert conn.list_collections() == []
    assert conn.get_collection_info("foo") is None
    assert conn.query_collection("foo") is None
    assert conn.get_all_items("foo") is None
    assert conn.add_items("foo", ["a"]) is False
    assert conn.update_items("foo", ["id1"]) is False
    assert conn.delete_items("foo", ids=["id1"]) is False
    assert conn.delete_collection("foo") is False

    info = conn.get_connection_info()
    assert isinstance(info, dict)
    assert info.get("provider") == "Template"


def test_disconnect_resets_client():
    """disconnect() sets _client to None."""
    conn = _make_concrete()
    conn._client = MagicMock()  # simulate a connected state
    assert conn.is_connected is True

    conn.disconnect()
    assert conn._client is None
    assert conn.is_connected is False


def test_methods_with_client_set():
    """Calling methods when _client is set covers the 'happy path' branches."""
    conn = _make_concrete()
    conn._client = MagicMock()  # bypass connect(); set client directly

    # list_collections — returns [] stub
    result = conn.list_collections()
    assert result == []

    # get_collection_info — returns dict stub
    info = conn.get_collection_info("my-collection")
    assert isinstance(info, dict)
    assert info["name"] == "my-collection"
    assert info["count"] == 0

    # query_collection — returns dict stub
    qr = conn.query_collection("my-collection")
    assert isinstance(qr, dict)
    assert "ids" in qr

    # get_all_items — returns dict stub
    items = conn.get_all_items("my-collection")
    assert isinstance(items, dict)
    assert "ids" in items

    # add_items — returns True stub
    assert conn.add_items("my-collection", ["doc1"], metadatas=[{}], ids=["id1"]) is True

    # update_items — returns True stub
    assert conn.update_items("my-collection", ["id1"], documents=["doc1"]) is True

    # delete_items — returns True stub
    assert conn.delete_items("my-collection", ids=["id1"]) is True

    # delete_collection — returns True stub
    assert conn.delete_collection("my-collection") is True

    # get_connection_info — connected state
    ci = conn.get_connection_info()
    assert ci["connected"] is True
