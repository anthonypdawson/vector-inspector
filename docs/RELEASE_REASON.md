# Release Notes (0.8.3) — June 21, 2026

Content column detection improvements and local embedding support.

## Features

- **Dynamic content column detection**: Automatically detects the best content column for each collection based on schema analysis (text/string fields, common naming patterns). Manual override support with persistence across sessions.
- **Ollama embedding integration**: Local embedding generation via Ollama HTTP API for environments where HuggingFace is blocked or unavailable.

## Improvements

- Content column configuration UI shows both auto-detected recommendation and currently active column
- Settings persistence for content column overrides per collection
- Fixed LanceDB schema detection to use PyArrow schema instead of pandas DataFrame conversion (performance improvement)
- Fixed threading deadlock in content column detection (switched from Lock to RLock)
- Platform-specific monospace fonts in UI dialogs (Menlo on macOS, Consolas on Windows)

## Bug Fixes

- Fixed LanceDB metadata array length mismatch in search results
- Fixed QThread leak in embedding configuration dialog
- Fixed content column cache poisoning when schema unavailable

---
