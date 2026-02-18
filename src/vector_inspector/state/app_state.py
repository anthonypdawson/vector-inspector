"""Centralized application state with signal-based reactivity."""

from typing import Any, Optional

from PySide6.QtCore import QObject, Signal

from vector_inspector.core.connection_manager import ConnectionInstance


class AppState(QObject):
    """
    Centralized application state with signal-based change propagation.

    All major application state lives here. UI components subscribe to signals
    to react to state changes declaratively rather than imperatively managing state.

    Signals:
        provider_changed: Emitted when the active provider/connection changes
        collection_changed: Emitted when the active collection changes
        vectors_loaded: Emitted when vectors are loaded (vectors_dict, metadata)
        metadata_loaded: Emitted when metadata is loaded (metadata_dict)
        selection_changed: Emitted when selected item(s) change (item_ids)
        clusters_updated: Emitted when clustering results change (labels, algorithm)
        search_results_updated: Emitted when search results change (results_dict)
        filters_changed: Emitted when active filters change (filters_dict)
        page_changed: Emitted when pagination state changes (page, page_size)
    """

    # Signals for state changes
    provider_changed = Signal(object)  # ConnectionInstance or None
    collection_changed = Signal(str)  # collection_name
    database_changed = Signal(str)  # database_name
    vectors_loaded = Signal(dict)  # full data dict
    metadata_loaded = Signal(dict)  # metadata dict
    selection_changed = Signal(list)  # list of selected item IDs
    clusters_updated = Signal(object, str)  # (labels, algorithm)
    search_results_updated = Signal(dict)  # search results dict
    filters_changed = Signal(dict)  # filter specification
    page_changed = Signal(int, int)  # (page_number, page_size)
    loading_started = Signal(str)  # loading message
    loading_finished = Signal()  # loading complete
    error_occurred = Signal(str, str)  # (title, message)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        # Provider and collection state
        self._provider: Optional[ConnectionInstance] = None
        self._collection: Optional[str] = None
        self._database: Optional[str] = None

        # Data state
        self._vectors: Optional[dict[str, Any]] = None
        self._metadata: Optional[dict[str, Any]] = None
        self._full_data: Optional[dict[str, Any]] = None  # Combined data

        # Selection state
        self._selected_ids: list[str] = []

        # Clustering state
        self._cluster_labels: Optional[Any] = None
        self._cluster_algorithm: Optional[str] = None

        # Search state
        self._search_results: Optional[dict[str, Any]] = None
        self._search_query: Optional[str] = None

        # Filter state
        self._active_filters: dict[str, Any] = {}

        # Pagination state
        self._current_page: int = 1
        self._page_size: int = 100

        # Loading state
        self._is_loading: bool = False
        self._loading_message: str = ""

    # Provider property
    @property
    def provider(self) -> Optional[ConnectionInstance]:
        """Get the current provider/connection."""
        return self._provider

    @provider.setter
    def provider(self, value: Optional[ConnectionInstance]) -> None:
        """Set the current provider/connection."""
        if self._provider != value:
            self._provider = value
            self.provider_changed.emit(value)
            # Reset dependent state
            self._collection = None
            self._database = None
            self._clear_data()

    # Collection property
    @property
    def collection(self) -> Optional[str]:
        """Get the current collection."""
        return self._collection

    @collection.setter
    def collection(self, value: Optional[str]) -> None:
        """Set the current collection."""
        if self._collection != value:
            self._collection = value
            self.collection_changed.emit(value or "")
            self._clear_data()

    # Database property
    @property
    def database(self) -> Optional[str]:
        """Get the current database name."""
        return self._database

    @database.setter
    def database(self, value: Optional[str]) -> None:
        """Set the current database name."""
        if self._database != value:
            self._database = value
            self.database_changed.emit(value or "")

    # Data properties
    @property
    def vectors(self) -> Optional[dict[str, Any]]:
        """Get loaded vectors."""
        return self._vectors

    @property
    def metadata(self) -> Optional[dict[str, Any]]:
        """Get loaded metadata."""
        return self._metadata

    @property
    def full_data(self) -> Optional[dict[str, Any]]:
        """Get full loaded data (vectors + metadata)."""
        return self._full_data

    def set_data(self, data: dict[str, Any]) -> None:
        """
        Set loaded data (vectors and metadata).

        Args:
            data: Dictionary with 'ids', 'embeddings', 'metadatas', 'documents'
        """
        self._full_data = data
        self._vectors = {"ids": data.get("ids", []), "embeddings": data.get("embeddings", [])}
        self._metadata = {
            "ids": data.get("ids", []),
            "metadatas": data.get("metadatas", []),
            "documents": data.get("documents", []),
        }
        self.vectors_loaded.emit(data)

    def set_metadata(self, metadata: dict[str, Any]) -> None:
        """Set metadata only."""
        self._metadata = metadata
        self.metadata_loaded.emit(metadata)

    # Selection properties
    @property
    def selected_ids(self) -> list[str]:
        """Get selected item IDs."""
        return self._selected_ids

    @selected_ids.setter
    def selected_ids(self, value: list[str]) -> None:
        """Set selected item IDs."""
        if self._selected_ids != value:
            self._selected_ids = value
            self.selection_changed.emit(value)

    # Clustering properties
    @property
    def cluster_labels(self) -> Optional[Any]:
        """Get cluster labels."""
        return self._cluster_labels

    @property
    def cluster_algorithm(self) -> Optional[str]:
        """Get clustering algorithm used."""
        return self._cluster_algorithm

    def set_clusters(self, labels: Any, algorithm: str) -> None:
        """Set clustering results."""
        self._cluster_labels = labels
        self._cluster_algorithm = algorithm
        self.clusters_updated.emit(labels, algorithm)

    def clear_clusters(self) -> None:
        """Clear clustering results."""
        if self._cluster_labels is not None or self._cluster_algorithm is not None:
            self._cluster_labels = None
            self._cluster_algorithm = None
            self.clusters_updated.emit(None, "")

    # Search properties
    @property
    def search_results(self) -> Optional[dict[str, Any]]:
        """Get search results."""
        return self._search_results

    @property
    def search_query(self) -> Optional[str]:
        """Get current search query."""
        return self._search_query

    def set_search_results(self, results: dict[str, Any], query: Optional[str] = None) -> None:
        """Set search results."""
        self._search_results = results
        if query is not None:
            self._search_query = query
        self.search_results_updated.emit(results)

    def clear_search_results(self) -> None:
        """Clear search results."""
        if self._search_results is not None:
            self._search_results = None
            self._search_query = None
            self.search_results_updated.emit({})

    # Filter properties
    @property
    def active_filters(self) -> dict[str, Any]:
        """Get active filters."""
        return self._active_filters

    @active_filters.setter
    def active_filters(self, value: dict[str, Any]) -> None:
        """Set active filters."""
        if self._active_filters != value:
            self._active_filters = value
            self.filters_changed.emit(value)

    # Pagination properties
    @property
    def current_page(self) -> int:
        """Get current page number."""
        return self._current_page

    @property
    def page_size(self) -> int:
        """Get page size."""
        return self._page_size

    def set_page(self, page: int, page_size: Optional[int] = None) -> None:
        """Set pagination state."""
        changed = False
        if self._current_page != page:
            self._current_page = page
            changed = True
        if page_size is not None and self._page_size != page_size:
            self._page_size = page_size
            changed = True
        if changed:
            self.page_changed.emit(self._current_page, self._page_size)

    # Loading state
    @property
    def is_loading(self) -> bool:
        """Check if currently loading."""
        return self._is_loading

    def start_loading(self, message: str = "Loading...") -> None:
        """Signal loading started."""
        self._is_loading = True
        self._loading_message = message
        self.loading_started.emit(message)

    def finish_loading(self) -> None:
        """Signal loading finished."""
        self._is_loading = False
        self._loading_message = ""
        self.loading_finished.emit()

    def emit_error(self, title: str, message: str) -> None:
        """Emit an error."""
        self.error_occurred.emit(title, message)

    # Helper methods
    def _clear_data(self) -> None:
        """Clear all data (called when provider/collection changes)."""
        self._vectors = None
        self._metadata = None
        self._full_data = None
        self._selected_ids = []
        self._cluster_labels = None
        self._cluster_algorithm = None
        self._search_results = None
        self._search_query = None
        self._active_filters = {}
        self._current_page = 1

    def get_cache_key(self) -> Optional[tuple[str, str]]:
        """Get cache key for current provider/collection."""
        if self._database and self._collection:
            return (self._database, self._collection)
        return None
