# Changelog

All notable changes to Vector Viewer will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


### Added - Phase 1 Implementation

#### Core Features
- ChromaDB connection manager with support for persistent, HTTP, and ephemeral connections
- Main application window with tabbed interface (PySide6)
- Connection configuration dialog
- Collection browser with list, select, and delete functionality
- Data browser with paginated table view
- Item addition dialog with JSON metadata support
- Item deletion (single and batch)
- Text-based similarity search interface
- Vector visualization with three dimensionality reduction methods (PCA, t-SNE, UMAP)
- 2D and 3D interactive plotting with Plotly
- Background processing for dimensionality reduction

#### User Interface
- Professional Qt-based GUI
- Main menu bar with File, Collection, and Help menus
- Toolbar with quick actions
- Status bar with connection and collection status
- Left panel for connection and collections
- Right panel with three tabs: Data Browser, Search, Visualization
- Responsive layout with splitters

#### Documentation
- Comprehensive README.md with project overview
- GETTING_STARTED.md with installation and usage instructions
- IMPLEMENTATION_SUMMARY.md with technical details
- QUICK_REFERENCE.md for common tasks
- PROJECT_STATUS.md tracking development progress
- Inline code documentation with docstrings

#### Developer Tools
- PDM project configuration
- Sample data generation script
- Run scripts for Windows (.bat) and Unix (.sh)
- Development dependencies configured (pytest, black, ruff, mypy)

### Technical Details

#### Dependencies
- chromadb >= 0.4.22
- pyside6 >= 6.6.0
- pandas >= 2.1.0
- numpy >= 1.26.0
- scikit-learn >= 1.3.0
- umap-learn >= 0.5.5
- plotly >= 5.18.0
- sentence-transformers >= 2.2.0

#### Architecture
- Modular structure with separation of concerns
- Core layer for database operations
- UI layer for interface components
- Services layer for business logic
- Signal/slot pattern for component communication

### Testing
- Manual testing of all core features
- Verified with sample dataset
- All visualization methods tested (PCA, t-SNE, UMAP)
- CRUD operations validated

## [0.2.0] - 2026-01-19

### Added - Phase 2 Complete

#### Core Features
- Advanced metadata filtering with customizable filter rules (AND/OR logic)
- Item editing: double-click to edit items directly in the data browser
- Backup and restore system for collections
- Provider abstraction layer: unified interface for ChromaDB and Qdrant
- Query builder for advanced metadata filtering
- Combined vector similarity search with metadata filters
- Query history and saved queries (initial support)
- Enhanced error handling and status reporting

#### User Interface
- Improved tabbed interface: Data Browser, Search, Visualization
- Status bar and toolbar enhancements
- More responsive and robust UI for large datasets

#### Documentation
- Updated README, implementation summary, and quick reference
- Detailed documentation for new features and usage
- Phase 2 planning and roadmap updates

#### Developer Tools
- Expanded test coverage (manual and automated tests planned)
- Improved sample data scripts for ChromaDB and Qdrant
- Refactored codebase for maintainability and extensibility

## [0.2.5] - 2026-01-22

### Fixed
- Improved text readability in Info Panel (all info text now uses high-contrast color)
- Collections list now refreshes automatically when reconnecting to a new database
- Info Panel and Collection Browser clear properly on disconnect
- Fixed ambiguous array truth value error in ChromaDB connection
- Lazy loading implemented for all heavy visualization libraries (plotly, numpy, sklearn, umap)
- Visualization tab is now lazy loaded, reducing app startup time by ~2 seconds

### Performance & Developer Experience
- Created performance optimization guide (docs/performance_optimization.md)
- Added utility for lazy imports (src/vector_inspector/utils/lazy_imports.py)
- Added and organized test scripts under test_scripts/

### Testing
- All changes validated: no syntax or lint errors, type-safe, and tested with sample data

## [0.2.7] - 2026-01-23

### Added
- **Comprehensive caching system** for database browser, search panel, and info panel
  - Cache keyed by (database_id, collection_name) for instant collection switching
  - Restores scroll position, selected items, search queries, and UI state
  - Optional toggle: View menu → Enable/Disable Caching
  - Cache automatically invalidates on data modifications and settings changes
- **Embedding model configuration UI** in Info Panel
  - Configure embedding models per collection via "Configure..." button
  - Support for sentence-transformers and CLIP multi-modal models
  - Visual indicators: green (stored in metadata), blue (user configured), orange (auto-detect)
  - Settings persisted to ~/.vector-inspector/settings.json
- **Dimension-aware embedding model selection**
  - Automatic model selection based on collection vector dimensions
  - Supports 384d (all-MiniLM-L6-v2), 512d (CLIP), 768d (all-mpnet-base-v2), 1024d, 1536d
  - Shared embedding utilities (embedding_utils.py) for all database providers
  - ChromaDB: Custom DimensionAwareEmbeddingFunction for query-time model selection
  - Qdrant: Dynamic model loading based on collection metadata or user settings

### Fixed
- **Vector dimension mismatch errors** when switching between collections with different dimensions
- Incorrect dimension-to-model mapping (768d now correctly maps to all-mpnet-base-v2, not 512d)
- ChromaDB query failures with non-default embedding dimensions
- Import errors in embedding configuration dialog
- Text readability in embedding model configuration dialog (black text on light background)
- Connection ID attribute errors in Info Panel
- Database name tracking for cache keys

### Changed
- All database providers now support dimension-aware embedding model selection
- Cache manager integrated across MetadataView, SearchView, and InfoPanel
- Settings service extended with cache_enabled toggle and collection_embedding_models storage
- Info Panel displays current embedding model configuration with color-coded status

### Performance
- Collection switching now near-instant when cached (no database queries)
- Reduced redundant metadata queries via InfoPanel caching
- Embedding models loaded on-demand and reused per collection


---

[0.1.0]: https://github.com/yourusername/vector-viewer/releases/tag/v0.1.0
