# Release Notes (0.8.4) — June 23, 2026

Critical LanceDB metadata extraction fixes and column rendering improvements.

## Bug Fixes

- **LanceDB flat schema metadata extraction**: Fixed metadata display for LanceDB databases with flat schemas (e.g., Contextus) where metadata is stored as individual columns rather than nested in a 'metadata' column
- **Duplicate document column**: Prevented content column from appearing twice in data browser (once as content, once as metadata)
- **Column width limits**: Added 600px max-width constraint to table columns to prevent excessive width from breaking UI

## Improvements

- LanceDB connection now extracts metadata from PyArrow schema first for better performance
- Content column (e.g., "document") is automatically detected and excluded from metadata fields
- Backward compatibility maintained with nested 'metadata' column format

## Testing

- Added comprehensive tests for flat schema metadata extraction
- CI workflow now runs unit tests on all pull requests

---
