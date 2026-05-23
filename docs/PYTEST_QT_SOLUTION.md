# pytest-qt: The Solution to QWebEngineView Testing

## The Problem We Had

Originally, we skipped 5 tests because creating `PlotPanel` instances would hang the test suite:

```python
@pytest.mark.skip(reason="PlotPanel initialization with QWebEngineView hangs in test environment")
def test_plot_panel_on_point_selected_updates_ui():
    panel = PlotPanel()  # This would hang indefinitely
    ...
```

The issue was that `QWebEngineView` (Chromium browser engine) requires:
- Proper Qt event loop management
- Async initialization time
- Correct widget lifecycle handling

## The Solution: pytest-qt's `qtbot` Fixture

**pytest-qt** was already in our dev dependencies but we weren't using it correctly!

### What is pytest-qt?

[pytest-qt](https://pytest-qt.readthedocs.io/) is a pytest plugin that provides fixtures and helpers for testing Qt applications. Key features:

- **`qtbot` fixture**: Manages Qt event loop and widget lifecycle
- **Signal testing**: `qtbot.waitSignal()` for testing Qt signals
- **Event processing**: `qtbot.wait()` for async operations
- **Widget registration**: `qtbot.addWidget()` for proper cleanup
- **Timeout handling**: `qtbot.waitUntil()` for conditional waits

### How We Fixed It

#### Before (Hangs):
```python
def test_plot_panel_on_point_selected_updates_ui():
    panel = PlotPanel()  # Hangs here!
    panel._on_point_selected(2, "id3")
    assert "id3" in panel.selection_label.text()
```

#### After (Works!):
```python
@pytest.fixture
def plot_panel(qtbot):
    """Create a PlotPanel instance using qtbot for proper Qt widget handling."""
    from vector_inspector.ui.views.visualization.plot_panel import PlotPanel

    panel = PlotPanel()
    qtbot.addWidget(panel)  # Register for proper cleanup
    
    # Give QWebEngineView time to initialize
    qtbot.waitUntil(lambda: panel.web_view is not None, timeout=3000)
    
    return panel


def test_plot_panel_on_point_selected_updates_ui(qtbot, plot_panel):
    """Test that _on_point_selected updates selection label and button state."""
    plot_panel._on_point_selected(2, "id3")
    
    # Check UI was updated
    assert "id3" in plot_panel.selection_label.text()
    assert plot_panel.view_data_button.isEnabled() is True
```

### Key Changes

1. **Use `qtbot` fixture** in test functions
2. **Create fixture for widget** with `qtbot.addWidget()` registration
3. **Wait for initialization** with `qtbot.waitUntil()`
4. **Test signals properly** with `qtbot.waitSignal()`

### Example: Testing Signals

```python
def test_plot_panel_on_view_data_clicked_emits_signal(qtbot, plot_panel):
    """Test that button click emits signal."""
    plot_panel._selected_index = 1
    plot_panel._selected_id = "id2"

    # Use waitSignal to verify signal emission
    with qtbot.waitSignal(plot_panel.view_in_data_browser, timeout=1000) as blocker:
        plot_panel._on_view_data_clicked()

    # Verify signal arguments
    assert blocker.args == [1, "id2"]
```

## Results

### Before:
- **45 tests**: 40 passing, 5 skipped (89% runnable coverage)
- Plot panel behavior untested (only code inspection)
- Signal forwarding untested

### After Consolidation:
- **45 tests**: All passing, 0 skipped (100% coverage) ✅
- Plot panel fully tested with QWebEngineView
- All plot selection and navigation flows tested
- Signal emission and forwarding verified
- All tests in single file: [test_plot_selection.py](../tests/test_plot_selection.py)

### What Changed

1. **Removed skipped tests** - Replaced with working qtbot versions
2. **Consolidated files** - Merged test_plot_selection_with_qtbot.py into test_plot_selection.py
3. **Added qtbot fixture** - Now used for all tests that need widgets
4. **Better coverage** - Tests now cover full widget lifecycle, not just code inspection

## Running the Tests

```bash
# Run all plot selection tests (consolidated file)
pdm run pytest tests/test_plot_selection.py -v

# Run all new feature tests
pdm run pytest tests/test_timestamp_injection.py \
              tests/test_metadata_navigation.py \
              tests/test_cluster_saving.py \
              tests/test_plot_selection.py -v

# Run with coverage
pdm run pytest tests/test_plot_selection.py \
              --cov=vector_inspector.ui.views.visualization.plot_panel \
              --cov-report=html

# All 45 tests should pass
```

## When to Use qtbot

Use `qtbot` for testing:
- ✅ Qt widgets (QWidget, QLabel, QPushButton, etc.)
- ✅ Qt signals and slots
- ✅ QWebEngineView and web-based widgets
- ✅ User interactions (clicks, keyboard input)
- ✅ Widget visibility and state changes
- ✅ Async Qt operations

Don't need qtbot for:
- ❌ Pure Python logic (no Qt dependencies)
- ❌ Simple object instantiation without UI
- ❌ Code structure inspection with `inspect` module

## Best Practices

1. **Create fixtures for complex widgets**:
   ```python
   @pytest.fixture
   def my_widget(qtbot):
       widget = MyWidget()
       qtbot.addWidget(widget)
       return widget
   ```

2. **Use waitUntil for async operations**:
   ```python
   qtbot.waitUntil(lambda: widget.is_ready(), timeout=3000)
   ```

3. **Test signals with waitSignal**:
   ```python
   with qtbot.waitSignal(widget.signal_name, timeout=1000) as blocker:
       widget.trigger_action()
   assert blocker.args == [expected, args]
   ```

4. **Give operations time to complete**:
   ```python
   qtbot.wait(100)  # Wait 100ms for Qt event loop
   ```

5. **Always register widgets**:
   ```python
   qtbot.addWidget(widget)  # Ensures proper cleanup
   ```

## References

- [pytest-qt Documentation](https://pytest-qt.readthedocs.io/)
- [Qt Test Tutorial](https://doc.qt.io/qt-6/qtest-tutorial.html)
- [PySide6 Testing Guide](https://doc.qt.io/qtforpython-6/tutorials/debugging/qtest.html)

## Lessons Learned

1. **Always check existing dependencies** - pytest-qt was already installed!
2. **Read framework documentation** - pytest-qt has solutions for common Qt testing issues
3. **Don't skip tests prematurely** - There's usually a way to make them work
4. **Fixtures are powerful** - Use them to manage complex test setup
5. **Signal testing is critical** - Qt apps are signal-driven, test them properly

## The Bottom Line

**Never skip Qt widget tests again!** With `pytest-qt`'s `qtbot` fixture, even complex widgets like `QWebEngineView` can be tested reliably in CI/CD environments.
