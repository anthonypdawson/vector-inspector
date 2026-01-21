# Vector Inspector Roadmap

## Phase 1: Foundation (MVP)
- [x] Connection to ChromaDB
- [x] Basic metadata browsing and filtering
- [x] Simple similarity search interface
- [x] 2D vector visualization (PCA/t-SNE)
- [x] Basic CRUD operations

## Phase 2: Core Features
- [x] Metadata filtering (advanced filtering, combine with search)
- [x] Item editing (update metadata and documents)
- [x] Import/export (CSV, JSON, Parquet, backup/restore)
- [x] Provider abstraction layer (unified interface for all supported vector DBs)
- [x] Qdrant support (basic/experimental, free)

## Phase 3: UX & Professional Polish
- [ ] **Unified Information Panel** (new "Info" tab as default view)
- [ ] Database and collection metadata display
- [ ] Connection health and version information
- [ ] Schema visualization and index configuration display

## Phase 4: Data Migration & Pinecone
- [ ] Pinecone support
- [ ] Cross-database migration (dedicated controls for migrating collections between providers)

## Phase 5: Modular/Plugin System & Hybrid Model
- [ ] Implement modular/plugin system for feature extensions
- [ ] Migrate paid/advanced features to commercial modules
- [ ] Add licensing/access control for commercial features

## Phase 6: Provider Expansion (All Free)
- [ ] Weaviate support
- [ ] Milvus support
- [ ] FAISS (local files) support
- [ ] pgvector (PostgreSQL extension) support
- [ ] Elasticsearch with vector search support

> **All providers are available in the free tier.** Pro features focus on advanced workflows, not basic provider access.

## Phase 6A: Advanced Usability & Visualization
- [ ] Advanced query builder (free)
- [ ] 3D visualization (free)
- [ ] Embedding model integration (basic, free)
- [ ] Query history (recent queries, free)
- [ ] Saved queries (named, persistent, Pro)
- [ ] Metadata Type Detection & Rich Media Preview (free)

## Phase 6B: Analytical & Comparison Tools
- [ ] Model Comparison Mode (paid)
- [ ] Cluster Explorer (paid)
- [ ] Embedding Inspector (paid)
- [ ] Embedding Provenance Graph (paid)

## Phase 6C: Temporal & Cross-Collection Analytics
- [ ] Semantic Drift Timeline (paid)
- [ ] Cross-Collection Similarity (paid)

## Phase 6D: Experimental & Power Features
- [ ] Vector Surgery (Pro)
- [ ] Custom plugin system (Pro)
- [ ] Team collaboration features (Pro)
- [ ] Parquet import/export (Pro)
- [ ] Bulk import/export pipelines (Pro)
- [ ] Advanced embedding workflows (Pro)
  - Large batch processing
  - Multiple model selection
  - GPU acceleration
- [ ] Advanced provider features (Pro)
  - Cloud authentication flows
  - Hybrid search
  - Performance profiling
  - Index optimization tools


## Phase 7: Enterprise Features (Pro)
- [ ] Multi-user support with auth
- [ ] Audit logging
- [ ] Advanced security features
- [ ] Custom reporting and dashboards
- [ ] API for programmatic access (FastAPI backend)
- [ ] Cross-collection queries and analytics
- [ ] Team workspaces and sharing

> **Enterprise features enhance collaboration and scale.** All core functionality remains free.
