from vector_inspector.core.connections.template_connection import TemplateConnection


def test_template_defaults():
    # TemplateConnection is abstract via VectorDBConnection; create a minimal
    # concrete subclass to exercise the base implementations.
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

    conn = ConcreteTemplate()
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
