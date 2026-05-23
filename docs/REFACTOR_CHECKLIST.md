"""
UI Refactor Migration Checklist
================================

Use this checklist for each UI file you refactor to use AppState and services.

## Pre-Migration

- [ ] Read the current file and identify:
  - [ ] State variables (connection, collection, data, etc.)
  - [ ] Threading code (QThread subclasses, thread management)
  - [ ] Business logic (data loading, filtering, calculations)
  - [ ] Provider-specific code
  - [ ] Cache access
  - [ ] Direct service calls
- [ ] List all dependencies the view needs (connection, services)
- [ ] Identify which signals the view should subscribe to
- [ ] Estimate new line count (should be ~30% of original)

## Step 1: Update __init__ Signature

- [ ] Add `app_state: AppState` parameter
- [ ] Add `task_runner: ThreadedTaskRunner` parameter
- [ ] Keep `parent` parameter
- [ ] Remove `connection` parameter (get from app_state)
- [ ] Store app_state and task_runner as instance variables

```python
# Before
def __init__(self, connection=None, parent=None):
    super().__init__(parent)
    self.connection = connection
    # ...

# After
def __init__(self, app_state: AppState, task_runner: ThreadedTaskRunner, parent=None):
    super().__init__(parent)
    self.app_state = app_state
    self.task_runner = task_runner
    # ...
```

## Step 2: Create Service Instances

- [ ] Identify which services this view needs:
  - [ ] ProviderManager (for provider operations)
  - [ ] CollectionLoader (for loading collection data)
  - [ ] VectorLoader (for loading vectors)
  - [ ] MetadataLoader (for loading metadata)
  - [ ] SearchRunner (for search operations)
  - [ ] ClusterRunner (for clustering)
- [ ] Create service instances in __init__
- [ ] Don't pass connection to services (they'll get it via set_connection later)

```python
# Services this view uses
self.collection_loader = CollectionLoader()
self.search_runner = SearchRunner()
```

## Step 3: Remove State Variables

Remove these instance variables (use AppState instead):

- [ ] `self.connection` → `app_state.provider`
- [ ] `self.current_collection` → `app_state.collection`
- [ ] `self.current_database` → `app_state.database`
- [ ] `self.loaded_data` → `app_state.full_data`
- [ ] `self.selected_ids` → `app_state.selected_ids`
- [ ] `self.cluster_labels` → `app_state.cluster_labels`
- [ ] `self.search_results` → `app_state.search_results`
- [ ] `self.active_filters` → `app_state.active_filters`
- [ ] `self.current_page` → `app_state.current_page`
- [ ] Any other state variables

## Step 4: Connect to AppState Signals

- [ ] Create `_connect_state_signals()` method
- [ ] Call it from `__init__` after `_setup_ui()`
- [ ] Connect to relevant signals:

```python
def _connect_state_signals(self):
    \"\"\"Subscribe to state changes.\"\"\"
    self.app_state.provider_changed.connect(self._on_provider_changed)
    self.app_state.collection_changed.connect(self._on_collection_changed)
    self.app_state.vectors_loaded.connect(self._on_data_loaded)
    self.app_state.selection_changed.connect(self._on_selection_changed)
    self.app_state.clusters_updated.connect(self._on_clusters_updated)
    self.app_state.search_results_updated.connect(self._on_search_updated)
    self.app_state.filters_changed.connect(self._on_filters_changed)
    self.app_state.page_changed.connect(self._on_page_changed)
    self.app_state.loading_started.connect(self._on_loading_started)
    self.app_state.loading_finished.connect(self._on_loading_finished)
    self.app_state.error_occurred.connect(self._on_error)
```

## Step 5: Remove Custom Thread Classes

For each QThread subclass:

- [ ] Identify what function it runs
- [ ] Remove the thread class definition
- [ ] Remove instance variables like `self.load_thread`
- [ ] Remove thread.finished.connect() calls
- [ ] Remove thread.error.connect() calls
- [ ] Remove thread.start() calls
- [ ] Remove thread.wait() or thread.cancel() calls

## Step 6: Replace Threading with TaskRunner.run_task()

For each place where you started a thread:

- [ ] Replace with `task_runner.run_task()` call
- [ ] Pass the service method as first argument
- [ ] Pass method arguments
- [ ] Use `on_finished` callback for success
- [ ] Use `on_error` callback for errors
- [ ] Optionally use `task_id` for cancellation

```python
# Before
self.load_thread = DataLoadThread(self.connection, collection)
self.load_thread.finished.connect(self._on_data_loaded)
self.load_thread.error.connect(self._on_error)
self.load_thread.start()

# After
self.task_runner.run_task(
    self.collection_loader.load_all,
    collection,
    on_finished=self._on_load_complete,
    on_error=self._on_load_failed,
    task_id=f"load_{collection}"
)
```

## Step 7: Extract Business Logic to Service Calls

For each chunk of business logic (>10 lines):

- [ ] Identify what it does (load data, search, cluster, filter, etc.)
- [ ] Find the appropriate service method
- [ ] Replace inline logic with service call
- [ ] Move complex logic to a new service method if needed

```python
# Before (40 lines of inline search logic)
def _perform_search(self):
    try:
        results = self.connection.query(...)
        # normalize...
        # calculate similarities...
        # format...
        self._update_results(results)
    except Exception as e:
        # error handling...

# After (delegate to service)
def _perform_search(self):
    query = self.query_input.text()
    self.task_runner.run_task(
        self.search_runner.search,
        self.app_state.collection,
        query,
        n_results=10,
        on_finished=self._on_search_complete,
        on_error=self._on_search_failed
    )

def _on_search_complete(self, results: dict):
    self.app_state.set_search_results(results)
```

## Step 8: Make UI Updates Reactive

For each place where you update UI after business logic:

- [ ] Split into two methods:
  1. Task initiation (calls service)
  2. UI update (reacts to state signal)
- [ ] Task method updates AppState
- [ ] UI update method subscribes to AppState signal
- [ ] Keep UI update methods pure (no state changes, no business logic)

```python
# Before (imperative)
def load_data(self):
    data = self.connection.get_all_items(...)
    self.loaded_data = data
    self._populate_table(data)
    self._update_status()

# After (reactive)
def load_data(self):
    \"\"\"Initiate data load.\"\"\"
    self.task_runner.run_task(
        self.collection_loader.load_all,
        self.app_state.collection,
        on_finished=self._on_load_complete
    )

def _on_load_complete(self, data: dict):
    \"\"\"Update state (triggers UI update via signal).\"\"\"
    self.app_state.set_data(data)

def _on_data_loaded(self, data: dict):
    \"\"\"React to data being loaded (pure UI update).\"\"\"
    self._populate_table(data)
    self._update_status()
```

## Step 9: Remove Cache Access

- [ ] Remove `self.cache_manager` instance variable
- [ ] Remove `cache_manager.get()` calls
- [ ] Remove `cache_manager.set()` calls
- [ ] Remove `cache_manager.invalidate()` calls
- [ ] Let services or AppState handle caching if needed

## Step 10: Remove Provider-Specific Code

- [ ] Identify provider-specific logic (Qdrant, Chroma, Weaviate quirks)
- [ ] Move to ProviderManager.normalize_item() or normalize_batch()
- [ ] Call provider_manager.normalize_item() in service, not UI
- [ ] UI should only see normalized data

```python
# Before (in UI)
if provider_type == "qdrant":
    # convert string floats to floats
    for key, val in metadata.items():
        if isinstance(val, str):
            try:
                metadata[key] = float(val)
            except: pass

# After (in ProviderManager)
# ... already handled by service
```

## Step 11: Update Signal Handlers

For each signal handler:

- [ ] Rename to match convention: `_on_<event>`
- [ ] Accept correct parameters from AppState signals
- [ ] Keep logic minimal (delegate to services if needed)
- [ ] Update UI only (no state changes)

```python
def _on_provider_changed(self, connection: ConnectionInstance):
    \"\"\"React to provider change.\"\"\"
    # Update services
    self.collection_loader.set_connection(connection)
    self.search_runner.set_connection(connection)
    
    # Clear UI
    self.table.setRowCount(0)

def _on_collection_changed(self, collection: str):
    \"\"\"React to collection change.\"\"\"
    if collection:
        self.load_data()

def _on_data_loaded(self, data: dict):
    \"\"\"React to data load (pure UI update).\"\"\"
    self._populate_table(data)
```

## Step 12: Add Loading/Error Handling

- [ ] Use AppState signals for loading states:
  - `app_state.start_loading("message")`
  - `app_state.finish_loading()`
  - `app_state.emit_error("title", "message")`
- [ ] Subscribe to `loading_started` and `loading_finished`
- [ ] Subscribe to `error_occurred`
- [ ] Show/hide loading dialog reactively

```python
def _on_loading_started(self, message: str):
    self.loading_dialog.show_loading(message)

def _on_loading_finished(self):
    self.loading_dialog.hide()

def _on_error(self, title: str, message: str):
    QMessageBox.critical(self, title, message)
```

## Step 13: Update Tests

- [ ] Remove mocked connections from tests
- [ ] Mock AppState instead
- [ ] Mock services instead of provider methods
- [ ] Use qtbot.waitSignal() to wait for AppState signals
- [ ] Test UI reactions to state changes
- [ ] Test service calls independently

```python
def test_view_reacts_to_data(qtbot):
    app_state = AppState()
    task_runner = ThreadedTaskRunner()
    view = MyView(app_state, task_runner)
    
    test_data = {"ids": ["1", "2"], ...}
    
    with qtbot.waitSignal(app_state.vectors_loaded):
        app_state.set_data(test_data)
    
    assert view.table.rowCount() == 2
```

## Step 14: Verify and Clean Up

- [ ] Remove unused imports (threading, cache_manager, etc.)
- [ ] Remove dead code (old state management)
- [ ] Check line count (should be ~30% of original)
- [ ] Run linter and fix issues
- [ ] Run tests and verify they pass
- [ ] Test manually in the app

## Step 15: Document

- [ ] Add docstring explaining view's purpose
- [ ] Document which services it uses
- [ ] Document which AppState signals it subscribes to
- [ ] Add usage example in docstring

```python
class MetadataView(QWidget):
    \"\"\"
    View for browsing collection metadata.
    
    Services:
        - CollectionLoader: Loads paginated data
        - MetadataLoader: Loads metadata details
    
    AppState subscriptions:
        - collection_changed: Loads new collection data
        - vectors_loaded: Updates table display
        - page_changed: Reloads current page
    
    Usage:
        app_state = AppState()
        task_runner = ThreadedTaskRunner()
        view = MetadataView(app_state, task_runner)
    \"\"\"
```

## Final Checklist

- [ ] View uses AppState for all state
- [ ] View uses TaskRunner for all background tasks
- [ ] View delegates business logic to services
- [ ] View has no provider-specific code
- [ ] View has no cache access
- [ ] View has no custom QThread classes
- [ ] View subscribes to AppState signals
- [ ] View methods are pure UI updates
- [ ] Tests updated and passing
- [ ] Line count reduced significantly
- [ ] Code is readable and maintainable
- [ ] Documentation added

## Common Pitfalls

❌ **Forgetting to call set_connection() on services when provider changes**
✅ Subscribe to provider_changed and update services

❌ **Mixing state updates with UI updates in one method**
✅ Separate: task → update state → signal → UI update

❌ **Storing duplicate state in view and AppState**
✅ Only use AppState; view has no state variables

❌ **Calling AppState setters from signal handlers**
✅ Tasks/services update state; handlers only update UI

❌ **Not using task_id for cancellable tasks**
✅ Use task_id when you need to cancel (e.g., on view close)

❌ **Accessing AppState._private variables directly**
✅ Use public properties and methods only

❌ **Creating AppState in each view**
✅ Pass shared AppState instance to all views

❌ **Testing UI with real services**
✅ Mock services; test UI reactions to AppState changes independently

## Success Metrics

After refactoring, the view should be:

✅ **~30% of original line count**
✅ **No QThread subclasses**
✅ **No state variables (uses AppState)**
✅ **No business logic (delegates to services)**
✅ **No provider-specific code**
✅ **Testable without mocking Qt**
✅ **Declarative (reacts to signals)**
✅ **Single responsibility (UI rendering only)**

## Need Help?

- Check [UI_REFACTOR.md](./UI_REFACTOR.md) for architecture overview
- Check [METADATA_VIEW_REFACTOR_EXAMPLE.md](./METADATA_VIEW_REFACTOR_EXAMPLE.md) for concrete example
- Check service docstrings for API documentation
- Check AppState docstrings for signal documentation
"""
