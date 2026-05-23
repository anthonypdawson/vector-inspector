"""Milvus connection manager supporting both Milvus Lite and remote Milvus."""

import hashlib
import os
from typing import Any, Optional

from pymilvus import MilvusClient

from vector_inspector.core.connections.base_connection import VectorDBConnection
from vector_inspector.core.logging import log_info, log_tracked_error


class MilvusConnection(VectorDBConnection):
    """Manages connection to Milvus (both Lite local and remote server)."""

    def __init__(
        self,
        path: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
    ):
        """
        Initialize Milvus connection.

        Args:
            path: Path for local Milvus Lite database file (e.g., "./milvus.db")
            host: Host for remote Milvus server
            port: Port for remote Milvus server (default: 19530)
        """
        self.path = path
        self.host = host
        self.port = port or 19530
        self._client: Optional[MilvusClient] = None
        self._connected = False
        self._mode: Optional[str] = None  # 'lite' or 'remote'

    @staticmethod
    def _to_milvus_id(value: Any) -> int:
        """Convert any external ID value to Milvus-compatible int64 ID."""
        if isinstance(value, int):
            return value

        text = str(value)
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)

        # Deterministic 63-bit hash for non-numeric IDs.
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        numeric = int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)
        return numeric or 1

    def _get_vector_dimension(self, collection_name: str) -> int | None:
        """Infer vector dimension from Milvus collection schema."""
        if not self._client:
            return None
        try:
            collection_info = self._client.describe_collection(collection_name=collection_name)
            fields = collection_info.get("fields", []) if isinstance(collection_info, dict) else []
            for field in fields:
                if not isinstance(field, dict):
                    continue
                field_name = str(field.get("name", "")).lower()
                field_type = str(field.get("type", "")).lower()
                if "vector" not in field_name and "vector" not in field_type:
                    continue
                params = field.get("params", {})
                if isinstance(params, dict) and params.get("dim") is not None:
                    return int(params["dim"])
        except Exception:
            return None
        return None

    def _ensure_collection_loaded(self, collection_name: str) -> bool:
        """Ensure a collection is loaded before get/query/search operations."""
        if not self._client:
            return False
        try:
            self._client.load_collection(collection_name=collection_name)
            return True
        except Exception as e:
            log_tracked_error(
                "Milvus load_collection failed: %s",
                e,
                category="connection",
                operation="load_collection",
                provider="milvus",
                error_type=type(e).__name__,
                summary=f"collection={collection_name}",
                exc_info=True,
            )
            return False

    def connect(self) -> bool:
        """
        Establish connection to Milvus.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.path is not None:
                # Milvus Lite mode (local file-based)
                # Normalize path to absolute file path.
                # Milvus Lite expects a file path (typically ending with .db).
                raw_path = self.path.strip() if isinstance(self.path, str) else ""
                if not raw_path:
                    raw_path = "./milvus.db"

                db_path = os.path.abspath(os.path.expanduser(raw_path))

                # If a directory is provided (e.g. selected via folder picker),
                # place a default Milvus Lite DB file inside it.
                if os.path.isdir(db_path):
                    db_path = os.path.join(db_path, "milvus.db")

                # If no extension is provided, default to a .db file path.
                root, ext = os.path.splitext(db_path)
                if not ext:
                    db_path = f"{root}.db"

                self._client = MilvusClient(uri=db_path)
                self._mode = "lite"
                log_info("Connected to Milvus Lite: %s", db_path)
            elif self.host:
                # Remote Milvus server mode
                uri = f"http://{self.host}:{self.port}"
                self._client = MilvusClient(uri=uri)
                self._mode = "remote"
                log_info("Connected to Milvus server: %s", uri)
            else:
                log_tracked_error(
                    "Milvus connection failed: no path or host provided",
                    category="connection",
                    operation="connect",
                    provider="milvus",
                    error_type="ConfigError",
                )
                return False

            self._connected = True
            return True

        except Exception as e:
            log_tracked_error(
                "Milvus connection failed: %s",
                e,
                category="connection",
                operation="connect",
                provider="milvus",
                error_type=type(e).__name__,
                exc_info=True,
            )
            self._connected = False
            return False

    def disconnect(self):
        """Close connection to Milvus."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
        self._client = None
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to Milvus."""
        return self._connected

    def list_collections(self) -> list[str]:
        """Get list of all collections."""
        if not self.is_connected or not self._client:
            return []
        try:
            collections = self._client.list_collections()
            if isinstance(collections, list):
                return [str(name) for name in collections]
            if isinstance(collections, tuple):
                return [str(name) for name in collections]
            if isinstance(collections, dict):
                for key in ("collections", "data", "result", "tables"):
                    value = collections.get(key)
                    if isinstance(value, list):
                        return [str(name) for name in value]
                return []
            if collections is not None and hasattr(collections, "__iter__"):
                return [str(name) for name in collections]
            return []
        except Exception as e:
            log_tracked_error(
                "Milvus list_collections failed: %s",
                e,
                category="connection",
                operation="list_collections",
                provider="milvus",
                error_type=type(e).__name__,
                summary=f"mode={self._mode}",
            )
            return []

    def get_collection_info(self, name: str) -> dict[str, Any] | None:
        """Get collection metadata and statistics."""
        if not self.is_connected or not self._client:
            return None
        try:
            # Get collection description
            collection_info = self._client.describe_collection(collection_name=name)  # type: ignore

            # Try to get count of items
            try:
                stats = self._client.get_collection_stats(collection_name=name)
                count = stats.get("row_count", 0) if stats else 0
            except Exception:
                count = 0

            # Extract vector dimension from fields
            vector_dimension: Any = "Unknown"
            metadata_fields = []

            if collection_info and "fields" in collection_info:  # type: ignore
                for field in collection_info["fields"]:  # type: ignore
                    field_name = field.get("name", "")
                    field_type = field.get("type", "")
                    field_type_str = str(field_type).lower()
                    field_name_str = str(field_name).lower()

                    # Check if it's a vector field
                    if "vector" in field_type_str or "vector" in field_name_str:
                        # Try to extract dimension
                        params = field.get("params", {})
                        if isinstance(params, dict):
                            dim = params.get("dim")
                            if dim:
                                vector_dimension = int(dim)
                                break

                    # Collect metadata field names (non-ID, non-vector fields)
                    if field_name != "id" and "vector" not in field_type_str and "vector" not in field_name_str:
                        metadata_fields.append(field_name)

            return {
                "name": name,
                "count": int(count) if count else 0,
                "metadata_fields": metadata_fields,
                "vector_dimension": vector_dimension,
                "distance_metric": "Unknown",
            }

        except Exception as e:
            log_tracked_error(
                "Milvus get_collection_info failed: %s",
                e,
                category="connection",
                operation="get_collection_info",
                provider="milvus",
                error_type=type(e).__name__,
            )
            return None

    def create_collection(self, name: str, vector_size: int, distance: str = "Cosine") -> bool:
        """
        Create a collection.

        Args:
            name: Collection name
            vector_size: Dimension of vectors
            distance: Distance metric (Cosine, L2, IP)

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected or not self._client:
            return False

        try:
            # Map distance metric to Milvus metric_type
            metric_map = {
                "Cosine": "COSINE",
                "L2": "L2",
                "IP": "IP",
            }
            metric_type = metric_map.get(distance, "COSINE")

            # Create collection with simple API
            # Milvus auto-creates fields on first insert, so we just specify dimension
            self._client.create_collection(
                collection_name=name,
                dimension=vector_size,
                metric_type=metric_type,
                auto_id=False,
            )

            log_info("Created Milvus collection: %s (vector_size=%d)", name, vector_size)
            return True

        except Exception as e:
            log_tracked_error(
                "Milvus create_collection failed: %s",
                e,
                category="connection",
                operation="create_collection",
                provider="milvus",
                error_type=type(e).__name__,
                summary=f"collection={name} vector_size={vector_size}",
                exc_info=True,
            )
            return False

    def add_items(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict[str, Any]] | None = None,
        ids: list[str] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> bool:
        """Add items to a collection."""
        if not self.is_connected or not self._client:
            return False

        try:
            if not documents:
                return True

            vector_dimension: int | None = None
            if embeddings and embeddings[0]:
                vector_dimension = len(embeddings[0])
            else:
                vector_dimension = self._get_vector_dimension(collection_name)

            if not vector_dimension:
                log_tracked_error(
                    "Milvus add_items failed: could not infer vector dimension",
                    category="connection",
                    operation="add_items",
                    provider="milvus",
                    error_type="ConfigError",
                    summary=f"collection={collection_name}",
                )
                return False

            # Prepare data for insertion
            data = []
            for i, doc in enumerate(documents):
                item_id = self._to_milvus_id(ids[i] if ids and i < len(ids) else f"{collection_name}:{i}:{doc}")
                item = {
                    "id": item_id,
                    "text": doc,
                    "metadata": metadatas[i] if metadatas else {},
                }

                # Add embedding if provided
                if embeddings and i < len(embeddings):
                    item["vector"] = embeddings[i]
                else:
                    item["vector"] = [0.0] * vector_dimension

                data.append(item)

            # Insert data
            self._client.insert(
                collection_name=collection_name,
                data=data,
            )

            log_info("Added %d items to Milvus collection: %s", len(data), collection_name)
            return True

        except Exception as e:
            log_tracked_error(
                "Milvus add_items failed: %s",
                e,
                category="connection",
                operation="add_items",
                provider="milvus",
                error_type=type(e).__name__,
                summary=f"collection={collection_name} num_items={len(documents)}",
                exc_info=True,
            )
            return False

    def get_items(self, name: str, ids: list[str]) -> dict[str, Any]:
        """Retrieve items by IDs."""
        if not self.is_connected or not self._client:
            return {"documents": [], "metadatas": [], "ids": []}

        if not self._ensure_collection_loaded(name):
            return {"documents": [], "metadatas": [], "ids": []}

        try:
            int_ids = [self._to_milvus_id(id_val) for id_val in ids]

            results = self._client.get(
                collection_name=name,
                ids=int_ids,
            )

            documents = []
            metadatas = []
            result_ids = []

            if results:
                for item in results:
                    documents.append(item.get("text", ""))
                    metadatas.append(item.get("metadata", {}))
                    result_ids.append(str(item.get("id", "")))

            return {
                "documents": documents,
                "metadatas": metadatas,
                "ids": result_ids,
            }

        except Exception as e:
            log_tracked_error(
                "Milvus get_items failed: %s",
                e,
                category="connection",
                operation="get_items",
                provider="milvus",
                error_type=type(e).__name__,
                summary=f"collection={name} num_ids={len(ids)}",
            )
            return {"documents": [], "metadatas": [], "ids": []}

    def delete_collection(self, name: str) -> bool:
        """Delete a collection."""
        if not self.is_connected or not self._client:
            return False

        try:
            self._client.drop_collection(collection_name=name)
            log_info("Deleted Milvus collection: %s", name)
            return True

        except Exception as e:
            log_tracked_error(
                "Milvus delete_collection failed: %s",
                e,
                category="connection",
                operation="delete_collection",
                provider="milvus",
                error_type=type(e).__name__,
                summary=f"collection={name}",
                exc_info=True,
            )
            return False

    def count_collection(self, name: str) -> int:
        """Return the number of items in a collection."""
        if not self.is_connected or not self._client:
            return 0

        if not self._ensure_collection_loaded(name):
            return 0

        try:
            # Try to get count from collection stats
            stats = self._client.get_collection_stats(collection_name=name)
            if stats and "row_count" in stats:
                return int(stats["row_count"])

            # Fallback: query with limit 1 to get any result
            result = self._client.query(
                collection_name=name,
                output_fields=["id"],
                limit=1,
            )
            # If we can query, the collection exists; return 1 or 0
            return 1 if result else 0
        except Exception as e:
            log_tracked_error(
                "Milvus count_collection failed: %s",
                e,
                category="connection",
                operation="count_collection",
                provider="milvus",
                error_type=type(e).__name__,
                summary=f"collection={name}",
            )
            return 0

    def query_collection(
        self,
        collection_name: str,
        query_texts: list[str] | None = None,
        query_embeddings: list[list[float]] | None = None,
        n_results: int = 10,
        where: dict[str, Any] | None = None,
        where_document: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> dict[str, Any] | None:
        """
        Query a collection for similar vectors.

        Args:
            collection_name: Name of collection to query
            query_texts: Text queries (not used; embeddings required)
            query_embeddings: Direct embedding vectors to search
            n_results: Number of results to return
            where: Metadata filter
            where_document: Document content filter (not used)

        Returns:
            Query results dictionary
        """
        if not self.is_connected or not self._client:
            return None

        query_embedding_model: str | None = None

        # Follow the provider contract used by SearchThread: when only query_texts
        # are provided, compute embeddings with the resolved model for this collection.
        if not query_embeddings and query_texts:
            try:
                query_embeddings = self.compute_embeddings_for_documents(collection_name, query_texts)
                query_embedding_model = self.get_embedding_model(collection_name)
            except Exception as e:
                log_tracked_error(
                    "Milvus query_collection embedding generation failed: %s",
                    e,
                    category="embedding",
                    operation="query_collection",
                    provider="milvus",
                    error_type=type(e).__name__,
                    summary=f"collection={collection_name}",
                    exc_info=True,
                )
                return None

        if not query_embeddings:
            return None

        if not self._ensure_collection_loaded(collection_name):
            return None

        try:
            # Build filter expression if where clause provided
            filter_expr = None
            if where and isinstance(where, dict):
                # Simple filter support - convert dict to Milvus filter syntax
                filter_parts = []
                for key, value in where.items():
                    if isinstance(value, str):
                        filter_parts.append(f'metadata["{key}"] == "{value}"')
                    else:
                        filter_parts.append(f'metadata["{key}"] == {value}')
                filter_expr = " && ".join(filter_parts) if filter_parts else None

            search_kwargs = {
                "collection_name": collection_name,
                "data": query_embeddings,
                "limit": n_results,
                "output_fields": ["text", "metadata"],
            }
            if filter_expr:
                search_kwargs["filter"] = filter_expr

            results = self._client.search(**search_kwargs)

            # Parse results
            ids = []
            documents = []
            metadatas = []
            distances = []
            embeddings = []

            if results:
                for result_group in results:
                    for hit in result_group:
                        ids.append(str(hit.get("id", "")))
                        documents.append(hit.get("text", ""))
                        metadatas.append(hit.get("metadata", {}))
                        distances.append(float(hit.get("distance", 0.0)))
                        # Milvus doesn't return embeddings in search results

            return {
                "ids": [ids],
                "documents": [documents],
                "metadatas": [metadatas],
                "distances": [distances],
                "embeddings": [embeddings] if embeddings else None,
                "query_embedding": query_embeddings[0] if query_embeddings else None,
                "query_embedding_model": query_embedding_model,
            }

        except Exception as e:
            log_tracked_error(
                "Milvus query_collection failed: %s",
                e,
                category="connection",
                operation="query_collection",
                provider="milvus",
                error_type=type(e).__name__,
                summary=f"collection={collection_name}",
                exc_info=True,
            )
            return None

    def get_all_items(
        self,
        collection_name: str,
        limit: int | None = None,
        offset: int | None = None,
        where: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Get all items from a collection.

        Args:
            collection_name: Name of collection
            limit: Maximum number of items to return
            offset: Number of items to skip
            where: Metadata filter

        Returns:
            Dictionary with collection items
        """
        if not self.is_connected or not self._client:
            return None

        if not self._ensure_collection_loaded(collection_name):
            return None

        try:
            # Build filter expression if where clause provided
            filter_expr = None
            if where and isinstance(where, dict):
                filter_parts = []
                for key, value in where.items():
                    if isinstance(value, str):
                        filter_parts.append(f'metadata["{key}"] == "{value}"')
                    else:
                        filter_parts.append(f'metadata["{key}"] == {value}')
                filter_expr = " && ".join(filter_parts) if filter_parts else None

            # Query all items with pagination
            query_kwargs = {
                "collection_name": collection_name,
                "output_fields": ["text", "metadata", "vector"],
                "limit": limit or 10000,
                "offset": offset or 0,
            }
            if filter_expr:
                query_kwargs["filter"] = filter_expr

            results = self._client.query(**query_kwargs)

            ids = []
            documents = []
            metadatas = []
            embeddings = []

            if results:
                for item in results:
                    ids.append(str(item.get("id", "")))
                    documents.append(item.get("text", ""))
                    metadatas.append(item.get("metadata", {}))
                    if "vector" in item:
                        embeddings.append(item["vector"])

            return {
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
                "embeddings": embeddings if embeddings else [],
            }

        except Exception as e:
            log_tracked_error(
                "Milvus get_all_items failed: %s",
                e,
                category="connection",
                operation="get_all_items",
                provider="milvus",
                error_type=type(e).__name__,
                summary=f"collection={collection_name}",
                exc_info=True,
            )
            return None

    def update_items(
        self,
        collection_name: str,
        ids: list[str],
        documents: list[str] | None = None,
        metadatas: list[dict[str, Any]] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> bool:
        """
        Update items in a collection.

        Note: Milvus doesn't support direct updates; this uses upsert.
        """
        if not self.is_connected or not self._client:
            return False

        try:
            if not ids:
                return True

            # Prepare data for upsert
            data: list[dict[str, Any]] = []
            for i, item_id in enumerate(ids):
                item: dict[str, Any] = {"id": self._to_milvus_id(item_id)}

                if documents and i < len(documents):
                    item["text"] = documents[i]

                if metadatas and i < len(metadatas):
                    item["metadata"] = metadatas[i]

                if embeddings and i < len(embeddings):
                    item["vector"] = embeddings[i]

                data.append(item)

            # Upsert data
            self._client.upsert(
                collection_name=collection_name,
                data=data,
            )

            log_info("Updated %d items in Milvus collection: %s", len(data), collection_name)
            return True

        except Exception as e:
            log_tracked_error(
                "Milvus update_items failed: %s",
                e,
                category="connection",
                operation="update_items",
                provider="milvus",
                error_type=type(e).__name__,
                summary=f"collection={collection_name} num_items={len(ids)}",
                exc_info=True,
            )
            return False

    def delete_items(
        self,
        collection_name: str,
        ids: list[str] | None = None,
        where: dict[str, Any] | None = None,
    ) -> bool:
        """
        Delete items from a collection by IDs or filter.

        Args:
            collection_name: Name of collection
            ids: List of item IDs to delete
            where: Metadata filter for deletion

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected or not self._client:
            return False

        try:
            if ids:
                int_ids = [self._to_milvus_id(id_val) for id_val in ids]

                self._client.delete(
                    collection_name=collection_name,
                    ids=int_ids,
                )
                log_info("Deleted %d items from Milvus collection: %s", len(ids), collection_name)

            elif where and isinstance(where, dict):
                # Delete by filter
                filter_parts = []
                for key, value in where.items():
                    if isinstance(value, str):
                        filter_parts.append(f'metadata["{key}"] == "{value}"')
                    else:
                        filter_parts.append(f'metadata["{key}"] == {value}')
                filter_expr = " && ".join(filter_parts)

                self._client.delete(
                    collection_name=collection_name,
                    filter=filter_expr,
                )
                log_info("Deleted items from Milvus collection: %s (by filter)", collection_name)

            return True

        except Exception as e:
            log_tracked_error(
                "Milvus delete_items failed: %s",
                e,
                category="connection",
                operation="delete_items",
                provider="milvus",
                error_type=type(e).__name__,
                summary=f"collection={collection_name} num_ids={len(ids) if ids else 0}",
                exc_info=True,
            )
            return False
