# Content Column Detection

## Overview

Vector Inspector now automatically detects the content/text column name across different vector database providers and custom schemas, eliminating the previous hardcoded assumption that all tables use "document" as the content column name.

## Problem

Previously, the code hardcoded "document" as the content column name, causing issues with:

- **Cross-database compatibility**: Milvus uses "text", not "document"
- **User-created tables**: Custom schemas might use "content", "text_content", or other names
- **Migration scenarios**: Moving data between providers with different column naming conventions
- **Metadata corruption**: Non-content columns could be incorrectly treated as metadata

## Solution

### Automatic Detection

The system now automatically detects the content column using this priority order:

1. **Common names** (checked in order):
   - `document` (PostgreSQL pgvector default)
   - `text` (Milvus default)
   - `content`
   - `text_content`
   - `doc`
   - `body`

2. **First text-type column**: If no common name is found, uses the first column with a text-related type (`text`, `varchar`, `character varying`, `string`, `str`)

3. **Default fallback**: Returns "document" if no text column is detected

### Caching

Detected column names are cached per collection to avoid repeated schema lookups, improving performance.

### Manual Override

For special cases, you can manually specify the content column:

```python
# Set custom content column for a collection
connection.set_content_column("my_collection", "custom_text_field")

# Get the current content column (uses cache or detection)
column_name = connection.get_content_column("my_collection")
```

## Implementation Details

### Base Connection Class

The `VectorDBConnection` base class provides:

- `_detect_content_column(collection_name, schema, override)`: Core detection logic
- `set_content_column(collection_name, column_name)`: Manual override
- `get_content_column(collection_name)`: Retrieve cached or detected column name
- `_content_column_cache`: Per-collection cache dictionary

### Provider Updates

All connection providers have been updated:

- **pgvector**: All 9 hardcoded "document" references replaced with dynamic detection
- **LanceDB**: All 11 references updated, preserves all columns during operations
- **Milvus**: Uses "text" consistently, works with detection automatically

### UI Components

UI components continue to use "document" as an internal dictionary key, but this is just for internal data passing. The connection layer handles the actual column mapping automatically, so no UI changes were required.

## Examples

### PostgreSQL with Standard Schema

```python
# Table with standard "document" column
schema = {"id": "uuid", "document": "text", "embedding": "vector"}
column = connection._detect_content_column("my_table", schema)
# Returns: "document"
```

### Milvus Schema

```python
# Milvus uses "text" by default
schema = {"id": "int", "text": "varchar", "metadata": "json", "vector": "array"}
column = connection._detect_content_column("my_collection", schema)
# Returns: "text"
```

### Custom Schema

```python
# User-created table with "content" column
schema = {"id": "int", "content": "character varying", "embedding": "vector"}
column = connection._detect_content_column("user_table", schema)
# Returns: "content"
```

### Custom Column Name

```python
# Table with non-standard text column
schema = {"id": "int", "description": "text", "embedding": "vector"}
column = connection._detect_content_column("products", schema)
# Returns: "description" (first text-type column)
```

### Manual Override

```python
# Force a specific column regardless of schema
connection.set_content_column("special_table", "custom_field")
# All operations on "special_table" will now use "custom_field"
```

## Testing

Comprehensive test coverage in `tests/test_content_column_detection.py`:

- Detection of all common column names
- Priority ordering verification
- Fallback behavior
- Cache functionality
- Manual override capability
- PostgreSQL-specific type handling

Run tests with:

```bash
python -m pytest tests/test_content_column_detection.py -v
```

## Migration Guide

### For Existing Users

No action required! The system will automatically detect your existing content column names. Your existing data and workflows will continue to work seamlessly.

### For New Collections

When creating new collections:

- **pgvector**: Continues to use "document" as default
- **Milvus**: Uses "text" as per Milvus convention
- **LanceDB**: Uses "document" as default for new tables

### For Custom Schemas

If you're creating tables with custom schemas outside of Vector Inspector:

1. Use one of the common names (`document`, `text`, `content`) if possible
2. Or use any text-type column - it will be auto-detected
3. Or manually configure via `set_content_column()` after connecting

## Future Enhancements

Potential future improvements:

1. **Persistent storage**: Store content column mapping in collection metadata
2. **UI configuration**: Add content column field to collection creation dialog
3. **Multi-column support**: Support multiple text columns per collection
4. **Custom type detection**: Plugin system for detecting content columns in custom database types

## Related Files

- `src/vector_inspector/core/connections/base_connection.py`: Core detection logic
- `src/vector_inspector/core/connections/pgvector_connection.py`: PostgreSQL implementation
- `src/vector_inspector/core/connections/lancedb_connection.py`: LanceDB implementation  
- `src/vector_inspector/core/connections/milvus_connection.py`: Milvus implementation (uses "text")
- `tests/test_content_column_detection.py`: Test suite
