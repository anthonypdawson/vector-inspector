"""Vector Inspector MCP server: the provider layer as MCP tools.

One server, one tool surface, any supported vector database. Tools
are named once (``vi_*``) and take a ``connection`` name; connections
are named in the server configuration (see ``config.py``) and open
lazily on first use, staying open for the server's lifetime.

Safety rules (PRD):
- stdio only; never ``print()`` to stdout — logging goes to stderr.
- Telemetry is forced off in this process (see
  :func:`disable_telemetry`): the telemetry service defaults to
  enabled when its setting is unset, and ``VI_NO_TELEMETRY=1`` alone
  does not cover the ``log_tracked_error`` path the provider layer
  uses, so the send path is neutralised in-process.
- ``--read-only`` blocks all mutating tools.
- ``vi_get_items`` pages with a capped limit; no unbounded dumps.
- No secrets ever appear in tool output.
- Filters (``where``) are provider-native and passed raw.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from vector_inspector.core.connections import get_connection_class
from vector_inspector.core.connections.base_connection import VectorDBConnection
from vector_inspector.core.provider_factory import ProviderFactory
from vector_inspector.mcp.config import (
    PROVIDER_EXTRAS,
    SUPPORTED_PROVIDERS,
    ConnectionConfig,
)

logger = logging.getLogger(__name__)

# vi_get_items paging guard: never return more than this many items
# in one call, however large the limit the agent asks for.
MAX_ITEMS_PER_CALL = 100
DEFAULT_ITEMS_PER_CALL = 50

# Mutating tools, blocked by --read-only.
MUTATING_TOOLS = frozenset(
    {
        "vi_add_items",
        "vi_update_items",
        "vi_delete_items",
        "vi_create_collection",
        "vi_delete_collection",
    }
)

_SECRET_KEY_PARTS = ("api_key", "apikey", "password", "passwd", "token", "secret")


def disable_telemetry() -> None:
    """Neutralise telemetry for this process.

    ``TelemetryService.is_enabled()`` defaults to True when the
    ``telemetry.enabled`` setting is unset, and ``VI_NO_TELEMETRY=1``
    is only honoured by the desktop CLI's launch path — it does not
    cover the ``log_tracked_error`` -> ``TelemetryService.send_event``
    path used throughout the provider layer. Replacing ``send_event``
    with a no-op is process-local, touches no user settings, and
    guarantees an agent tool can never phone home.
    """
    try:
        from vector_inspector.services.telemetry_service import TelemetryService

        def _no_op_send_event(event_name: str, payload: dict) -> None:
            return None

        TelemetryService.send_event = staticmethod(_no_op_send_event)  # type: ignore[method-assign]
        logger.info("Telemetry disabled for MCP server process")
    except Exception as exc:  # pragma: no cover - defensive; telemetry import is local-only
        logger.warning("Could not disable telemetry: %s", exc)


def _strip_secrets(value: Any) -> Any:
    """Recursively remove secret-like keys from tool output."""
    if isinstance(value, dict):
        return {
            k: _strip_secrets(v) for k, v in value.items() if not any(part in k.lower() for part in _SECRET_KEY_PARTS)
        }
    if isinstance(value, list):
        return [_strip_secrets(v) for v in value]
    return value


def _to_json(payload: Any) -> str:
    """Serialize a tool result; never leaks secrets, never fails on odd types."""
    return json.dumps(_strip_secrets(payload), default=str, indent=2)


def _embedding_error_message(exc: BaseException) -> str | None:
    """Return the PRD's clear message if this is a missing-embedding-model failure."""
    text = f"{type(exc).__name__}: {exc}".lower()
    if "embedding" in text or isinstance(exc, (ImportError, ModuleNotFoundError)):
        return (
            "Text search needs an embedding model, and none is available: "
            "install the sentence-transformers extra "
            "(pip install vector-inspector[sentence-transformers]) or pass "
            "query_embeddings (raw vectors) instead of query_texts. "
            f"Underlying error: {exc}"
        )
    return None


class ConnectionRegistry:
    """Named connections, opened lazily and kept for the server lifetime."""

    def __init__(self, configs: dict[str, ConnectionConfig], read_only: bool = False):
        self._configs = configs
        self._connections: dict[str, VectorDBConnection] = {}
        self.read_only = read_only

    @property
    def names(self) -> list[str]:
        return sorted(self._configs)

    def require_writable(self, tool: str) -> None:
        if self.read_only:
            raise ToolError(
                f"Server is running in read-only mode; {tool} is blocked. Restart without --read-only to allow writes."
            )

    def get(self, name: str) -> VectorDBConnection:
        """Return the live connection, opening it on first use.

        A failed connect is not cached: the next call retries.
        """
        if name not in self._configs:
            known = ", ".join(self.names) or "(none configured)"
            raise ToolError(f"Unknown connection '{name}'. Configured connections: {known}.")
        if name not in self._connections:
            cfg = self._configs[name]
            try:
                credentials = cfg.resolve_credentials()
            except ValueError as exc:
                raise ToolError(str(exc)) from exc
            try:
                conn = ProviderFactory.create(cfg.provider, cfg.factory_config(), credentials)
            except (ImportError, ValueError) as exc:
                raise ToolError(f"Cannot create connection '{name}' ({cfg.provider}): {exc}") from exc
            try:
                if not conn.connect():
                    raise ToolError(
                        f"Connection '{name}' ({cfg.provider}) failed to connect; check its path/host and credentials."
                    )
            except ToolError:
                raise
            except Exception as exc:
                raise ToolError(f"Connection '{name}' ({cfg.provider}) failed to connect: {exc}") from exc
            self._connections[name] = conn
        return self._connections[name]

    def close_all(self) -> None:
        for name, conn in list(self._connections.items()):
            try:
                conn.disconnect()
            except Exception as exc:
                logger.warning("Error disconnecting '%s': %s", name, exc)
        self._connections.clear()


def create_server(
    configs: dict[str, ConnectionConfig] | None = None,
    read_only: bool = False,
) -> MCPServer:
    """Build the MCP server for the given named connections."""
    disable_telemetry()
    registry = ConnectionRegistry(configs or {}, read_only=read_only)
    mcp = MCPServer(
        name="vector-inspector",
        title="Vector Inspector",
        description=(
            "Inspect, search, and manage vector databases "
            "(ChromaDB, Qdrant, Pinecone, LanceDB, pgvector, Weaviate, "
            "Milvus) through one tool surface."
        ),
        version="0.8.4",
    )

    @mcp.tool()
    def vi_list_providers() -> str:
        """List supported providers and whether each client's library is installed."""
        providers = []
        for provider in SUPPORTED_PROVIDERS:
            try:
                get_connection_class(provider)
                providers.append({"provider": provider, "installed": True, "extra": PROVIDER_EXTRAS[provider]})
            except ImportError:
                providers.append(
                    {
                        "provider": provider,
                        "installed": False,
                        "extra": PROVIDER_EXTRAS[provider],
                        "install_hint": f"pip install vector-inspector[{PROVIDER_EXTRAS[provider]}]",
                    }
                )
        return _to_json({"providers": providers})

    @mcp.tool()
    def vi_connect(connection: str) -> str:
        """Open a named connection (or confirm it is already open).

        Connections also open lazily on first use by any other tool;
        this tool exists to surface connection errors early. Never
        returns credentials.
        """
        conn = registry.get(connection)
        return _to_json(
            {
                "connection": connection,
                "connected": conn.is_connected,
                "info": conn.get_connection_info(),
            }
        )

    @mcp.tool()
    def vi_list_collections(connection: str) -> str:
        """List collection names on a connection."""
        conn = registry.get(connection)
        try:
            names = conn.list_collections()
        except Exception as exc:
            raise ToolError(f"Could not list collections on '{connection}': {exc}") from exc
        return _to_json({"connection": connection, "collections": names})

    @mcp.tool()
    def vi_collection_info(connection: str, collection: str) -> str:
        """Schema, vector size, distance, item count, and supported filter operators for a collection."""
        conn = registry.get(connection)
        try:
            info = conn.get_collection_info(collection)
        except Exception as exc:
            raise ToolError(f"Could not get info for collection '{collection}' on '{connection}': {exc}") from exc
        if info is None:
            raise ToolError(f"Collection '{collection}' does not exist on connection '{connection}'.")
        try:
            count = conn.count_collection(collection)
        except Exception:
            count = None
        try:
            operators = conn.get_supported_filter_operators()
        except Exception:
            operators = []
        return _to_json(
            {
                "connection": connection,
                "collection": collection,
                "count": count,
                "filter_operators": operators,
                "info": info,
            }
        )

    @mcp.tool()
    def vi_search(
        connection: str,
        collection: str,
        query_texts: list[str] | None = None,
        query_embeddings: list[list[float]] | None = None,
        n_results: int = 10,
        where: dict | None = None,
        where_document: dict | None = None,
    ) -> str:
        """Search a collection by text (embedded server-side) or raw vectors.

        Pass exactly one of query_texts or query_embeddings. Filters
        (where / where_document) are provider-native and passed raw —
        see the server docs for each provider's filter syntax.
        """
        if bool(query_texts) == bool(query_embeddings):
            raise ToolError(
                "vi_search needs exactly one of query_texts or "
                "query_embeddings (got "
                f"{'both' if query_texts and query_embeddings else 'neither'})."
            )
        conn = registry.get(connection)
        try:
            result = conn.query_collection(
                collection,
                query_texts=query_texts,
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
                where_document=where_document,
            )
        except Exception as exc:
            message = _embedding_error_message(exc)
            if message is not None and query_texts:
                raise ToolError(message) from exc
            raise ToolError(f"Search failed on '{connection}/{collection}': {exc}") from exc
        if result is None:
            raise ToolError(
                f"Search returned no result for collection '{collection}' "
                f"on connection '{connection}' (does it exist?)."
            )
        return _to_json({"connection": connection, "collection": collection, "results": result})

    @mcp.tool()
    def vi_get_items(
        connection: str,
        collection: str,
        ids: list[str] | None = None,
        limit: int = DEFAULT_ITEMS_PER_CALL,
        offset: int = 0,
    ) -> str:
        """Fetch items by id, or page through a collection.

        With ids, returns those items. Without ids, pages with limit
        (default 50, capped at 100) and offset — never dumps a whole
        collection in one call.
        """
        conn = registry.get(connection)
        try:
            if ids:
                result = conn.get_items(collection, ids)
                return _to_json({"connection": connection, "collection": collection, "items": result})
            limit = max(1, min(int(limit), MAX_ITEMS_PER_CALL))
            offset = max(0, int(offset))
            result = conn.get_all_items(collection, limit=limit, offset=offset)
        except Exception as exc:
            raise ToolError(f"Could not get items from '{connection}/{collection}': {exc}") from exc
        if result is None:
            raise ToolError(f"Collection '{collection}' does not exist on connection '{connection}'.")
        return _to_json(
            {
                "connection": connection,
                "collection": collection,
                "limit": limit,
                "offset": offset,
                "items": result,
            }
        )

    @mcp.tool()
    def vi_add_items(
        connection: str,
        collection: str,
        documents: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> str:
        """Add items to a collection. Documents are embedded server-side when no embeddings are given."""
        registry.require_writable("vi_add_items")
        if not documents:
            raise ToolError("vi_add_items needs at least one document.")
        conn = registry.get(connection)
        try:
            ok = conn.add_items(collection, documents, metadatas, ids, embeddings)
        except Exception as exc:
            message = _embedding_error_message(exc)
            if message is not None and not embeddings:
                raise ToolError(message) from exc
            raise ToolError(f"Add failed on '{connection}/{collection}': {exc}") from exc
        if not ok:
            raise ToolError(
                f"Add failed on '{connection}/{collection}': the provider reported failure (see server log for detail)."
            )
        return _to_json({"connection": connection, "collection": collection, "added": len(documents)})

    @mcp.tool()
    def vi_update_items(
        connection: str,
        collection: str,
        ids: list[str],
        documents: list[str] | None = None,
        metadatas: list[dict] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> str:
        """Update items by id (documents, metadatas, and/or embeddings)."""
        registry.require_writable("vi_update_items")
        if not ids:
            raise ToolError("vi_update_items needs at least one id.")
        conn = registry.get(connection)
        try:
            ok = conn.update_items(collection, ids, documents, metadatas, embeddings)
        except Exception as exc:
            raise ToolError(f"Update failed on '{connection}/{collection}': {exc}") from exc
        if not ok:
            raise ToolError(
                f"Update failed on '{connection}/{collection}': the provider "
                "reported failure (see server log for detail)."
            )
        return _to_json({"connection": connection, "collection": collection, "updated": len(ids)})

    @mcp.tool()
    def vi_delete_items(
        connection: str,
        collection: str,
        ids: list[str] | None = None,
        where: dict | None = None,
    ) -> str:
        """Delete items by id or by metadata filter. Requires ids or where — never deletes blindly."""
        registry.require_writable("vi_delete_items")
        if not ids and not where:
            raise ToolError("vi_delete_items needs ids or a where filter; refusing to delete without a selector.")
        conn = registry.get(connection)
        try:
            ok = conn.delete_items(collection, ids, where)
        except Exception as exc:
            raise ToolError(f"Delete failed on '{connection}/{collection}': {exc}") from exc
        if not ok:
            raise ToolError(
                f"Delete failed on '{connection}/{collection}': the provider "
                "reported failure (see server log for detail)."
            )
        return _to_json({"connection": connection, "collection": collection, "deleted": True})

    @mcp.tool()
    def vi_create_collection(
        connection: str,
        collection: str,
        vector_size: int,
        distance: str = "Cosine",
    ) -> str:
        """Create a collection with the given vector size and distance metric."""
        registry.require_writable("vi_create_collection")
        conn = registry.get(connection)
        try:
            ok = conn.create_collection(collection, vector_size, distance)
        except Exception as exc:
            raise ToolError(f"Create collection failed on '{connection}/{collection}': {exc}") from exc
        if not ok:
            raise ToolError(
                f"Create collection failed on '{connection}/{collection}': "
                "the provider reported failure (see server log for detail)."
            )
        return _to_json(
            {
                "connection": connection,
                "collection": collection,
                "created": True,
                "vector_size": vector_size,
                "distance": distance,
            }
        )

    @mcp.tool()
    def vi_delete_collection(connection: str, collection: str) -> str:
        """Delete a whole collection. Destructive; blocked in read-only mode."""
        registry.require_writable("vi_delete_collection")
        conn = registry.get(connection)
        try:
            ok = conn.delete_collection(collection)
        except Exception as exc:
            raise ToolError(f"Delete collection failed on '{connection}/{collection}': {exc}") from exc
        if not ok:
            raise ToolError(
                f"Delete collection failed on '{connection}/{collection}': "
                "the provider reported failure (see server log for detail)."
            )
        return _to_json({"connection": connection, "collection": collection, "deleted": True})

    @mcp.tool()
    def vi_connection_info(connection: str) -> str:
        """What the server is connected to (provider, connected state). Never includes credentials."""
        conn = registry.get(connection)
        try:
            info = conn.get_connection_info()
        except Exception as exc:
            raise ToolError(f"Could not get connection info for '{connection}': {exc}") from exc
        return _to_json({"connection": connection, "info": info})

    return mcp
