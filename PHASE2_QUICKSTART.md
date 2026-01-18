# Phase 2 Features - Quick Reference

## Advanced Metadata Filtering

### Where to Find It
- **Data Browser tab**: "Metadata Filters" section
- **Search tab**: "Advanced Metadata Filters" section

### How to Use
1. Click checkbox to enable filtering
2. Click "+ Add Filter Rule"
3. Enter: `field_name` `operator` `value`
4. Add multiple rules as needed
5. Choose AND/OR logic
6. Data updates automatically

### Supported Operators

**Server-Side (Fast, filtered in database):**
- `=` - Equals
- `!=` - Not equals
- `>`, `>=`, `<`, `<=` - Numeric comparisons
- `in` - Value in comma-separated list
- `not in` - Value not in list

**Client-Side (Slower, filtered in app after fetching):**
- `contains (client-side)` - Text contains substring
- `not contains (client-side)` - Text does not contain substring

**Note**: Client-side filters fetch data first then filter locally. For better text search, use the Search tab for semantic similarity queries. Client-side filters work on any field including the special "document" field.

### Examples
```
category = science
year >= 2020
author in Einstein, Newton, Curie
```

## Item Editing

### How to Edit
1. Go to Data Browser tab
2. Select a collection
3. **Double-click** any row
4. Edit dialog opens
5. Modify document or metadata (JSON format)
6. Click "Save"

### Tips
- ID is read-only (can't be changed)
- Metadata must be valid JSON
- Embeddings auto-regenerate from document text

## Import/Export

### Export Data

**Location**: Data Browser → "Export..." button

**Steps**:
1. Select collection
2. (Optional) Apply filters to export subset
3. Click "Export..." dropdown
4. Choose format:
   - **JSON** - Best for embeddings
   - **CSV** - Best for spreadsheets
   - **Parquet** - Best for data science
5. Choose save location

### Import Data

**Location**: Data Browser → "Import..." button

**Steps**:
1. Select target collection
2. Click "Import..." dropdown
3. Choose format (JSON/CSV/Parquet)
4. Select file
5. Data is added to collection

**Notes**:
- Embeddings auto-generate if not in file
- Metadata in CSV uses `metadata_` prefix
- IDs can be provided or auto-generated

## Backup & Restore

### Access
- **Menu**: Collection → Backup/Restore (Ctrl+B)
- **Toolbar**: "Backup/Restore" button

### Create Backup

**Tab**: "Create Backup"

1. Collection automatically selected
2. Choose backup directory (default: `~/vector-viewer-backups/`)
3. Check/uncheck "Include embedding vectors"
   - Checked: Full backup (larger)
   - Unchecked: Metadata only (smaller, embeddings regenerate)
4. Click "Create Backup"

**Backup Format**: `{collection}_backup_{timestamp}.zip`

### Restore Backup

**Tab**: "Restore from Backup"

1. Click "Refresh List" to see available backups
2. Select a backup from list
3. (Optional) Enter new collection name
4. Check "Overwrite if exists" if needed
5. Click "Restore Selected"

### Manage Backups

- **Refresh List**: Update backup list
- **Delete Selected**: Remove unwanted backup files
- Backups show: collection name, timestamp, item count, file size

## Keyboard Shortcuts

- **Ctrl+B** - Open Backup/Restore dialog
- **F5** - Refresh collections list
- **Ctrl+O** - Connect to database
- **Ctrl+Q** - Exit application

## Tips & Best Practices

### Filtering
- Start with simple filters, then add more
- Use "contains" for text search
- Use numeric operators for dates/numbers
- Combine search with filters for powerful queries

### Editing
- Always validate JSON before saving
- Consider backup before bulk edits
- Embeddings regenerate automatically

### Export/Import
- **JSON**: Best for full data preservation
- **CSV**: Best for Excel/spreadsheet analysis
- **Parquet**: Best for pandas/data science workflows
- Export filtered data for subsets

### Backup/Restore
- Create backups before major changes
- Include embeddings for full fidelity
- Exclude embeddings to save space (they regenerate)
- Name restored collections differently to compare
- Regular backups prevent data loss

## Troubleshooting

### Filter Not Working
- Check field name spelling (case-sensitive)
- Verify value type (number vs string)
- Enable filter group (checkbox)

### Edit Failed
- Metadata must be valid JSON: `{"key": "value"}`
- Check collection connection
- Verify item still exists

### Import Failed
- Check file format matches selection
- Verify JSON structure
- CSV metadata columns must start with `metadata_`

### Restore Failed
- Check "Overwrite" option if collection exists
- Verify backup file integrity
- Ensure sufficient disk space

## File Locations

- **Backups**: `~/vector-viewer-backups/` (customizable)
- **Exports**: User-selected location
- **Imports**: User-selected files

## What's Next?

Phase 3 will add:
- More vector database providers (Pinecone, Weaviate)
- Enhanced visualization features
- Query history and templates
- And more!

Stay tuned for updates!
