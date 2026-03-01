"""Tests for VectorDBConnection base class default (non-abstract) methods.

These methods have concrete implementations in the base class and were
uncovered: get_connection_info and get_supported_filter_operators.
"""

from vector_inspector.core.connections.base_connection import VectorDBConnection


class _MinimalConnection(VectorDBConnection):
    """Minimal concrete subclass to instantiate the abstract base class."""

    _connected: bool = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self):
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def list_collections(self) -> list[str]:
        return []

    def get_collection_info(self, name: str):
        return None

    def create_collection(self, name: str, vector_size: int, distance: str = "Cosine") -> bool:
        return True

    def add_items(self, collection_name, documents, metadatas=None, ids=None, embeddings=None):
        return True

    def get_items(self, name, ids):
        return {"documents": [], "metadatas": []}

    def delete_collection(self, name: str) -> bool:
        return True

    def count_collection(self, name: str) -> int:
        return 0

    def query_collection(
        self, collection_name, query_texts=None, query_embeddings=None, n_results=10, where=None, where_document=None
    ):
        return None

    def get_all_items(self, collection_name, limit=None, offset=None, where=None):
        return None

    def update_items(self, collection_name, ids, documents=None, metadatas=None, embeddings=None):
        return True

    def delete_items(self, collection_name, ids=None, where=None):
        return True


# ---------------------------------------------------------------------------
# get_connection_info()
# ---------------------------------------------------------------------------


def test_get_connection_info_returns_dict():
    conn = _MinimalConnection()
    info = conn.get_connection_info()
    assert isinstance(info, dict)


def test_get_connection_info_has_provider_key():
    conn = _MinimalConnection()
    info = conn.get_connection_info()
    assert "provider" in info
    assert info["provider"] == "_MinimalConnection"


def test_get_connection_info_connected_false_when_not_connected():
    conn = _MinimalConnection()
    info = conn.get_connection_info()
    assert info["connected"] is False


def test_get_connection_info_connected_true_when_connected():
    conn = _MinimalConnection()
    conn.connect()
    info = conn.get_connection_info()
    assert info["connected"] is True


# ---------------------------------------------------------------------------
# get_supported_filter_operators()
# ---------------------------------------------------------------------------


def test_get_supported_filter_operators_returns_list():
    conn = _MinimalConnection()
    ops = conn.get_supported_filter_operators()
    assert isinstance(ops, list)
    assert len(ops) > 0


def test_get_supported_filter_operators_each_has_name_and_server_side():
    conn = _MinimalConnection()
    for op in conn.get_supported_filter_operators():
        assert "name" in op
        assert "server_side" in op


def test_get_supported_filter_operators_contains_equality():
    conn = _MinimalConnection()
    names = [op["name"] for op in conn.get_supported_filter_operators()]
    assert "=" in names
    assert "!=" in names


def test_get_supported_filter_operators_contains_comparison():
    conn = _MinimalConnection()
    names = [op["name"] for op in conn.get_supported_filter_operators()]
    assert ">" in names
    assert ">=" in names
    assert "<" in names
    assert "<=" in names


def test_get_supported_filter_operators_contains_in_operators():
    conn = _MinimalConnection()
    names = [op["name"] for op in conn.get_supported_filter_operators()]
    assert "in" in names
    assert "not in" in names


def test_get_supported_filter_operators_contains_contains():
    conn = _MinimalConnection()
    names = [op["name"] for op in conn.get_supported_filter_operators()]
    assert "contains" in names


def test_contains_operator_is_not_server_side():
    """The 'contains' operator should be client-side (server_side=False) by default."""
    conn = _MinimalConnection()
    contains_op = next(op for op in conn.get_supported_filter_operators() if op["name"] == "contains")
    assert contains_op["server_side"] is False


# ---------------------------------------------------------------------------
# get_embedding_model()
# ---------------------------------------------------------------------------


def test_get_embedding_model_from_collection_info():
    """Returns model name stored in collection_info."""
    conn = _MinimalConnection()
    conn.get_collection_info = lambda name: {"embedding_model": "all-MiniLM-L6-v2"}
    result = conn.get_embedding_model("my_col")
    assert result == "all-MiniLM-L6-v2"


def test_get_embedding_model_from_item_metadata(monkeypatch):
    """Falls back to checking first item's metadata when collection_info has no model."""
    conn = _MinimalConnection()
    conn.get_collection_info = lambda name: {}
    conn.get_all_items = lambda name, limit=None, offset=None: {
        "metadatas": [{"_embedding_model": "paraphrase-MiniLM-L6-v2"}]
    }
    result = conn.get_embedding_model("my_col")
    assert result == "paraphrase-MiniLM-L6-v2"


def test_get_embedding_model_from_settings_via_profile_name(monkeypatch):
    """Falls through to settings when no other source available."""
    from unittest.mock import MagicMock, patch

    conn = _MinimalConnection()
    conn.get_collection_info = lambda name: {}
    conn.get_all_items = lambda name, limit=None, offset=None: {"metadatas": [{}]}
    conn.profile_name = "my_profile"

    mock_settings = MagicMock()
    mock_settings.get_embedding_model.return_value = {"model": "settings-model"}

    with patch(
        "vector_inspector.services.settings_service.SettingsService",
        return_value=mock_settings,
    ):
        result = conn.get_embedding_model("my_col")
    assert result == "settings-model"


def test_get_embedding_model_returns_none_when_nothing_found():
    """Returns None when no model found on any source."""
    conn = _MinimalConnection()
    conn.get_collection_info = lambda name: {}
    conn.get_all_items = lambda name, limit=None, offset=None: {"metadatas": [{}]}
    result = conn.get_embedding_model("my_col")
    assert result is None


def test_get_embedding_model_returns_none_on_exception():
    """Returns None without raising when an exception occurs."""
    conn = _MinimalConnection()
    conn.get_collection_info = None  # will cause AttributeError when called
    result = conn.get_embedding_model("col")
    assert result is None
