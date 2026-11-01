---
name: content-column-resolution-layers
description: >-
  Content column resolution order: persisted manual override short-circuits
  detection, then fingerprint-validated cache, then fresh detection
metadata:
  type: reference
  tags:
    - content-column
    - caching
    - base-connection
    - diagnosis
---

`VectorDBConnection._detect_content_column()` (`src/vector_inspector/core/connections/base_connection.py`) resolves in three layers, in order:

1. **Persisted manual override** — if the collection key exists in `_content_column_overrides` (seeded at construction from disk via `_load_persisted_overrides()`), the cached value is returned immediately. The passed schema is not even fingerprinted; detection never runs.
2. **Fingerprint-validated memory cache** — the schema is hashed (`_compute_schema_fingerprint`, md5 of sorted `col:type` pairs). A cached value is reused only when the stored fingerprint matches the current schema. A changed schema evicts the entry and detection re-runs. No-schema calls reuse whatever is cached.
3. **Fresh detection** — common names (`document`, `text`, `content`, `text_content`, `doc`, `body`), then fallback priority names (`description`, `summary`, ...), then first text-typed non-reserved column, else default `"document"`. The result is cached with the schema fingerprint — unless `skip_cache=True`.

Writes: `set_content_column()` sets the cache entry, flags the override, and immediately persists the whole override map to disk (`_persist_overrides` -> `SettingsService`), so the override outlives the process.

## Why this matters for diagnosis

Any order-dependent content-column test failure is almost certainly layer 1: a shared collection key (notably `"test_col"`, reused across many tests with different schemas and different expected results) plus an earlier `set_content_column` — in the same file, another test file, or a stale settings file from a previous run. Read the override map first (`content_column_overrides.<provider>` in the settings file); do not start from the detection heuristics in layer 3.
