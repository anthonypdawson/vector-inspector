# Clustering Feature Migration

## Overview
Clustering features have been moved from vector-studio into vector-inspector with feature gating to allow basic clustering in the free version while reserving advanced options for Vector Studio.

## Architecture

### Feature Flagging System
- **Location**: `src/vector_inspector/core/feature_flags.py`
- **Purpose**: Detects whether Vector Studio is active and enables/disables advanced features accordingly
- **Key Functions**:
  - `are_advanced_features_enabled()`: Returns True if Vector Studio is active
  - `enable_advanced_features()`: Called by Vector Studio to activate advanced features
  - `get_feature_tooltip()`: Provides tooltip text for disabled premium features

### Clustering Core Logic
- **Location**: `src/vector_inspector/core/clustering.py`
- **Purpose**: Implements clustering algorithms (HDBSCAN, KMeans, DBSCAN, OPTICS)
- **Key Function**: `run_clustering(embeddings, algorithm, params)` - Runs clustering and returns labels

### Clustering UI
- **Location**: `src/vector_inspector/ui/views/visualization_view.py`
- **Features**:
  - Algorithm selection dropdown (HDBSCAN, KMeans, DBSCAN, OPTICS)
  - Basic parameters for each algorithm (always visible and enabled)
  - "Run Clustering" button
  - Status label showing cluster count and noise points
  - "Color by Clusters" checkbox to toggle cluster visualization
  - "Advanced Settings" toggle (disabled in vector-inspector, enabled in Vector Studio)

## Behavior

### In Vector Inspector (Free)
- Basic clustering algorithms are available
- Users can select algorithm and adjust basic parameters
- Advanced settings toggle is visible but disabled with tooltip: "Advanced clustering settings available in Vector Studio"
- Full clustering functionality works with default/basic parameters

### In Vector Studio (Premium)
- All basic clustering features work as in vector-inspector
- Advanced settings toggle is enabled
- (Future) Advanced parameters for fine-tuning clustering behavior

## Implementation Details

### Vector Inspector Changes
1. Added `feature_flags.py` for feature detection
2. Added `clustering.py` with core clustering algorithms
3. Modified `visualization_view.py`:
   - Added `ClusteringThread` for background clustering
   - Added clustering UI controls in `_setup_ui()`
   - Added `_run_clustering()` method
   - Modified `_create_plot()` to use cluster colors when enabled
   - Modified `set_collection()` to reset cluster state

### Vector Studio Changes
1. Modified `__main__.py` to call `enable_advanced_features()` on startup
2. Simplified `features/clustering.py` to a stub (functionality moved to vector-inspector)

## Migration Benefits
1. **Code Consolidation**: Clustering logic is now in one place (vector-inspector)
2. **Reduced Duplication**: No need to maintain separate implementations
3. **Clear Feature Gating**: Advanced features are cleanly separated via feature flags
4. **User Visibility**: Free users can see advanced options but understand they need Vector Studio to enable them
5. **Easy Testing**: Both basic and advanced features can be tested in vector-inspector

## Future Enhancements
- Add advanced parameter controls to vector-inspector UI (hidden/disabled by default, enabled in Vector Studio)
- Add more clustering algorithms (Spectral, Agglomerative, etc.)
- Add cluster analysis tools (silhouette scores, cluster quality metrics)
- Add cluster export functionality
