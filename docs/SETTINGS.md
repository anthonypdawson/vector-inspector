Settings & Preferences

Overview

This document describes the initial Settings/Preferences surface for Vector Viewer, storage/persistence choices, and implementation notes for adding new options.

Storage

- Use `QSettings` (platform-native persistent storage). Keeps settings simple and cross-platform.
- Store non-sensitive settings directly. For secrets (API keys) consider encrypting on disk or using OS keychain where available.

Minimal initial settings (recommended)

- breadcrumb.enabled: bool — Show breadcrumb bar (default: true)
- breadcrumb.elide_mode: enum {left, middle} — How long breadcrumbs are elided (default: left)
- window.restore_geometry: bool — Restore window size/position on startup (default: true)
- window.geometry: bytes — Saved geometry blob (managed by `QMainWindow.saveGeometry()` / `restoreGeometry()`)
- search.default_n_results: int — Default results count for searches (default: 10)
- embeddings.auto_generate: bool — Auto-generate embeddings for pasted/added text (default: true)
- embeddings.auto_generate_per_collection: bool — Allow per-collection override (default: false)
- telemetry.enabled: bool — Opt-in telemetry (default: false)
- theme: enum {system, light, dark} — UI theme preference (default: system)
- logging.level: string — e.g. DEBUG/INFO/WARNING (default: INFO)

Additional useful options (nice-to-have)

- cache.max_entries: int, cache.ttl_seconds: int — Control local cache size/expiry
- provider.default_distance_metric: string — e.g. cosine, euclidean
- provider.auto_reindex_on_change: bool — Background reindex when underlying data changes
- proxy/http_proxy: string — Proxy for networked providers
- api_keys.store_securely: bool — Use OS keychain if available
- experimental.features: list — Toggle experimental UI/engine flags
- keyboard.shortcuts: mapping — Customizable shortcuts (save/import/prev/next)

UI and UX

- Implement a `SettingsDialog` (modal) placed under `Edit -> Preferences` or `File -> Settings` with grouped sections: General, Search, Embeddings, Providers, Advanced.
- Each setting writes immediately to `QSettings` (or on OK) and emits a small internal signal so listeners can react without restart.

Implementation notes

- Provide a small settings helper module `vector_inspector.core.settings` with typed accessor functions (get_bool, get_int, get_enum, set_value) and default values.
- On startup, read key settings before building UI (e.g., theme, window geometry, breadcrumb toggle).
- For window geometry: store via `QMainWindow.saveGeometry()` into `window.geometry` and restore on startup if `window.restore_geometry` is true.
- For breadcrumb: `SearchView.set_breadcrumb()` should check `breadcrumb.enabled` and hide/clear label when disabled.
- For auto-embedding generation: integration point is the connection/provider layer — expose `should_auto_embed(collection)` helper that reads global and per-collection flags.

Extensibility & migrations

- Version settings by a `settings.version` key so migrations can be applied when adding/removing keys.
- When adding new enum options, provide fallback defaults for older settings.

Security

- Treat API keys and secrets carefully: either don't persist them or persist using OS-provided secure storage. Document where keys are stored and how to clear them.

Developer notes

- To add a setting:
  1. Add typed accessor in `vector_inspector.core.settings` with a sensible default.
  2. Add a control to `SettingsDialog` and wire OK/apply to `set_value()`.
  3. Add consumers (e.g., `SearchView`) to listen for setting changes or query setting on relevant events.

Next steps

- Implement `vector_inspector.ui.dialogs.settings_dialog` and a small `vector_inspector.core.settings` wrapper.
- Wire `MainWindow` to open the dialog and persist changes.

Questions / decisions for you

- Do we want settings applied immediately, or only on dialog OK? (I recommend immediate apply with an explicit `Reset` option.)
- Do you want per-collection overrides visible in the same dialog or managed separately on collection settings UI?

---

File created by the dev assistant. Update as needed.