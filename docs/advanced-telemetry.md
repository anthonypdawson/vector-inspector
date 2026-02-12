# Advanced Telemetry

This document describes recommended telemetry events, common properties, privacy guidance, and integration notes for Vector Inspector.

## Goals
- Capture meaningful, low-volume events (errors, flows) at 100%.
- Sample high-volume events (queries, embeddings) to control cost.
- Preserve user privacy: never send raw PII or secrets.

## How telemetry works

`TelemetryService` is initialized once with the app version and automatically populates these fields for every event:
- `hwid` — persistent client UUID (retrieved from settings)
- `event_name` — the event identifier (e.g., `db.connection_result`)
- `app_version` — application version (set once during service initialization)
- `client_type` — always `"vector-inspector"`
- `metadata` — your event-specific data goes here

The backend automatically adds a `created_at` timestamp when storing events.

**Key benefit**: You don't need to call `get_version()` or pass `app_version` with every telemetry call. The service handles this automatically.

## Implementation Status

The following table shows which telemetry events have been implemented:

| Event Name | Status | File |
|------------|--------|------|
| `db.connection_attempt` | ✅ Implemented | `ui/controllers/connection_controller.py` |
| `db.connection_result` | ✅ Implemented | `ui/controllers/connection_controller.py` |
| `sample_db.create_started` | ✅ Implemented | `ui/workers/collection_worker.py` |
| `sample_db.create_completed` | ✅ Implemented | `ui/workers/collection_worker.py` |
| `sample_db.create_failed` | ✅ Implemented | `ui/workers/collection_worker.py` |
| `query.executed` | ✅ Implemented | `ui/views/search_view.py` |
| `embedding.request` | ✅ Implemented | `core/connections/base_connection.py` |
| `clustering.run` | ✅ Implemented | `core/clustering.py` |
| `visualization.generated` | ✅ Implemented | `services/visualization_service.py` |
| `UncaughtException` | ✅ Auto-implemented | `utils/exception_handler.py` |
| `QtError` | ✅ Auto-implemented | `utils/exception_handler.py` |
| `session.start` | ⚠️ Not yet | N/A |
| `session.end` | ⚠️ Not yet | N/A |
| `feature.toggled` | ⚠️ Not yet | N/A |

## Recommended events

All event-specific data should be placed in the `metadata` dict. Below are suggested events with their metadata fields:

### Database Operations

**`db.connection_attempt`** — When the app starts a connection attempt
- Metadata: `db_type`, `host_hash`, `connection_id`, `correlation_id`

**`db.connection_result`** — After connection attempt finishes
- Metadata: `success` (bool), `db_type`, `error_code`, `error_class`, `duration_ms`, `correlation_id`

**`sample_db.create_started`** — Start of creating a sample DB
- Metadata: `db_type`, `sample_db_id`, `estimated_rows`, `correlation_id`

**`sample_db.create_completed`** — Sample DB creation finished
- Metadata: `success` (bool), `db_type`, `sample_db_id`, `rows_created`, `duration_ms`, `correlation_id`

**`sample_db.create_failed`** — Sample DB creation failed
- Metadata: `db_type`, `sample_db_id`, `error_code`, `retriable` (bool), `correlation_id`

### Query & Embedding Operations

**`query.executed`** — User executed a query
- Metadata: `query_type` (`vector`/`metadata`), `db_type`, `result_count`, `latency_ms`, `filters_applied` (summary), `correlation_id`

**`embedding.request`** — Embeddings requested from a provider
- Metadata: `provider`, `model_id`, `batch_size`, `latency_ms`, `error_code` (if any), `correlation_id`

### Visualization & Analysis

**`clustering.run`** — Clustering executed
- Metadata: `algorithm`, `params` (size-limited summary), `dataset_size`, `duration_ms`, `success`, `correlation_id`

**`visualization.generated`** — Dimensionality reduction performed
- Metadata: `method` (`umap`/`pca`/`tsne`), `dims`, `points_rendered`, `duration_ms`, `correlation_id`

### Session & Features

**`session.start`** / **`session.end`** — User session boundaries
- Metadata: `session_id`, `os`, `duration_ms` (end only)

**`feature.toggled`** — User toggles an experimental feature
- Metadata: `feature_name`, `new_value` (bool)

### Errors

**`UncaughtException`** — Automatically sent by global exception handler
- Metadata: `message`, `traceback`, `exception_type`, `correlation_id`

**`QtError`** — Qt-specific critical/fatal errors
- Metadata: `message`, `msg_type`, `file`, `line`, `function`, `correlation_id`

Note: The exception handlers automatically populate error telemetry with correlation IDs. For manual error reporting, use `TelemetryService.send_error_event()`.

## Common metadata fields

While each event has specific metadata, these fields are commonly used across multiple events:

- `correlation_id` — UUID to tie related events in a flow (e.g., connection → sample creation)
- `session_id` — User session identifier for grouping activity
- `db_type` — Database type (e.g., `chroma`, `qdrant`, `pinecone`)
- `duration_ms` — How long an operation took
- `success` — Boolean indicating operation success
- `error_code` — Machine-readable error code (when `success` is false)
- `error_class` — Exception class name for errors
- `os` — Operating system info (e.g., `Windows-10`, `Darwin-23.1.0`)

**Important:** Never put `hwid`, `event_name`, `app_version`, or `client_type` in metadata — these are automatically set by `TelemetryService`.

## Privacy & PII guidance

- Never send raw hostnames, connection strings, usernames, API keys, or file paths.
- Hash or truncate identifiers: e.g. `host_hash = sha256(host + salt)` and store only a stable prefix.
- Sanitize error messages: remove substrings that match secret patterns (keys, tokens, IPs).
- Keep stack traces out of telemetry; send an `error_hash` and sanitized class/message instead.
- Respect an opt-out flag: provide `settings.telemetry_enabled` and respect OS privacy controls.

## Sampling & retention

- High-volume events (e.g., `query.executed`, `embedding.request`) default sample: 1–5%.
- Keep errors and crashes at 100%.
- Retention guidance: raw event store 7–30 days; aggregated metrics and dashboards 90+ days.
- Record effective `sampling_rate` in event metadata when sampled.

## Integration notes

- Create a `correlation_id` at the start of user flows (UI action) and pass it to background tasks.
- Use a project-wide salt for `user_id_hash` to allow grouping without exposing identity.
- Add feature flagging for verbose telemetry (e.g., dev builds or consented analytics).

## Automatic exception handling

The application automatically captures and reports all uncaught exceptions to telemetry via global exception hooks set up in `main.py`:

- **`sys.excepthook`**: Catches all unhandled Python exceptions
- **Qt message handler**: Catches Qt-specific critical/fatal errors from slots and signals

These are configured in `src/vector_inspector/utils/exception_handler.py` and initialized at application startup.

**Key features:**
- **Correlation IDs**: Each exception gets a unique UUID to track related events
- **Clean error messages**: Uses `traceback.format_exception_only()` for formatted exception messages
- **Singleton pattern**: Uses a module-level singleton `TelemetryService` to avoid I/O overhead during cascading failures
- **Best-effort**: Telemetry failures never interrupt exception propagation

## Decorator for caught exceptions

For caught exceptions in business logic that you want to report to telemetry, use the `@exception_telemetry` decorator:

```python
from vector_inspector.utils.exception_handler import exception_telemetry

@exception_telemetry(event_name="DataImportError", feature="data_import")
def import_data(file_path):
    # This will catch exceptions, send to telemetry, and re-raise
    # ...your code...
    pass
```

The decorator:
- Catches the exception
- Sends it to telemetry with context (function name, exception type, custom fields, correlation ID)
- Re-raises the original exception so normal error handling continues
- Is best-effort: telemetry failures won't break your application
- Uses the singleton TelemetryService (no need to pass app_version)

**When to use the decorator:**
- Critical user flows where you want visibility into failures
- Background tasks where exceptions might be silently logged
- Operations with external services (DB connections, API calls, file I/O)

**When NOT to use:**
- Top-level exception handlers that already call `TelemetryService.send_error_event()`
- Functions where exceptions are expected and handled gracefully
- Hot paths or performance-critical loops

## Usage example

### Emitting a custom event

```python
from vector_inspector.services.telemetry_service import TelemetryService
import uuid
import time

# Create service instance (pass app_version once during initialization)
from vector_inspector import get_version
telemetry = TelemetryService(app_version=get_version())

# Generate correlation ID for this operation
correlation_id = str(uuid.uuid4())

# Record operation start
start_time = time.time()
telemetry.queue_event({
    "event_name": "sample_db.create_started",
    "metadata": {
        "db_type": "chroma",
        "sample_db_id": "example-1",
        "estimated_rows": 1000,
        "correlation_id": correlation_id
    }
})

try:
    # ... perform operation ...
    rows_created = 1234
    
    # Record success
    telemetry.queue_event({
        "event_name": "sample_db.create_completed",
        "metadata": {
            "db_type": "chroma",
            "sample_db_id": "example-1",
            "rows_created": rows_created,
            "duration_ms": int((time.time() - start_time) * 1000),
            "success": True,
            "correlation_id": correlation_id
        }
    })
except Exception as e:
    # Record failure
    telemetry.send_error_event(
        message=str(e),
        tb=traceback.format_exc(),
        event_name="sample_db.create_failed",
        extra={
            "db_type": "chroma",
            "sample_db_id": "example-1",
            "correlation_id": correlation_id,
            "retriable": True
        }
    )

# Send batch to server
telemetry.send_batch()
```

### Example payload (as sent to backend)

```json
{
  "hwid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "event_name": "sample_db.create_completed",
  "app_version": "1.2.3",
  "client_type": "vector-inspector",
  "metadata": {
    "db_type": "chroma",
    "sample_db_id": "example-1",
    "rows_created": 1234,
    "duration_ms": 5423,
    "success": true,
    "correlation_id": "f9e8d7c6-b5a4-3210-fedc-ba0987654321"
  }
}
```

## Quick reference

### Initialization (do once at app startup)
```python
from vector_inspector import get_version
from vector_inspector.services.telemetry_service import TelemetryService

telemetry = TelemetryService(app_version=get_version())
```

### Sending a simple event
```python
telemetry.queue_event({
    "event_name": "feature.toggled",
    "metadata": {"feature_name": "advanced_clustering", "new_value": True}
})
telemetry.send_batch()
```

### Sending an error
```python
telemetry.send_error_event(
    message="Failed to connect to database",
    tb=traceback.format_exc(),
    event_name="db.connection_failed",
    extra={"db_type": "chroma", "error_code": "CONN_REFUSED"}
)
```

### Using the decorator for automatic error telemetry
```python
from vector_inspector.utils.exception_handler import exception_telemetry

@exception_telemetry(event_name="DataImportError", feature="data_import")
def import_large_dataset():
    # Exceptions automatically sent to telemetry
    pass
```

---

For implementation details, see:
- `src/vector_inspector/services/telemetry_service.py` — Core telemetry service
- `src/vector_inspector/utils/exception_handler.py` — Automatic exception handling

## Implementation patterns

The implemented telemetry follows these patterns:

### 1. Connection telemetry (connection_controller.py)

**Pattern:** Async connection flow with correlation IDs

```python
# Generate correlation ID before operation
correlation_id = str(uuid.uuid4())

# Send attempt event (app_version auto-populated by TelemetryService)
telemetry.queue_event({
    "event_name": "db.connection_attempt",
    "metadata": {
        "db_type": provider,
        "host_hash": hashlib.sha256(host.encode()).hexdigest()[:16],
        "correlation_id": correlation_id
    }
})

# After operation completes
telemetry.queue_event({
    "event_name": "db.connection_result",
    "metadata": {
        "success": success,
        "duration_ms": duration,
        "correlation_id": correlation_id  # Same ID links events
    }
})
telemetry.send_batch()
```

**Key points:**
- Generate `correlation_id` once at the start
- Pass it through async workers via signals
- Hash sensitive data (hosts, paths) before sending
- Use try/except wrappers for best-effort telemetry
- No need to pass `app_version` - it's auto-populated

### 2. Query telemetry (search_view.py)

**Pattern:** Timing query execution with metadata

```python
correlation_id = str(uuid.uuid4())
start_time = time.time()

try:
    results = connection.query_collection(...)
    query_success = bool(results)
finally:
    duration_ms = int((time.time() - start_time) * 1000)
    telemetry.queue_event({
        "event_name": "query.executed",
        "metadata": {
            "query_type": "similarity",
            "result_count": len(results) if results else 0,
            "latency_ms": duration_ms,
            "correlation_id": correlation_id,
            "success": query_success
        }
    })
```

**Key points:**
- Use `finally` block to ensure telemetry fires
- Track success boolean separately
- Capture latency in milliseconds
- Service automatically adds app_version, hwid, client_type

### 3. Embedding telemetry (base_connection.py)

**Pattern:** Batch embedding tracking

```python
correlation_id = str(uuid.uuid4())
start_time = time.time()
batch_size = len(documents)
success = False

try:
    result = model.encode(documents)
    success = True
    return result
finally:
    duration_ms = int((time.time() - start_time) * 1000)
    telemetry.queue_event({
        "event_name": "embedding.request",
        "metadata": {
            "provider": model_type,
            "model_id": model_name,
            "batch_size": batch_size,
            "latency_ms": duration_ms,
            "success": success
        }
    })
```

**Key points:**
- Track batch size for performance analysis
- Include provider and model for debugging
- Use `locals()` check for variables that may not be defined if early failure

### 4. Visualization telemetry (visualization_service.py)

**Pattern:** Algorithm performance tracking

```python
start_time = time.time()
success = False

try:
    reduced = reducer.fit_transform(X)
    success = True
    return reduced
finally:
    duration_ms = int((time.time() - start_time) * 1000)
    telemetry.queue_event({
        "event_name": "visualization.generated",
        "metadata": {
            "method": method,
            "dims": n_components,
            "points_rendered": len(embeddings),
            "duration_ms": duration_ms,
            "success": success
        }
    })
```

**Key points:**
- Standard try/finally pattern
- Track algorithm parameters (method, dims)
- Include dataset size for performance correlation

### 5. Clustering telemetry (clustering.py)

**Pattern:** Algorithm with result statistics

```python
start_time = time.time()
cluster_count = 0
noise_count = 0
success = False

try:
    labels = clusterer.fit_predict(X)
    cluster_count = len(set(labels)) - (1 if -1 in labels else 0)
    noise_count = int((labels == -1).sum())
    success = True
    return labels
finally:
    telemetry.queue_event({
        "event_name": "clustering.run",
        "metadata": {
            "algorithm": algorithm,
            "dataset_size": len(embeddings),
            "cluster_count": cluster_count,
            "noise_count": noise_count,
            "duration_ms": duration_ms,
            "success": success
        }
    })
```

**Key points:**
- Calculate result statistics before telemetry
- Summarize params (keys only) to avoid large payloads
- Include noise/outlier counts for quality metrics

### Best practices summary

1. **Initialize once**: Create `TelemetryService(app_version=get_version())` once at app startup
2. **Always use try/finally**: Ensures telemetry fires even on exceptions
3. **Generate correlation_id early**: Create once, reuse across related events
4. **Hash PII**: Use `hashlib.sha256(value.encode()).hexdigest()[:16]` for sensitive data
5. **Best-effort wrapper**: Wrap telemetry calls in try/except to never break user flows
6. **Batch when possible**: Use `send_batch()` after queuing multiple events
7. **Track success**: Include boolean `success` field to measure reliability
8. **Millisecond precision**: Convert `time.time()` to `int(... * 1000)` for consistency
9. **No manual app_version**: Let TelemetryService auto-populate standard fields
