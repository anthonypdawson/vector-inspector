"""
MetadataView Refactor Example
==============================

This file shows a concrete example of refactoring MetadataView to use
AppState and service modules.

## Problem

MetadataView is 1104 lines and handles:
- Connection management
- Data loading (threading)
- Pagination
- Filtering
- Selection tracking
- Cache management
- UI updates

## Solution

Extract logic into services and use AppState for state management.

=============================================================================
BEFORE: metadata_view.py (excerpt showing problems)
=============================================================================

class MetadataView(QWidget):
    def __init__(self, connection=None, parent=None):
        super().__init__(parent)
        
        # State scattered in instance variables
        self.connection = connection
        self.current_collection = None
        self.current_database = None
        self.loaded_data = None
        self.selected_ids = []
        self.current_page = 1
        self.page_size = 100
        
        # Threading managed manually
        self.load_thread = None
        self.update_thread = None
        
        # Cache accessed directly
        self.cache_manager = get_cache_manager()
        
        self._setup_ui()
    
    def set_collection(self, database, collection):
        \"\"\"Switch to a different collection.\"\"\"
        # 50 lines of logic:
        # - Stop running threads
        # - Clear old data
        # - Check cache
        # - Start new load thread
        # - Update UI
        
        if self.load_thread and self.load_thread.isRunning():
            self.load_thread.cancel()
            self.load_thread.wait()
        
        self.current_database = database
        self.current_collection = collection
        
        # Check cache
        cache_key = (database, collection)
        cached = self.cache_manager.get(cache_key)
        if cached:
            self._on_data_loaded(cached.data)
            return
        
        # Load data
        self.loading_dialog.show_loading("Loading data...")
        
        self.load_thread = DataLoadThread(
            self.connection,
            collection,
            self.current_page,
            self.page_size
        )
        self.load_thread.finished.connect(self._on_data_loaded)
        self.load_thread.error.connect(self._on_load_error)
        self.load_thread.start()
    
    def _on_data_loaded(self, data):
        \"\"\"Handle loaded data.\"\"\"
        self.loading_dialog.hide()
        self.loaded_data = data
        
        # Cache it
        cache_key = (self.current_database, self.current_collection)
        self.cache_manager.set(cache_key, CacheEntry(data=data))
        
        # Update UI (30 lines)
        self._populate_table(data)
        self._update_pagination()
        # ...
    
    def _on_load_error(self, error):
        \"\"\"Handle load error.\"\"\"
        self.loading_dialog.hide()
        QMessageBox.critical(self, "Error", f"Failed to load data: {error}")

=============================================================================
AFTER: metadata_view.py (refactored to use AppState and services)
=============================================================================

class MetadataView(QWidget):
    \"\"\"
    Thin view for browsing collection metadata.
    
    Responsibilities:
        - Render UI
        - Subscribe to AppState changes
        - Delegate logic to services
    \"\"\"
    
    def __init__(
        self,
        app_state: AppState,
        task_runner: ThreadedTaskRunner,
        parent=None
    ):
        super().__init__(parent)
        
        # Injected dependencies
        self.app_state = app_state
        self.task_runner = task_runner
        
        # Services (no connection passed - they get it from app_state)
        self.collection_loader = CollectionLoader()
        self.metadata_loader = MetadataLoader()
        
        # UI state only
        self.loading_dialog = LoadingDialog("Loading...", self)
        
        self._setup_ui()
        self._connect_state_signals()
    
    def _connect_state_signals(self):
        \"\"\"Subscribe to AppState changes.\"\"\"
        # React to state changes declaratively
        self.app_state.provider_changed.connect(self._on_provider_changed)
        self.app_state.collection_changed.connect(self._on_collection_changed)
        self.app_state.vectors_loaded.connect(self._on_data_loaded)
        self.app_state.page_changed.connect(self._on_page_changed)
        self.app_state.loading_started.connect(self.loading_dialog.show_loading)
        self.app_state.loading_finished.connect(self.loading_dialog.hide)
        self.app_state.error_occurred.connect(self._on_error)
    
    def _on_provider_changed(self, connection):
        \"\"\"React to provider change.\"\"\"
        # Update services with new connection
        self.collection_loader.set_connection(connection)
        self.metadata_loader.set_connection(connection)
        
        # Clear UI
        self.table.setRowCount(0)
    
    def _on_collection_changed(self, collection: str):
        \"\"\"React to collection change.\"\"\"
        if not collection:
            return
        
        # Simply trigger load - state will handle the rest
        self._load_collection_data()
    
    def _load_collection_data(self):
        \"\"\"Load current collection data.\"\"\"
        collection = self.app_state.collection
        if not collection:
            return
        
        # Signal loading started
        self.app_state.start_loading("Loading collection data...")
        
        # Run load task
        self.task_runner.run_task(
            self.collection_loader.load_page,
            collection,
            self.app_state.current_page,
            self.app_state.page_size,
            on_finished=self._on_load_complete,
            on_error=self._on_load_failed,
            task_id=f"load_{collection}"
        )
    
    def _on_load_complete(self, data: dict):
        \"\"\"Handle successful load.\"\"\"
        # Update state (will trigger UI update via signal)
        self.app_state.set_data(data)
        self.app_state.finish_loading()
    
    def _on_load_failed(self, error: str):
        \"\"\"Handle load failure.\"\"\"
        self.app_state.finish_loading()
        self.app_state.emit_error("Load Error", f"Failed to load data: {error}")
    
    def _on_data_loaded(self, data: dict):
        \"\"\"React to data being loaded (from any source).\"\"\"
        # Pure UI update - no business logic
        self._populate_table(data)
        self._update_pagination_display()
    
    def _on_page_changed(self, page: int, page_size: int):
        \"\"\"React to pagination change.\"\"\"
        self._load_collection_data()
    
    def _on_error(self, title: str, message: str):
        \"\"\"React to error.\"\"\"
        QMessageBox.critical(self, title, message)
    
    def _populate_table(self, data: dict):
        \"\"\"Populate table with data (pure UI logic).\"\"\"
        # Extract just the UI rendering logic
        # No state management, no threading, no business logic
        self.table.setRowCount(len(data.get("ids", [])))
        # ... populate rows ...

=============================================================================
COMPARISON
=============================================================================

**Before:**
- 1104 lines
- Mixed UI, state, threading, caching, business logic
- Hard to test (needs Qt, mocked connections, etc.)
- Duplicated threading patterns
- Direct cache access
- Manual thread lifecycle

**After:**
- ~300 lines
- Pure UI rendering + signal handlers
- Easy to test (mock AppState and services)
- No threading code (delegated to TaskRunner)
- No cache access (handled by services/AppState)
- Declarative reactivity (subscribe to signals)

=============================================================================
MIGRATION STEPS
=============================================================================

1. **Add AppState and TaskRunner to __init__**
   - Inject as dependencies instead of creating connection/cache locally
   - Create service instances (CollectionLoader, etc.)

2. **Replace state variables with AppState subscriptions**
   - Remove: self.connection, self.current_collection, self.loaded_data, etc.
   - Add: signal connections in _connect_state_signals()

3. **Replace manual threading with TaskRunner.run_task()**
   - Remove: DataLoadThread, self.load_thread.finished.connect(...)
   - Add: self.task_runner.run_task(service_method, on_finished=..., on_error=...)

4. **Move business logic to service calls**
   - Remove: inline data loading, filtering, pagination logic
   - Add: self.collection_loader.load_page(...), self.metadata_loader.load_metadata(...)

5. **Convert imperative UI updates to reactive handlers**
   - Remove: self.loaded_data = data; self._populate_table(data)
   - Add: self.app_state.set_data(data) → triggers _on_data_loaded via signal

6. **Remove cache management from UI**
   - Remove: self.cache_manager.get/set calls
   - Caching now handled by services or AppState

7. **Test with mocks**
   - Mock AppState (emit signals to test UI reactions)
   - Mock services (return test data)
   - No need to mock Qt or connections

=============================================================================
TESTING EXAMPLES
=============================================================================

**Before (hard to test):**
```python
def test_metadata_view_loads_data():
    # Need Qt app, mocked connection, etc.
    app = QApplication([])
    mock_conn = MagicMock()
    mock_conn.get_all_items.return_value = {...}
    
    view = MetadataView(mock_conn)
    view.set_collection("db", "collection")
    
    # How do we wait for thread to finish?
    # How do we access internal state?
    # Brittle, complex test
```

**After (easy to test):**
```python
def test_metadata_view_reacts_to_data(qtbot):
    # Mock state and services
    app_state = AppState()
    task_runner = ThreadedTaskRunner()
    
    view = MetadataView(app_state, task_runner)
    qtbot.addWidget(view)
    
    # Simulate state change
    test_data = {"ids": ["1", "2"], "metadatas": [...]}</gu>
    
    with qtbot.waitSignal(app_state.vectors_loaded):
        app_state.set_data(test_data)
    
    # Verify UI updated
    assert view.table.rowCount() == 2
```

=============================================================================
BENEFITS
=============================================================================

✅ **Testability**: Services tested without Qt, UI tested with mocked state
✅ **Maintainability**: UI reduced from 1104 → ~300 lines
✅ **Consistency**: All views use same patterns (AppState, TaskRunner, services)
✅ **Decoupling**: UI doesn't know about providers, caching, threading details
✅ **Reactivity**: State changes propagate automatically via signals
✅ **Reusability**: Services shared across views
✅ **Debugging**: Clear separation of concerns, easier to trace issues

=============================================================================
NEXT VIEWS TO REFACTOR
=============================================================================

1. SearchView (841 lines) → Use SearchRunner + AppState
2. VisualizationView (519 lines) → Use ClusterRunner + AppState
3. InfoPanel (804 lines) → Use services + AppState
4. ConnectionView (617 lines) → Use ProviderManager + AppState

Each follows the same pattern shown above.
"""
