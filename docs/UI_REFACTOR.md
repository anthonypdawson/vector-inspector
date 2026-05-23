"""
UI Refactor Documentation
==========================

This document describes the UI refactor that extracts business logic from UI components
into testable service classes and introduces centralized state management.

## Architecture Overview

### Before Refactor:
- UI components (1000+ lines) contained business logic, data loading, threading
- State scattered across multiple widgets
- Direct provider SDK calls from UI
- Provider quirks handled in UI code
- 200-300 lines of threading code duplicated

### After Refactor:
- UI components are thin views (~300 lines)
- Business logic in service modules
- Centralized AppState with signal-based reactivity
- ThreadedTaskRunner handles all background tasks
- Provider quirks normalized in ProviderManager
- Services are testable without Qt dependency

## Core Components

### 1. AppState (vector_inspector/state/app_state.py)

Centralized application state with Qt signals for change propagation.

**State Managed:**
- Provider/connection
- Collection and database
- Loaded vectors and metadata
- Selection state
- Clustering results
- Search results
- Filters
- Pagination

**Usage Example:**

```python
from vector_inspector.state import AppState

# Create state instance (typically one per application)
app_state = AppState()

# Subscribe to changes
app_state.collection_changed.connect(on_collection_changed)
app_state.vectors_loaded.connect(on_vectors_loaded)

# Update state (emits signals automatically)
app_state.collection = "my_collection"
app_state.set_data(loaded_data)
```

### 2. ThreadedTaskRunner (vector_inspector/services/task_runner.py)

Unified background task execution with automatic cleanup and cancellation.

**Features:**
- Single API for all async operations
- Automatic thread lifecycle management
- Progress reporting
- Error handling
- Cancellation support

**Usage Example:**

```python
from vector_inspector.services import ThreadedTaskRunner

runner = ThreadedTaskRunner()

# Run a task
task_id = runner.run_task(
    load_collection_data,  # function to execute
    collection_name,       # arguments
    on_finished=handle_success,
    on_error=handle_error,
    on_progress=handle_progress
)

# Cancel if needed
runner.cancel_task(task_id)
```

### 3. Service Modules

#### ProviderManager
Manages provider connections and normalizes provider-specific quirks.

```python
from vector_inspector.services import ProviderManager

manager = ProviderManager(connection)

# Get collections
collections = manager.get_collections()

# Normalize data (handles Qdrant float strings, Weaviate nesting, etc.)
normalized = manager.normalize_item(raw_item, provider_type)
```

#### CollectionLoader
Loads collection data with pagination and filtering.

```python
from vector_inspector.services import CollectionLoader

loader = CollectionLoader(connection)

# Load page of data
data = loader.load_page(collection, page=1, page_size=100)

# Get total count
count = loader.get_count(collection)
```

#### VectorLoader
Loads and validates vector embeddings.

```python
from vector_inspector.services import VectorLoader

loader = VectorLoader(connection)

# Load vectors (automatically filters invalid embeddings)
vectors = loader.load_vectors(collection, sample_size=1000)
```

#### MetadataLoader
Loads metadata and documents.

```python
from vector_inspector.services import MetadataLoader

loader = MetadataLoader(connection)

# Load metadata
metadata = loader.load_metadata(collection, item_ids=["id1", "id2"])

# Get all metadata fields
fields = loader.get_metadata_fields(data)
```

#### SearchRunner
Executes similarity searches.

```python
from vector_inspector.services import SearchRunner

searcher = SearchRunner(connection)

# Search by text
results = searcher.search(collection, "query text", n_results=10)

# Search by ID
results = searcher.search_by_id(collection, "item_id", n_results=10)

# Calculate similarity from distance
similarity = searcher.calculate_similarity(0.1, metric="cosine")
```

#### ClusterRunner
Executes clustering algorithms.

```python
from vector_inspector.services import ClusterRunner

clusterer = ClusterRunner()

# Run clustering
labels, algorithm = clusterer.cluster(embeddings, "kmeans", {"n_clusters": 5})

# Get statistics
stats = clusterer.get_cluster_stats(labels)

# Format summary
summary = clusterer.format_summary(labels, algorithm)
```

## Migration Guide

### Step 1: Refactor UI Component to Use AppState

**Before:**
```python
class MetadataView(QWidget):
    def __init__(self):
        self.connection = None
        self.current_collection = None
        self.loaded_data = None
    
    def set_collection(self, collection):
        self.current_collection = collection
        self._load_data()
```

**After:**
```python
class MetadataView(QWidget):
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        
        # Subscribe to state changes
        self.app_state.collection_changed.connect(self._on_collection_changed)
        self.app_state.vectors_loaded.connect(self._on_vectors_loaded)
    
    def _on_collection_changed(self, collection: str):
        """React to collection change."""
        self._load_data()  # Trigger load
        
    def _on_vectors_loaded(self, data: dict):
        """React to data load completion."""
        self._update_table(data)
```

### Step 2: Replace Inline Logic with Service Calls

**Before:**
```python
def _perform_search(self):
    # 40 lines of search logic
    try:
        results = self.connection.query(
            collection_name=self.collection,
            query_texts=[query],
            n_results=10
        )
        # normalize results...
        # calculate similarities...
        # update UI...
    except Exception as e:
        # error handling...
```

**After:**
```python
def _perform_search(self):
    query = self.query_input.toPlainText()
    
    self.task_runner.run_task(
        self.search_runner.search,
        self.app_state.collection,
        query,
        n_results=10,
        on_finished=self._on_search_complete,
        on_error=self._on_search_error
    )

def _on_search_complete(self, results: dict):
    self.app_state.set_search_results(results)
```

### Step 3: Replace Custom Threads with TaskRunner

**Before:**
```python
class DataLoadThread(QThread):
    finished = Signal(dict)
    error = Signal(str)
    
    def run(self):
        try:
            data = self.connection.get_all_items(...)
            self.finished.emit(data)
        except Exception as e:
            self.error.emit(str(e))

# In UI:
self.thread = DataLoadThread(...)
self.thread.finished.connect(self._on_loaded)
self.thread.start()
```

**After:**
```python
# In UI:
self.task_runner.run_task(
    self.collection_loader.load_all,
    collection_name,
    on_finished=self._on_loaded,
    on_error=self._on_error
)
```

### Step 4: Extract Panel Logic into Dedicated Classes

**Before (in main view):**
```python
# 200 lines of clustering panel setup and logic
def _setup_clustering_panel(self):
    # create widgets...
    # connect signals...
    # implement logic...
```

**After:**
```python
# In view:
def _setup_clustering_panel(self):
    self.clustering_panel = ClusteringPanel(self.app_state)
    layout.addWidget(self.clustering_panel)

# In ClusteringPanel class (separate file):
class ClusteringPanel(QWidget):
    def __init__(self, app_state: AppState):
        super().__init__()
        self.app_state = app_state
        self.cluster_runner = ClusterRunner()
        self._setup_ui()
```

## Testing

Services are now testable without Qt:

```python
def test_collection_loader():
    # Mock connection
    mock_conn = MagicMock()
    mock_conn.get_all_items.return_value = {...}
    
    # Test service
    loader = CollectionLoader(mock_conn)
    data = loader.load_all("test_collection")
    
    assert data is not None
    assert "ids" in data
```

AppState can be tested with signals:

```python
def test_app_state_signals(qtbot):
    state = AppState()
    
    with qtbot.waitSignal(state.collection_changed):
        state.collection = "new_collection"
    
    assert state.collection == "new_collection"
```

## Benefits

1. **Testability**: Services can be unit tested without Qt
2. **Maintainability**: UI components reduced from 1000+ to ~300 lines
3. **Consistency**: Single implementation of threading, errors, loading
4. **Decoupling**: UI doesn't know about provider quirks
5. **Reactivity**: State changes automatically propagate via signals
6. **Reusability**: Services can be shared across views
7. **Debugging**: Easier to trace issues (logic not buried in UI)

## Migration Checklist

For each large UI file:

- [ ] Replace local state with AppState
- [ ] Subscribe to AppState signals
- [ ] Extract data loading to service calls
- [ ] Replace custom threads with TaskRunner
- [ ] Move provider-specific logic to ProviderManager
- [ ] Extract complex panels into separate classes
- [ ] Add unit tests for extracted services
- [ ] Update integration tests to use AppState

## File Structure

```
src/vector_inspector/
  state/
    __init__.py
    app_state.py              # Centralized state
  services/
    __init__.py
    task_runner.py             # Background task execution
    provider_manager.py        # Provider abstraction
    data_loaders.py            # Collection/Vector/Metadata loaders
    search_runner.py           # Search execution
    cluster_runner.py          # Clustering execution
  ui/
    views/
      metadata_view.py         # Thin view using AppState + services
      search_view.py           # Thin view using AppState + services
      visualization_view.py    # Thin view using AppState + services
```

## Next Steps

1. Migrate MetadataView to use AppState and services
2. Migrate SearchView to use AppState and SearchRunner
3. Migrate VisualizationView to use AppState and ClusterRunner
4. Extract remaining panels (ClusteringPanel, PlotPanel, etc.)
5. Add comprehensive unit tests for all services
6. Update integration tests
7. Document UI component patterns
8. Remove old threading code

## Questions?

See the source code docstrings for detailed API documentation.
Each service class has comprehensive documentation and usage examples.
"""
