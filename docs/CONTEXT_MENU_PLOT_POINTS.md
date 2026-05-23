# Plot Point Selection - View in Data Browser (2D Only)

## Overview

This feature enables users to select points in **2D visualization plots** and navigate directly to the corresponding row in the data browser. Selection UI is automatically shown for 2D plots and hidden for 3D plots.

## Architecture

### Components

1. **PlotPanel** (`src/vector_inspector/ui/views/visualization/plot_panel.py`)
   - Added `PlotEventBridge` class to handle JavaScript-to-Qt communication
   - Integrated QWebChannel for receiving selection events from Plotly
   - Tracks selected point and displays selection info in a label
   - Added "View Selected Point in Data Browser" button
   - Emits `view_in_data_browser` signal when button is clicked

2. **VisualizationView** (`src/vector_inspector/ui/views/visualization_view.py`)
   - Added `view_in_data_browser_requested` signal
   - Implemented `_on_view_in_data_browser()` handler
   - Forwards the request to navigate to data browser

3. **MetadataView** (`src/vector_inspector/ui/views/metadata_view.py`)
   - Added `select_item_by_id()` public method
   - Handles selection of items on current page or navigates to the correct page
   - Scrolls to and selects the target row

4. **MainWindow** (`src/vector_inspector/ui/main_window.py`)
   - Connected `view_in_data_browser_requested` signal to handler
   - Implemented `_on_view_in_data_browser_requested()` to switch tabs and select item

## User Flow

1. User navigates to the Visualization tab and generates a **2D plot** (PCA, t-SNE, UMAP)
2. User **clicks** on a point in the plot (Plotly highlights the selected point)
3. The selection is displayed below the plot: "Selected: Point #X (ID: ...)"
4. The "View Selected Point in Data Browser" button becomes enabled
5. User clicks the button to navigate to the data browser
6. **OR**: User clicks the selected point again to deselect it (toggle behavior)
7. **3D plots**: Selection UI is automatically hidden (feature not available)

**Design Rationale**: 2D plots use Plotly's native selection mechanism (`clickmode="event+select"`) which provides visual feedback through highlighted points. 3D plots have complex interaction models (rotation, pan) that interfere with reliable point selection, so the feature is disabled for 3D. Selection UI is automatically shown/hidden based on plot dimensionality.

## Technical Details

### JavaScript Integration

The feature uses Plotly's native selection mechanism combined with QWebChannel:

```javascript
// Initialize QWebChannel first
new QWebChannel(qt.webChannelTransport, function(channel) {
    plotBridge = channel.objects.plotBridge;
    var selectedPointIndex = -1;  // Track for toggle behavior
    
    // Use plotly_selected for 2D plots (works with clickmode="event+select")
    plotDiv.on('plotly_selected', function(data) {
        if (data && data.points && data.points.length > 0) {
            var point = data.points[0];
            var pointIndex = point.pointIndex;
            
            // Toggle: if clicking same point, deselect
            if (selectedPointIndex === pointIndex) {
                selectedPointIndex = -1;
                plotBridge.onPointSelected(-1, '');
                return;
            }
            
            selectedPointIndex = pointIndex;
            var pointId = extractIdFromHoverText(point.text);
            plotBridge.onPointSelected(pointIndex, pointId);
        }
    });
    
    // Handle explicit deselection
    plotDiv.on('plotly_deselect', function() {
        selectedPointIndex = -1;
        plotBridge.onPointSelected(-1, '');
    });
});
```

**Key Implementation Details:**
- **2D plots only**: Feature automatically disabled for 3D due to interaction complexity
- Plot configured with `clickmode="event+select"` to enable native Plotly selection
- Uses `plotly_selected` event (fires when point is selected with visual feedback)
- Uses `plotly_deselect` event (fires when clicking selected point again - toggle off)
- Simple toggle behavior: click to select, click again to deselect
- Selection UI hidden/shown automatically based on `reduced_data.shape[1]`
- Deselection signaled by passing `-1` as point index
- `PlotEventBridge` uses `QObject` with `@Slot` decorator
- ID extraction uses regex: `/ID:\\s*([^<\\r\\n]+)/`
- Selection cleared automatically when new plot is generated

### UI Components

**Selection Label:**
- Shows: "No point selected" (disabled state, gray/italic)
- Or: "Selected: Point #X (ID: ...)" (enabled state, green)

**View Button:**
- Text: "View Selected Point in Data Browser"  
- Initially disabled
- Enabled when a point is selected
- Switches to Data Browser tab and selects the corresponding row
- Clicking emits signal to navigate to data browser

### Qt Signal/Slot Chain

```
Plotly selection (JS)
  → PlotEventBridge.point_selected (Qt signal)
  → PlotPanel._on_point_selected() [updates label, enables button]
  
Plotly deselection (JS) or empty space click
  → PlotEventBridge.point_selected(-1, '') (Qt signal)
  → PlotPanel._on_point_selected() [clears label, disables button]
  
Button click
  → PlotPanel.view_in_data_browser (Qt signal)
  → VisualizationView._on_view_in_data_browser()
  → VisualizationView.view_in_data_browser_requested
  → MainWindow._on_view_in_data_browser_requested()
  → MetadataView.select_item_by_id()
```

### Point ID Extraction

The point ID is extracted from the hover text using a regex pattern that matches the format:
```
ID: <actual_id><br>Doc: ...
```

This relies on the existing hover text format in PlotPanel.create_plot().

## Limitations & Future Enhancements

### Current Limitations

1. **2D Only**: Feature is disabled for 3D plots due to interaction complexity (rotation/pan interfering with selection)

2. **Single Selection**: Only tracks the most recently selected point. Plotly's box/lasso select could enable multi-select in future.

3. **Cross-Collection**: Only works when the same collection is active in both views.

4. **Selection Persistence**: Selection is cleared when a new plot is generated.

### Potential Enhancements

1. **3D Plot Support**:
   - Implement custom click handling for 3D plots
   - Account for rotation/pan state to distinguish selection clicks from navigation
   - May require disabling rotation temporarily during selection mode

2. **Multi-Select via Box/Lasso**:
   - Enable Plotly's box select or lasso select tools
   - Track multiple selected points
   - Add "View All Selected in Data Browser" button
   - Show count of selected points

3. **Keyboard Shortcuts**:
   - Ctrl+G or similar to quickly navigate to data browser
   - Escape to clear selection

4. **Selection Highlighting**:
   - Use different color/style for the selected point in the plot
   - Requires custom Plotly styling

5. **Bidirectional Navigation**:
   - Select a row in data browser and highlight the point in the visualization
   - Would require reverse mapping and plot updates

6. **Quick Actions**:
   - Add more buttons: "Edit Selected", "Delete Selected", "Find Similar"
   - Context-sensitive actions based on what's selected

6. **Selection History**:
   - Keep history of recently selected points
   - Allow quick navigation through history

7. **Export Selection**:
   - Export selected point(s) data to clipboard or file

## Testing

### Manual Testing Checklist

- [ ] Click on a 2D plot point updates the selection label
- [ ] Click on a 3D plot point updates the selection label
- [ ] Selected point is visually highlighted by Plotly
- [ ] Selection label displays correct point index and ID
- [ ] Button is disabled when no point is selected
- [ ] Button is enabled after clicking a point
- [ ] Clicking empty space/background deselects the point
- [ ] Deselection clears the label and disables the button
- [ ] Button click switches to correct tab (Data Browser)
- [ ] Correct row is selected in data browser
- [ ] Row is scrolled into view if not visible
- [ ] Works with filtered data
- [ ] Works with paginated data (item not on current page)
- [ ] Works with clustered visualizations
- [ ] Clicking different points updates the selection correctly
- [ ] All Plotly interactions still work (pan, zoom, right-click zoom-out)
- [ ] Generating a new plot clears any previous selection

### Automated Testing

Unit tests should be added for:
- `PlotEventBridge.onPointSelected()` signal emission
- `PlotPanel._on_point_selected()` label and button state updates
- `PlotPanel._on_view_data_clicked()` signal emission
- `MetadataView.select_item_by_id()` with various scenarios
- Signal/slot connections in MainWindow

## Dependencies

- **PySide6.QtWebChannel**: For JavaScript-Qt communication
- **PySide6.QtWebEngineCore**: For web engine settings
- **PySide6.QtWidgets**: For button and label widgets
- Existing Plotly integration

## Performance Considerations

- JavaScript injection is minimal (~40 lines) and only executed once per plot
- QWebChannel communication is asynchronous but fast for simple messages
- Selection tracking is lightweight (just storing index and ID)
- Button state management happens in Qt (no JavaScript overhead)
- Page loading for items not on current page may take 1-2 seconds depending on database

## Advantages of This Approach

1. **Native Selection**: Uses Plotly's built-in selection mechanism with visual feedback (highlighted points)
2. **Zero Conflict**: Doesn't interfere with any Plotly interactions (pan, zoom, etc.)
3. **Clear UX**: User can see what's selected before navigating (both visually and in label)
4. **Intentional Action**: Requires explicit button click, prevents accidental navigation
5. **Easy Deselection**: Click empty space to deselect
6. **Extensible**: Easy to add more buttons for other actions
7. **Accessible**: Button can be keyboard-navigable and screen-reader friendly
8. **Reliable**: No timing issues or custom event handler conflicts
9. **Standard Behavior**: Matches user expectations for plot selection interactions

## Security

- JavaScript injection is controlled and doesn't accept user input
- Point IDs are validated against the current data set
- No external URLs or scripts are loaded

## References

- Qt WebChannel documentation: https://doc.qt.io/qt-6/qwebchannel.html
- Plotly event handling: https://plotly.com/javascript/plotlyjs-events/
