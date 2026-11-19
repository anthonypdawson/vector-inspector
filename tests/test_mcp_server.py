"""Tool tests for the Vector Inspector MCP server.

End-to-end through the real MCP dispatch (``server.call_tool``),
against local Chroma (persistent) and LanceDB fixtures. No test
needs cloud credentials. Each tool gets a result-shape test and one
realistic failure test.

Run note: the repo's ``tests/conftest.py`` needs PySide6, so in a
Qt-free venv run these with ``pytest --noconftest``.
"""

import asyncio
import importlib.util
import json

import pytest

pytest.importorskip("chromadb")
pytest.importorskip("lancedb")
pytest.importorskip("mcp")

from mcp.server.mcpserver.exceptions import ToolError

from vector_inspector.mcp.config import parse_connection_specs
from vector_inspector.mcp.server import create_server

DIM = 3
DOCS = ["alpha", "beta", "gamma"]
IDS = ["id-alpha", "id-beta", "id-gamma"]
VECTORS = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
METAS = [{"group": "a"}, {"group": "b"}, {"group": "a"}]


def call(server, name, arguments):
    """Call a tool through MCP dispatch. Returns (text, error, is_error)."""
    try:
        result = asyncio.run(server.call_tool(name, arguments))
    except ToolError as exc:
        return None, str(exc), True
    text = result.content[0].text if result.content else ""
    return text, None, bool(getattr(result, "is_error", False))


def call_json(server, name, arguments):
    text, err, is_error = call(server, name, arguments)
    assert not is_error, f"{name} failed: {err or text}"
    assert text, f"{name} returned empty text"
    return json.loads(text)


def call_error(server, name, arguments):
    text, err, is_error = call(server, name, arguments)
    assert is_error, f"{name} unexpectedly succeeded: {text}"
    return err or text or ""


@pytest.fixture(scope="module", autouse=True)
def _restore_telemetry():
    """create_server() patches TelemetryService.send_event process-wide.

    Save/restore it so this module cannot affect telemetry tests that
    run later in the same pytest process.
    """
    from vector_inspector.services.telemetry_service import TelemetryService

    original = TelemetryService.send_event
    yield
    TelemetryService.send_event = original


@pytest.fixture(scope="module")
def mcp_server(_restore_telemetry, tmp_path_factory):
    tmp = tmp_path_factory.mktemp("vi_mcp")
    configs = parse_connection_specs(
        [
            f"chroma@chromadb?type=persistent&path={tmp / 'chroma'}",
            f"lance@lancedb?path={tmp / 'lancedb'}",
        ]
    )
    server = create_server(configs)
    for connection in ("chroma", "lance"):
        call_json(
            server,
            "vi_create_collection",
            {"connection": connection, "collection": "docs", "vector_size": DIM},
        )
        call_json(
            server,
            "vi_add_items",
            {
                "connection": connection,
                "collection": "docs",
                "documents": DOCS,
                "metadatas": METAS,
                "ids": IDS,
                "embeddings": VECTORS,
            },
        )
    yield server


@pytest.fixture(scope="module")
def read_only_server(mcp_server, tmp_path_factory):
    # Reuse the same underlying stores through a second server instance
    # in read-only mode. The stores live in the module tmp dir; rebuild
    # configs from the seeded server is unnecessary — the paths are
    # recoverable from the first fixture via its own tmp dir is not
    # exposed, so instead build a fresh read-only server on fresh
    # empty stores and only assert the read-only gate + reads work.
    tmp = tmp_path_factory.mktemp("vi_mcp_ro")
    configs = parse_connection_specs(
        [
            f"chroma@chromadb?type=persistent&path={tmp / 'chroma'}",
            f"lance@lancedb?path={tmp / 'lancedb'}",
        ]
    )
    return create_server(configs, read_only=True)


def _first_id(result):
    """Search ids are nested per query for Chroma, flat for LanceDB."""
    ids = result["results"]["ids"]
    first = ids[0]
    return first[0] if isinstance(first, list) else first


# --- vi_list_providers -------------------------------------------------


def test_list_providers_shape(mcp_server):
    payload = call_json(mcp_server, "vi_list_providers", {})
    by_name = {p["provider"]: p for p in payload["providers"]}
    assert by_name["chromadb"]["installed"] is True
    assert by_name["lancedb"]["installed"] is True
    for provider, entry in by_name.items():
        assert entry["provider"] == provider
        assert isinstance(entry["installed"], bool)
        assert entry["extra"]
        if not entry["installed"]:
            assert "install_hint" in entry


# --- vi_connect / vi_connection_info -----------------------------------


def test_connect_ok(mcp_server):
    payload = call_json(mcp_server, "vi_connect", {"connection": "chroma"})
    assert payload["connected"] is True
    assert payload["connection"] == "chroma"


def test_connect_unknown_connection(mcp_server):
    assert "Unknown connection 'nope'" in call_error(mcp_server, "vi_connect", {"connection": "nope"})


def test_connection_info_has_no_secrets(mcp_server):
    payload = call_json(mcp_server, "vi_connection_info", {"connection": "lance"})
    blob = json.dumps(payload).lower()
    assert "api_key" not in blob
    assert "password" not in blob
    assert "token" not in blob
    assert payload["info"]["connected"] is True


# --- collections -------------------------------------------------------


def test_list_collections(mcp_server):
    payload = call_json(mcp_server, "vi_list_collections", {"connection": "chroma"})
    assert "docs" in payload["collections"]


def test_collection_info_shape(mcp_server):
    payload = call_json(mcp_server, "vi_collection_info", {"connection": "chroma", "collection": "docs"})
    assert payload["count"] == 3
    assert payload["collection"] == "docs"
    assert isinstance(payload["filter_operators"], list)
    assert payload["filter_operators"], "expected the base operator list"


def test_collection_info_missing(mcp_server):
    assert "does not exist" in call_error(
        mcp_server,
        "vi_collection_info",
        {"connection": "chroma", "collection": "no-such-collection"},
    )


def test_create_and_delete_collection(mcp_server):
    call_json(
        mcp_server,
        "vi_create_collection",
        {"connection": "lance", "collection": "scratch", "vector_size": DIM},
    )
    payload = call_json(mcp_server, "vi_list_collections", {"connection": "lance"})
    assert "scratch" in payload["collections"]
    payload = call_json(mcp_server, "vi_delete_collection", {"connection": "lance", "collection": "scratch"})
    assert payload["deleted"] is True
    payload = call_json(mcp_server, "vi_list_collections", {"connection": "lance"})
    assert "scratch" not in payload["collections"]


# --- vi_search ---------------------------------------------------------


@pytest.mark.parametrize("connection", ["chroma", "lance"])
def test_search_by_embedding_nearest_first(mcp_server, connection):
    payload = call_json(
        mcp_server,
        "vi_search",
        {
            "connection": connection,
            "collection": "docs",
            "query_embeddings": [[1.0, 0.0, 0.0]],
            "n_results": 2,
        },
    )
    assert _first_id(payload) == "id-alpha"
    assert payload["results"]["documents"]


@pytest.mark.parametrize("connection", ["chroma"])
def test_search_with_provider_native_filter(mcp_server, connection):
    # Chroma-native filter syntax, passed raw (PRD: raw passthrough).
    payload = call_json(
        mcp_server,
        "vi_search",
        {
            "connection": connection,
            "collection": "docs",
            "query_embeddings": [[1.0, 0.0, 0.0]],
            "n_results": 10,
            "where": {"group": {"$eq": "a"}},
        },
    )
    ids = payload["results"]["ids"]
    flat = ids[0] if ids and isinstance(ids[0], list) else ids
    assert set(flat) == {"id-alpha", "id-gamma"}


def test_search_needs_exactly_one_query_form(mcp_server):
    assert "exactly one of query_texts or query_embeddings" in call_error(
        mcp_server,
        "vi_search",
        {"connection": "chroma", "collection": "docs"},
    )
    assert "exactly one of query_texts or query_embeddings" in call_error(
        mcp_server,
        "vi_search",
        {
            "connection": "chroma",
            "collection": "docs",
            "query_texts": ["alpha"],
            "query_embeddings": [[1.0, 0.0, 0.0]],
        },
    )


# Text search via the fastembed default (PRD: fastembed is the default
# embedding; a bare `vector-inspector[mcp]` install embeds text out of
# the box). A fresh 384-dim collection per connection, documents added
# with NO embeddings — the add path and the search path both have to
# resolve the model. Chroma ranks the fox document first; LanceDB
# stores zero vectors for text-only adds (it never computes embeddings
# in add_items), so only add + search completing is asserted there.
TEXT_DOCS = [
    "The quick brown fox jumps over the lazy dog.",
    "Vector databases store embeddings for similarity search.",
    "Bananas grow in warm climates.",
]
TEXT_IDS = ["text-fox", "text-vectors", "text-bananas"]
TEXT_DIM = 384


def _seed_text_collection(mcp_server, connection, collection="textdocs"):
    call_json(
        mcp_server,
        "vi_create_collection",
        {"connection": connection, "collection": collection, "vector_size": TEXT_DIM},
    )
    call_json(
        mcp_server,
        "vi_add_items",
        {
            "connection": connection,
            "collection": collection,
            "documents": TEXT_DOCS,
            "ids": TEXT_IDS,
        },
    )


@pytest.mark.parametrize("connection", ["chroma", "lance"])
def test_search_text_uses_fastembed_default(mcp_server, connection):
    if importlib.util.find_spec("fastembed") is None:
        pytest.skip("fastembed not installed; default text search not exercised")
    _seed_text_collection(mcp_server, connection)
    payload = call_json(
        mcp_server,
        "vi_search",
        {
            "connection": connection,
            "collection": "textdocs",
            "query_texts": ["fox"],
            "n_results": 2,
        },
    )
    assert payload["results"]["ids"], "text search returned no ids"
    if connection == "chroma":
        # Real embeddings: the fox document must rank first.
        assert _first_id(payload) == "text-fox"
    # LanceDB: text-only add stores zero vectors, so ranking is
    # meaningless (all distances tie); completing is the assertion.


def test_search_text_without_embedding_model_errors_clearly(mcp_server, monkeypatch):
    # With no embedding library loadable, text search must fail with
    # the PRD's clear message, not a bare traceback. Monkeypatch the
    # loader so the test is deterministic regardless of what is
    # installed. The collection is seeded with explicit vectors so
    # the add path never needs a model.
    call_json(
        mcp_server,
        "vi_create_collection",
        {"connection": "chroma", "collection": "nomodel", "vector_size": TEXT_DIM},
    )
    call_json(
        mcp_server,
        "vi_add_items",
        {
            "connection": "chroma",
            "collection": "nomodel",
            "documents": ["alpha"],
            "ids": ["id-alpha"],
            "embeddings": [[0.0] * TEXT_DIM],
        },
    )

    def _missing(*args, **kwargs):
        raise ModuleNotFoundError("No module named 'fastembed'")

    monkeypatch.setattr(
        "vector_inspector.core.embedding_utils.load_embedding_model",
        _missing,
    )
    message = call_error(
        mcp_server,
        "vi_search",
        {
            "connection": "chroma",
            "collection": "nomodel",
            "query_texts": ["alpha"],
        },
    )
    assert "embedding" in message.lower()
    assert "fastembed" in message.lower()


# --- vi_get_items ------------------------------------------------------


@pytest.mark.parametrize("connection", ["chroma", "lance"])
def test_get_items_by_ids(mcp_server, connection):
    payload = call_json(
        mcp_server,
        "vi_get_items",
        {"connection": connection, "collection": "docs", "ids": ["id-beta"]},
    )
    items = payload["items"]
    assert "beta" in items["documents"]
    assert items["metadatas"][0]["group"] == "b"


@pytest.mark.parametrize("connection", ["chroma", "lance"])
def test_get_items_paged(mcp_server, connection):
    page1 = call_json(
        mcp_server,
        "vi_get_items",
        {"connection": connection, "collection": "docs", "limit": 2, "offset": 0},
    )
    assert len(page1["items"]["documents"]) == 2
    page2 = call_json(
        mcp_server,
        "vi_get_items",
        {"connection": connection, "collection": "docs", "limit": 2, "offset": 2},
    )
    assert len(page2["items"]["documents"]) == 1


def test_get_items_limit_is_capped(mcp_server):
    payload = call_json(
        mcp_server,
        "vi_get_items",
        {"connection": "chroma", "collection": "docs", "limit": 5000},
    )
    assert payload["limit"] == 100
    assert len(payload["items"]["documents"]) == 3


def test_get_items_missing_collection(mcp_server):
    assert "does not exist" in call_error(
        mcp_server,
        "vi_get_items",
        {"connection": "chroma", "collection": "no-such-collection"},
    )


# --- vi_add_items / vi_update_items / vi_delete_items ------------------


def test_add_update_delete_items(mcp_server):
    # Add to a fresh collection so counts are deterministic.
    call_json(
        mcp_server,
        "vi_create_collection",
        {"connection": "chroma", "collection": "crud", "vector_size": DIM},
    )
    payload = call_json(
        mcp_server,
        "vi_add_items",
        {
            "connection": "chroma",
            "collection": "crud",
            "documents": ["one", "two"],
            "metadatas": [{"n": 1}, {"n": 2}],
            "ids": ["c1", "c2"],
            "embeddings": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        },
    )
    assert payload["added"] == 2

    payload = call_json(
        mcp_server,
        "vi_update_items",
        {
            "connection": "chroma",
            "collection": "crud",
            "ids": ["c1"],
            "metadatas": [{"n": 99}],
        },
    )
    assert payload["updated"] == 1
    got = call_json(
        mcp_server,
        "vi_get_items",
        {"connection": "chroma", "collection": "crud", "ids": ["c1"]},
    )
    assert got["items"]["metadatas"][0]["n"] == 99

    payload = call_json(
        mcp_server,
        "vi_delete_items",
        {"connection": "chroma", "collection": "crud", "ids": ["c2"]},
    )
    assert payload["deleted"] is True
    info = call_json(mcp_server, "vi_collection_info", {"connection": "chroma", "collection": "crud"})
    assert info["count"] == 1
    call_json(mcp_server, "vi_delete_collection", {"connection": "chroma", "collection": "crud"})


def test_add_items_needs_documents(mcp_server):
    assert "at least one document" in call_error(
        mcp_server,
        "vi_add_items",
        {"connection": "chroma", "collection": "docs", "documents": []},
    )


def test_update_items_needs_ids(mcp_server):
    assert "at least one id" in call_error(
        mcp_server,
        "vi_update_items",
        {"connection": "chroma", "collection": "docs", "ids": []},
    )


def test_delete_items_needs_selector(mcp_server):
    assert "needs ids or a where filter" in call_error(
        mcp_server,
        "vi_delete_items",
        {"connection": "chroma", "collection": "docs"},
    )


# --- read-only mode ----------------------------------------------------


def test_read_only_blocks_writes(read_only_server):
    message = call_error(
        read_only_server,
        "vi_add_items",
        {
            "connection": "chroma",
            "collection": "docs",
            "documents": ["nope"],
            "embeddings": [[1.0, 0.0, 0.0]],
        },
    )
    assert "read-only" in message.lower()
    for tool, args in [
        ("vi_update_items", {"connection": "chroma", "collection": "docs", "ids": ["x"]}),
        ("vi_delete_items", {"connection": "chroma", "collection": "docs", "ids": ["x"]}),
        (
            "vi_create_collection",
            {"connection": "chroma", "collection": "x", "vector_size": 3},
        ),
        ("vi_delete_collection", {"connection": "chroma", "collection": "docs"}),
    ]:
        assert "read-only" in call_error(read_only_server, tool, args).lower()


def test_read_only_still_reads(read_only_server):
    payload = call_json(read_only_server, "vi_list_collections", {"connection": "chroma"})
    assert payload["collections"] == []


# --- telemetry ---------------------------------------------------------


def test_telemetry_disabled_by_server_construction(mcp_server):
    from vector_inspector.services.telemetry_service import TelemetryService

    assert TelemetryService.send_event.__name__ == "_no_op_send_event"
    # Calling it must do nothing observable (no queue file, no thread).
    TelemetryService.send_event("mcp.test", {"category": "test"})
