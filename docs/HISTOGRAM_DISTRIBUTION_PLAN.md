# Histogram / Distribution Visualization Plan

Purpose
- Add a discoverable, well-scoped histogram/distribution panel to help users inspect vector distributions (norms and per-dimension values) and compare collections or subsets.

Design summary
- UI: Add a new "Distributions" tab inside the existing Visualization view. Keep global sample controls (Sample size / Use all data) above the tabs so sampling is consistent across Visualization and Distributions.
- Panel: `HistogramPanel` that renders Plotly histograms into a QWebEngineView using the same pattern as `PlotPanel`.
- Metrics: support `Norm` (vector magnitudes) and `Dimension N` (value from a selected embedding dimension). Provide bin-count and density (density vs count) toggles.
- Comparison: support overlaying two histograms (primary collection vs comparison collection or subset) with semi-transparent traces and a toggle to turn comparison on/off.

Implementation steps (MVP -> optional)
1. Create `HistogramPanel` (MVP)
   - Location: `src/vector_inspector/ui/views/visualization/histogram_panel.py`.
   - Responsibilities:
     - Accept `current_data` (dict with `embeddings`, `ids`, etc.) and `sample_size` semantics identical to `VisualizationView`.
     - Compute metric array using `numpy` and `has_embedding()` to filter invalid embeddings.
     - Build a `plotly.graph_objects` figure with a `go.Histogram` trace (bins configurable) and render via `fig.to_html()` into a `QWebEngineView`.
     - Provide simple UI: metric selector (`Norm` or `Dimension`), dimension index input (spinbox), bin count (spinbox), density toggle, and a "Compare" button (disabled in MVP if not implementing comparison immediately).
     - Expose `get_current_html()` to allow saving/export (reuse pattern from `PlotPanel`).

2. Integrate as a new tab in `VisualizationView` (MVP integration)
   - Replace current vertical layout that contains `ClusteringPanel`, `DRPanel`, and `PlotPanel` with a `QTabWidget`.
   - Tab 1: "Visualization" — contains existing DR + Plot panels (unchanged behavior).
   - Tab 2: "Distributions" — contains `HistogramPanel` and shares the global sample controls and loading dialog.
   - Wire `VisualizationDataLoadThread` success handler to pass `current_data` into `HistogramPanel` (or let the panel request data from `VisualizationView` via a public method).

3. Reuse existing services & patterns
   - Use `vector_inspector.utils.lazy_imports.get_plotly()` to lazily import Plotly.
   - Use `VisualizationDataLoadThread` for loading data with the same sampling logic.
   - Use `has_embedding()` from `vector_inspector.utils` to filter invalid embeddings.
   - Use `LoadingDialog` while computing metrics/plotting for large samples.

4. Implement comparison overlay (optional / follow-up)
   - Add UI to pick a second collection (simple popup or reuse collection selector). Validate embedding dimension compatibility.
   - Load the second collection using `VisualizationDataLoadThread` (with same sample rules) and overlay histograms with `opacity=0.6` and `barmode='overlay'`.
   - Handle mismatched embedding dims by showing an explanatory message and disabling dimension selection for comparison when incompatible.

5. Tests and edge cases
   - Unit tests for metric computation (`norms`, `dimension selection`, filtering with `has_embedding`).
   - GUI tests (pytest-qt) to validate panel loads, plot HTML generation, and basic interaction.
   - Edge cases: empty embeddings, variable-length embeddings, very large collections (ensure sampling prevents UI freezes), missing second collection.

Files to create/modify
- New: `src/vector_inspector/ui/views/visualization/histogram_panel.py` (primary implementation)
- Modify: `src/vector_inspector/ui/views/visualization_view.py` (replace/extend layout to include `QTabWidget` with Distributions tab)
- No changes required to `src/vector_inspector/ui/views/visualization/plot_panel.py` aside from reuse patterns.

Estimated effort
- MVP (single-collection histograms for norms + per-dimension, new tab, basic controls): ~4–8 hours.
- Comparison overlay & collection selector: additional ~4–8 hours.
- Tests + docs + polish: +4–12 hours depending on detail level.

UX notes and tradeoffs
- Tabs keep the main DR scatter UI uncluttered and keep distribution tools discoverable.
- Alternative: side-by-side split provides immediate visual comparison but consumes horizontal space and adds complexity; recommend tab for first pass.
- Keep sample controls global to avoid duplicate logic and to ensure consistent sampling behavior across views.

Next steps
- If approved, implement the `HistogramPanel` scaffold, integrate it into `VisualizationView` as a new tab, and add basic unit tests. Optionally follow up with comparison UI.

— end of plan
