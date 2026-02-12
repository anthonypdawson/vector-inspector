# Release Notes - Telemetry & Error Handling Overhaul

## Overview
This release adds comprehensive telemetry and advanced exception handling to improve diagnostics, reliability monitoring, and user experience tracking.

## ✨ New Features

### Comprehensive Telemetry Events
Implemented telemetry tracking for all major operations:

- **Database Operations**
  - Connection attempts and results (with correlation IDs)
  - Sample database creation lifecycle (started, completed, failed)
  - Connection duration and error tracking

- **Query & Data Operations**
  - Similarity query execution with latency tracking
  - Result counts and filter usage
  - Embedding requests with batch size and provider info

- **Visualization & Analysis**
  - Dimensionality reduction performance (PCA, t-SNE, UMAP)
  - Clustering operations (HDBSCAN, KMeans, DBSCAN, OPTICS)
  - Dataset sizes and algorithm parameters

### Advanced Exception Handling
- **Global Exception Hooks**: Automatic capture of all uncaught Python exceptions
- **Qt Error Handling**: Catches Qt critical/fatal errors from slots and signals
- **Exception Decorator**: `@exception_telemetry` for manual exception tracking
- **Correlation IDs**: Every exception gets a unique UUID for tracing
- **Clean Error Messages**: Uses `traceback.format_exception_only()` for formatted output

### Privacy & Security
- **PII Protection**: Automatic hashing of sensitive data (hosts, paths) using SHA256
- **Best-Effort Design**: Telemetry failures never interrupt user workflows
- **Opt-Out Support**: Respects telemetry settings

## 🔧 Technical Improvements

### TelemetryService Refactoring
- **Auto-Population**: Service automatically adds `app_version`, `hwid`, `client_type` to all events
- **Singleton Pattern**: Module-level singleton prevents I/O overhead during cascading failures
- **Centralized Version Management**: `get_version()` called once at startup instead of per-event
- **Cleaner API**: Callers only pass event name and metadata

### Performance Optimizations
- Reduced redundant `get_version()` calls across ~15 telemetry points
- Singleton exception handler prevents repeated service initialization
- Lazy event batching for efficient network usage

## 📚 Documentation

### New Documentation
- **`docs/advanced-telemetry.md`**: Comprehensive guide covering:
  - How telemetry works
  - All implemented events with metadata schemas
  - Implementation patterns and code examples
  - Privacy guidelines and best practices
  - Quick reference for developers

### Implementation Status Tracking
- Added status table showing which events are implemented
- File references for each telemetry point
- Best practices summary

## 🐛 Bug Fixes

- **Fixed Duplicate Launch Ping**: Removed redundant `app_launch` event that was being sent twice (once before Qt init, once after window load)
- **Removed Unused Imports**: Cleaned up `QTimer` and `log_error` imports no longer needed

## 📊 Observability Improvements

### Correlation IDs
All related events (connection attempt → result, sample DB start → completion) now share correlation IDs for easy tracing in analytics.

### Success Tracking
Every operation tracks a `success` boolean and duration in milliseconds for reliability metrics.

### Error Context
Exceptions include:
- Function name where error occurred
- Exception type and clean message
- Correlation ID linking to triggering operation
- Retriable flag for transient errors

## 🎯 Developer Experience

### Simplified Telemetry Usage

**Before:**
```python
from vector_inspector import get_version
telemetry = TelemetryService()
telemetry.queue_event({
    "event_name": "query.executed",
    "app_version": get_version(),  # Repeated everywhere
    "metadata": {...}
})
```

**After:**
```python
telemetry = TelemetryService(app_version=get_version())  # Once at startup
telemetry.queue_event({
    "event_name": "query.executed",
    "metadata": {...}  # Auto-populated
})
```

### Exception Decorator
```python
@exception_telemetry(event_name="DataImportError", feature="import")
def import_data():
    # Automatic exception tracking with correlation IDs
    pass
```

## 📈 Impact

- **Better Diagnostics**: Comprehensive visibility into application health and user workflows
- **Faster Debugging**: Correlation IDs and error context speed up issue resolution
- **Performance Insights**: Latency tracking reveals optimization opportunities
- **Reliability Metrics**: Success rates help prioritize stability improvements

## 🔄 Migration Notes

No breaking changes. Telemetry is opt-in via settings and all events are best-effort (failures logged but never interrupt user workflows).

---