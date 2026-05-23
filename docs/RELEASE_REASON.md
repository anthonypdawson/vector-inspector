# Release Notes (0.8.1) — May 23, 2026

Minor documentation and usability improvements.

## Providers

- Implemented full `MilvusConnection` supporting both Milvus Lite (file-based, local) and remote Milvus server (HTTP). Milvus Lite is now available on Windows, macOS, and Linux; remote Milvus server is available on all platforms.

## Docs

- Added provider compatibility matrix to README — lists minimum tested library versions, install extras, and platform support for each database provider (ChromaDB, Qdrant, Pinecone, LanceDB, PgVector, Weaviate, Milvus).
- Updated README to reflect that Milvus is now fully supported with dual connection modes (Lite file-based or remote HTTP server).
- Updated ROADMAP: marked Milvus support as complete.

---
