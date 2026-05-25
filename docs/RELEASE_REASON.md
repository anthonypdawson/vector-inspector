# Release Notes (0.8.1) — May 23, 2026

Full Milvus support and developer-facing type system improvements.

## Providers

- Implemented full `MilvusConnection` supporting both Milvus Lite (file-based, local) and remote Milvus server (HTTP). Milvus Lite is now available on Windows, macOS, and Linux; remote Milvus server is available on all platforms.
- Fixed provider factory to properly instantiate Milvus connections in both modes.
- Fixed connection UI to show appropriate connection type options for Milvus (Persistent/HTTP only; no in-memory ephemeral mode).

## Infrastructure & Type Safety

- Added proper return type annotation to `get_connection_class()` for better IDE support.
- Implemented `@overload` type hints for `get_connection_class()` so Pylance correctly infers constructor parameters for each provider. This enables full type checking without runtime overhead.
- Connection factory methods now have proper type validation while maintaining optional dependency architecture.

## Docs

- Added provider compatibility matrix to README — lists minimum tested library versions, install extras, and platform support for each database provider (ChromaDB, Qdrant, Pinecone, LanceDB, PgVector, Weaviate, Milvus).
- Updated README to reflect that Milvus is now fully supported with dual connection modes (Lite file-based or remote HTTP server).
- Updated ROADMAP: marked Milvus support as complete.

---
