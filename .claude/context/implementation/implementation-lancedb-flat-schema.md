---
name: lancedb-flat-schema-support
description: LanceDB databases can use flat schemas (columns) or nested metadata - handle both patterns with content column detection
metadata:
  type: implementation
  tags: [lancedb, metadata, schema, contextus]
---

# LanceDB Flat Schema Support

## Problem

LanceDB supports two metadata storage patterns:

1. **Nested metadata** (traditional): Single `metadata` column containing a dict/JSON
2. **Flat schema** (Contextus-style): Individual columns like `project`, `filename`, `heading`, `type`, `chunk_index`

Vector Inspector originally only supported pattern #1, causing Contextus databases to show empty metadata.

## Solution Pattern

### In `get_collection_info()`

1. **Extract from PyArrow schema first** (most reliable):
   ```python
   schema = tbl.schema
   reserved_columns = {"id", "vector", "embedding", "_distance"}
   
   # Detect content column to exclude it
   temp_schema = {field.name: str(field.type) for field in schema}
   content_col = self._detect_content_column(name, temp_schema)
   reserved_columns.add(content_col)
   
   # All other columns are metadata
   metadata_fields = [
       field.name for field in schema
       if field.name not in reserved_columns and not field.name.startswith("_")
   ]
   ```

2. **Fallback to pandas** if schema extraction fails

3. **CRITICAL**: Must also check `count is None` in fallback condition, not just metadata/vector detection

### In `get_all_items()`

1. **Detect content column FIRST** to build reserved set:
   ```python
   schema = {col: str(dtype) for col, dtype in df.dtypes.items()}
   content_col = self._detect_content_column(collection_name, schema)
   reserved_columns = {"id", "vector", "embedding", "_distance", content_col}
   ```

2. **Check for nested metadata column first**:
   ```python
   if "metadata" in df.columns:
       # Parse nested format
       raw_meta = df["metadata"].tolist()
       metadatas = self._parse_metadata_list(raw_meta)
   ```

3. **Otherwise extract flat schema columns**:
   ```python
   else:
       metadata_columns = [
           col for col in df.columns
           if col not in reserved_columns and not col.startswith("_")
       ]
       
       if metadata_columns:
           records = df[metadata_columns].to_dict('records')
           metadatas = [
               {k: v for k, v in record.items()
                if v is not None and (not isinstance(v, float) or not math.isnan(v))}
               for record in records
           ]
   ```

## Why Exclude Content Column

The content column (e.g., "document", "text", "content") serves a special purpose:
- It's displayed in the "Document" column of the data browser
- If also included in metadata, it appears TWICE in the table (once as "Document", once as "document")
- Users expect metadata to be *additional* fields, not duplicates of the main content

## Edge Cases

1. **Empty content column**: If content detection returns None or empty string, don't add it to reserved set
2. **NaN values**: Filter out `math.isnan()` values when building metadata dicts from flat schemas
3. **Count detection**: Even if schema extraction succeeds, must still fetch dataframe if `count is None`
4. **Backward compatibility**: Nested metadata format must continue to work (used by most LanceDB databases)

## Testing

Always test both patterns:
```python
# Flat schema (Contextus-style)
data = [
    {
        "id": "1",
        "vector": [0.1, 0.2, 0.3],
        "document": "content",
        "project": "test",
        "filename": "file.md",
    }
]

# Nested metadata (traditional)
conn.add_items(
    collection,
    documents=["doc1"],
    metadatas=[{"key": "value"}],
    ids=["id1"],
    embeddings=[[0.1, 0.2]]
)
```

## Files Modified

- `src/vector_inspector/core/connections/lancedb_connection.py`: Both `get_collection_info()` and `get_all_items()`
- Tests: `tests/providers/lancedb/test_flat_schema_metadata.py`
