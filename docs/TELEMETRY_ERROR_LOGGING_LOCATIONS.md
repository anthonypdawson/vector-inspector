# Critical Error Logging Locations for Telemetry

This document lists the most important error logging locations in the Vector Inspector codebase
that should be updated to use `log_tracked_error` with appropriate `category`, `operation`, and
`provider` kwargs for richer, privacy-safe telemetry.

> **Note:** The telemetry payload must never include raw exception messages, file paths, or user data.
> Pass only safe structured fields (`category`, `error_type`, `operation`, `provider`, `error_code`,
> `summary` capped at 100 chars). See `src/vector_inspector/core/logging.py` for the full interface.

---

## Priority 1 — Base/Core (affects all providers)

**`src/vector_inspector/core/connections/base_connection.py`** — every provider inherits from this;
embedding model failures here break all providers.
- `log_error("Failed to get embedding model: %s", e)` — `category="embedding"`, `operation="get_embedding_model"`
- `log_error("Failed to load embedding model for collection %s: %s", ...)` — `category="embedding"`, `operation="load_embedding_model"`

---

## Priority 2 — Connection/Provider Failures

All connection errors should use `provider=<provider name>` so we can see exactly which backends are failing.

**`src/vector_inspector/core/connections/chroma_connection.py`**
- `log_error("Connection failed: %s", e)` — `category="connection"`, `operation="connect"`
- `log_error("Failed to get collection: %s", e)` — `category="connection"`, `operation="get_collection"`
- `log_error("Failed to get collection info: %s", e)` — `category="connection"`, `operation="get_collection_info"`
- `log_error("Query failed: ...")` — `category="query"`, `operation="query"`
- `log_error("Failed to get items: %s", e)` — `category="data"`, `operation="get_items"`
- `log_error("Failed to compute embeddings for Chroma add_items: %s", e)` — `category="embedding"`, `operation="add_items"`
- `log_error("Failed to add items: ...")` — `category="data"`, `operation="add_items"`
- `log_error("Failed to compute embeddings for Chroma update_items: %s", e)` — `category="embedding"`, `operation="update_items"`
- `log_error("Failed to update items: %s", e)` — `category="data"`, `operation="update_items"`
- `log_error("Failed to delete items: %s", e)` — `category="data"`, `operation="delete_items"`
- `log_error("Failed to delete collection: %s", e)` — `category="data"`, `operation="delete_collection"`
- `log_error("Failed to create collection: %s", e)` — `category="data"`, `operation="create_collection"`

**`src/vector_inspector/core/connections/qdrant_connection.py`**
- `log_error("Connection failed: %s", e)` — `category="connection"`, `operation="connect"`
- `log_error("Failed to list collections: %s", e)` — `category="connection"`, `operation="list_collections"`
- `log_error("Failed to get collection info: %s", e)` — `category="connection"`, `operation="get_collection_info"`
- `log_error("Failed to resolve embedding model for %s: %s", ...)` — `category="embedding"`, `operation="resolve_embedding_model"`
- `log_error("Either query_texts or query_embeddings required")` — `category="query"`, `operation="query"`
- `log_error("Failed to embed query text: %s", e)` — `category="embedding"`, `operation="query"`
- `log_error("Query failed: %s", e)` — `category="query"`, `operation="query"`
- `log_error("Embeddings are required for Qdrant and computing them failed: %s", e)` — `category="embedding"`, `operation="add_items"`
- `log_error("Failed to add items: %s", e)` — `category="data"`, `operation="add_items"`
- `log_error("Failed to update items: %s", e)` — `category="data"`, `operation="update_items"`
- `log_error("Failed to delete items: %s", e)` — `category="data"`, `operation="delete_items"`
- `log_error("Failed to delete collection: %s", e)` — `category="data"`, `operation="delete_collection"`
- `log_error("Failed to create collection: %s", e)` — `category="data"`, `operation="create_collection"`

**`src/vector_inspector/core/connections/pinecone_connection.py`**
- `log_error("Connection failed: %s", e)` — `category="connection"`, `operation="connect"`
- `log_error("Failed to list indexes: %s", e)` — `category="connection"`, `operation="list_collections"`
- `log_error("Failed to get index: %s", e)` — `category="connection"`, `operation="get_collection_info"`
- `log_error("Failed to create index: %s", e)` — `category="data"`, `operation="create_collection"`
- `log_error("Embeddings are required for Pinecone and computing them failed: %s", e)` — `category="embedding"`, `operation="add_items"`
- `log_error("Failed to generate embeddings for query. Error: %s", e)` — `category="embedding"`, `operation="query"`
- `log_error("Query failed: ...")` — `category="query"`, `operation="query"`
- `log_error("Text query with hosted model failed: ...")` — `category="query"`, `operation="query_hosted"`
- `log_error("Failed to add items: %s", e)` — `category="data"`, `operation="add_items"`
- `log_error("Failed to get items: %s", e)` — `category="data"`, `operation="get_items"`
- `log_error("Failed to get all items: ...")` — `category="data"`, `operation="get_all_items"`
- `log_error("Failed to update items: %s", e)` — `category="data"`, `operation="update_items"`
- `log_error("Failed to delete items: %s", e)` — `category="data"`, `operation="delete_items"`
- `log_error("Failed to delete collection: %s", e)` — `category="data"`, `operation="delete_collection"`

**`src/vector_inspector/core/connections/lancedb_connection.py`**
- `log_error("LanceDB connection failed: %s", e)` — `category="connection"`, `operation="connect"`
- `log_error("LanceDB get_collection_info failed: %s", e)` — `category="connection"`, `operation="get_collection_info"`
- `log_error("LanceDB add_items failed: ...")` — `category="data"`, `operation="add_items"`
- `log_error("LanceDB get_items failed: %s", e)` — `category="data"`, `operation="get_items"`
- `log_error("LanceDB get_all_items failed: %s", e)` — `category="data"`, `operation="get_all_items"`
- `log_error("LanceDB query_collection failed: %s", e)` — `category="query"`, `operation="query"`
- `log_error("LanceDB search failed: %s", e_search)` — `category="query"`, `operation="search"`
- `log_error("Failed to compute embeddings for query_texts: %s", e)` — `category="embedding"`, `operation="query"`
- `log_error("LanceDB update_items failed: %s", e)` — `category="data"`, `operation="update_items"`
- `log_error("LanceDB delete_items failed: %s", e)` — `category="data"`, `operation="delete_items"`
- `log_error("LanceDB delete_collection failed: %s", e)` — `category="data"`, `operation="delete_collection"`

**`src/vector_inspector/core/connections/pgvector_connection.py`**
- `log_error("Connection failed: %s", e)` — `category="connection"`, `operation="connect"`
- `log_error("Failed to list collections: %s", e)` — `category="connection"`, `operation="list_collections"`
- `log_error("Failed to list databases: %s", e)` — `category="connection"`, `operation="list_databases"`
- `log_error("Failed to get collection info: %s", e)` — `category="connection"`, `operation="get_collection_info"`
- `log_error("Failed to create collection: %s", e)` — `category="data"`, `operation="create_collection"`
- `log_error("Failed to compute embeddings on add: %s", e)` — `category="embedding"`, `operation="add_items"`
- `log_error("Failed to add items: %s", e)` — `category="data"`, `operation="add_items"`
- `log_error("Failed to compute query embeddings: %s", e)` — `category="embedding"`, `operation="query"`
- `log_error("Query failed: %s", e)` — `category="query"`, `operation="query"`
- `log_error("Failed to compute embeddings on update: %s", e)` — `category="embedding"`, `operation="update_items"`
- `log_error("Failed to update items: %s", e)` — `category="data"`, `operation="update_items"`
- `log_error("Failed to delete items: %s", e)` — `category="data"`, `operation="delete_items"`
- `log_error("Failed to delete collection: %s", e)` — `category="data"`, `operation="delete_collection"`

**`src/vector_inspector/core/connections/weaviate_connection.py`**
- `log_error("Connection failed: %s", e)` — `category="connection"`, `operation="connect"`
- `log_error("Failed to list collections: %s", e)` — `category="connection"`, `operation="list_collections"`
- `log_error("Failed to get collection info: %s", e)` — `category="connection"`, `operation="get_collection_info"`
- `log_error("Failed to create collection: %s", e)` — `category="data"`, `operation="create_collection"`
- `log_error("Embeddings are required for Weaviate and computing them failed: %s", e)` — `category="embedding"`, `operation="add_items"`
- `log_error("Failed to add items: %s", e)` — `category="data"`, `operation="add_items"`
- `log_error("Failed to get items: %s", e)` — `category="data"`, `operation="get_items"`
- `log_error("Failed to get all items: %s", e)` — `category="data"`, `operation="get_all_items"`
- `log_error("Failed to embed query texts: %s", e)` — `category="embedding"`, `operation="query"`
- `log_error("Query failed: %s", e)` — `category="query"`, `operation="query"`
- `log_error("Failed to update items: %s", e)` — `category="data"`, `operation="update_items"`
- `log_error("Failed to delete items: %s", e)` — `category="data"`, `operation="delete_items"`
- `log_error("Failed to delete collection: %s", e)` — `category="data"`, `operation="delete_collection"`

---

## Priority 3 — Core Services

**`src/vector_inspector/services/data_loaders.py`** — central data loading path for all views.
- `log_error("Failed to load collection data: {e}")` — `category="data"`, `operation="load_collection_data"`
- `log_error("Failed to load vectors: {e}")` — `category="data"`, `operation="load_vectors"`
- `log_error("Failed to load metadata: {e}")` — `category="data"`, `operation="load_metadata"`
- `log_error("Failed to get collection count: {e}")` — `category="data"`, `operation="get_collection_count"`

**`src/vector_inspector/services/search_runner.py`** — central search path for all providers.
- `log_error("Search failed: {e}")` — `category="query"`, `operation="search"`
- `log_error("Search by ID failed: {e}")` — `category="query"`, `operation="search_by_id"`

**`src/vector_inspector/services/collection_service.py`** — central collection management.
- `log_error(f"Failed to create collection '{collection_name}'")` — `category="data"`, `operation="create_collection"`
- `log_error(error_msg)` (add/update/delete item failures) — `category="data"`, `operation="<relevant op>"`

**`src/vector_inspector/services/task_runner.py`** — catches all unhandled background task exceptions.
- `log_error("TaskRunner encountered an exception", exc_info=True)` — `category="task_runner"`, `operation="run_task"`

**`src/vector_inspector/services/visualization_service.py`**
- `log_error("Dimensionality reduction failed: %s", e)` — `category="visualization"`, `operation="dimensionality_reduction"`
- `log_error("Unknown method: %s", method)` — `category="visualization"`, `operation="dimensionality_reduction"`

---

## Priority 4 — LLM Providers

**`src/vector_inspector/core/llm_providers/runtime_manager.py`**
- `log_error("LLM provider selection failed: %s", exc)` — `category="llm"`, `operation="select_provider"`

**`src/vector_inspector/core/llm_providers/ollama_provider.py`**
- `log_error("Ollama chat failed: %s", exc)` — `category="llm"`, `operation="chat"`, `provider="ollama"`
- `log_error("Ollama stream failed: %s", exc)` — `category="llm"`, `operation="stream"`, `provider="ollama"`
- `log_error("Ollama list_models failed: %s", exc)` — `category="llm"`, `operation="list_models"`, `provider="ollama"`

**`src/vector_inspector/core/llm_providers/openai_compatible_provider.py`**
- `log_error("OpenAI-compatible chat HTTP %s: ...")` — `category="llm"`, `operation="chat"`, `provider="openai_compatible"`
- `log_error("OpenAI-compatible stream failed: %s", exc)` — `category="llm"`, `operation="stream"`, `provider="openai_compatible"`
- `log_error("Failed to fetch model list from %s: %s", ...)` — `category="llm"`, `operation="list_models"`, `provider="openai_compatible"`

**`src/vector_inspector/core/llm_providers/llama_cpp_provider.py`**
- `log_error("Failed to load llama-cpp model: %s", exc)` — `category="llm"`, `operation="load_model"`, `provider="llama_cpp"`
- `log_error("llama-cpp generate_messages failed: %s", exc)` — `category="llm"`, `operation="generate"`, `provider="llama_cpp"`

---

## Priority 5 — Data Integrity (Backup/Restore & Ingestion)

**`src/vector_inspector/services/backup_restore_service.py`** — data loss risk.
- `log_error("Backup failed: %s", e)` — `category="backup"`, `operation="backup"`
- `log_error("Restore failed: %s", e)` — `category="backup"`, `operation="restore"`
- `log_error("Failed to recompute embeddings: %s", e)` — `category="embedding"`, `operation="restore"`
- `log_error("Failed to restore collection %s", ...)` — `category="backup"`, `operation="restore"`

**`src/vector_inspector/services/file_ingestion_service.py`**
- `log_error("Document ingestion failed for %s: %s", ...)` — `category="ingestion"`, `operation="ingest_document"`
- `log_error("Image ingestion failed for %s: ...")` — `category="ingestion"`, `operation="ingest_image"`
- `log_error("Document final flush failed (%s): ...")` — `category="ingestion"`, `operation="flush"`

**`src/vector_inspector/services/import_export_service.py`**
- `log_error("Export to JSON failed: %s", e)` — `category="export"`, `operation="export_json"`
- `log_error("Export to CSV failed: %s", e)` — `category="export"`, `operation="export_csv"`
- `log_error("Export to Parquet failed: %s", e)` — `category="export"`, `operation="export_parquet"`
- `log_error("Import from JSON failed: %s", e)` — `category="import"`, `operation="import_json"`
- `log_error("Import from CSV failed: %s", e)` — `category="import"`, `operation="import_csv"`
- `log_error("Import from Parquet failed: %s", e)` — `category="import"`, `operation="import_parquet"`

---

## Priority 6 — Application & Infrastructure

**`src/vector_inspector/services/settings_service.py`**
- `log_error("Failed to load settings: %s", e)` — `category="settings"`, `operation="load_settings"`
- `log_error("Failed to save settings: %s", e)` — `category="settings"`, `operation="save_settings"`

**`src/vector_inspector/services/credential_service.py`**
- `log_error("Failed to store credentials: %s", e)` — `category="credentials"`, `operation="store"`
- `log_error("Failed to retrieve credentials: %s", e)` — `category="credentials"`, `operation="retrieve"`

**`src/vector_inspector/services/provider_manager.py`**
- `log_error(f"Failed to list collections: {e}")` — `category="connection"`, `operation="list_collections"`
- `log_error(f"Failed to get collection info: {e}")` — `category="connection"`, `operation="get_collection_info"`

**`src/vector_inspector/main.py`**
- `log_error("[Startup] Failed to apply global stylesheet: ...")` — `category="startup"`
- `log_error("LLM console failed to open: %s", ...)` — `category="startup"`, `operation="open_llm_console"`

**`src/vector_inspector/extensions/__init__.py`**
- `log_error("Context menu handler error: %s", e)` — `category="extension"`, `operation="context_menu_handler"`
- `log_error("Settings panel handler error: %s", e)` — `category="extension"`, `operation="settings_panel_handler"`

**`src/vector_inspector/tools/llm_console.py`**
- `log_error("LLM console: provider factory returned None ...")` — `category="llm"`, `operation="create_provider"`
- `log_error("LLM console: could not create provider — %s", exc)` — `category="llm"`, `operation="create_provider"`
- `log_error("LLM console request failed: %s", exc)` — `category="llm"`, `operation="request"`

---

## Do NOT convert to log_tracked_error

These errors in the telemetry service itself must stay as `log_error` to avoid recursive calls:
- All `log_error(f"[Telemetry] ...")` calls in `src/vector_inspector/services/telemetry_service.py`

---

## Example Conversion

Within any `VectorDBConnection` subclass, `provider` can be derived dynamically from
`type(self).__name__` — the same pattern already used in `base_connection.py` — so it
never needs to be hardcoded.

```python
# Before
log_error("Connection failed: %s", e)

# After (inside a VectorDBConnection method)
log_tracked_error(
    "Connection failed: %s", e,
    category="connection",
    operation="connect",
    provider=type(self).__name__.replace("Connection", "").lower(),  # e.g. "chromadb"
    error_type=type(e).__name__,
)
```

For LLM providers the same pattern works using `self.__class__.__name__`, e.g.:

```python
# Before
log_error("Ollama chat failed: %s", exc)

# After (inside an LLM provider method)
log_tracked_error(
    "Ollama chat failed: %s", exc,
    category="llm",
    operation="chat",
    provider=self.__class__.__name__,  # e.g. "OllamaProvider"
    error_type=type(exc).__name__,
)
```

For services that don't have a `self` provider reference, pass `provider` only if it is
available from context (e.g. passed as an argument or accessible via `app_state`):

```python
# Before
log_error("Search failed: %s", exc)

# After (inside a service with a provider argument)
log_tracked_error(
    "Search failed: %s", exc,
    category="query",
    operation="search",
    provider=type(connection).__name__.replace("Connection", "").lower() if connection else None,
    error_type=type(exc).__name__,
)
```
