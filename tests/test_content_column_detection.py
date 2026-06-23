"""Test content column detection across different schemas."""

from vector_inspector.core.connections.pgvector_connection import PgVectorConnection


def test_detect_document_column():
    """Test detection of 'document' column."""
    conn = PgVectorConnection()
    schema = {"id": "int", "document": "text", "embedding": "vector"}
    result = conn._detect_content_column("test_col", schema)
    assert result == "document"


def test_detect_text_column():
    """Test detection of 'text' column (Milvus style)."""
    conn = PgVectorConnection()
    schema = {"id": "int", "text": "varchar", "embedding": "vector"}
    result = conn._detect_content_column("test_col", schema)
    assert result == "text"


def test_detect_content_column():
    """Test detection of 'content' column."""
    conn = PgVectorConnection()
    schema = {"id": "int", "content": "text", "embedding": "vector"}
    result = conn._detect_content_column("test_col", schema)
    assert result == "content"


def test_detect_text_content_column():
    """Test detection of 'text_content' column."""
    conn = PgVectorConnection()
    schema = {"id": "int", "text_content": "varchar", "embedding": "vector"}
    result = conn._detect_content_column("test_col", schema)
    assert result == "text_content"


def test_fallback_to_first_text_column():
    """Test fallback to first text-type column."""
    conn = PgVectorConnection()
    schema = {"id": "int", "description": "text", "embedding": "vector"}
    result = conn._detect_content_column("test_col", schema)
    assert result == "description"


def test_default_fallback():
    """Test default fallback when no text column found."""
    conn = PgVectorConnection()
    schema = {"id": "int", "embedding": "vector"}
    result = conn._detect_content_column("test_col", schema)
    assert result == "document"


def test_priority_order():
    """Test that 'document' takes priority over 'text'."""
    conn = PgVectorConnection()
    schema = {"id": "int", "document": "text", "text": "varchar", "embedding": "vector"}
    result = conn._detect_content_column("test_col", schema)
    assert result == "document"


def test_cache_behavior():
    """Test that detected column is cached."""
    conn = PgVectorConnection()
    schema = {"id": "int", "content": "text", "embedding": "vector"}

    # First call should detect
    result1 = conn._detect_content_column("test_col", schema)
    assert result1 == "content"

    # Second call should use cache (even with different schema)
    result2 = conn._detect_content_column("test_col", {"id": "int", "other": "text"})
    assert result2 == "content"


def test_manual_override():
    """Test manual override via set_content_column."""
    conn = PgVectorConnection()

    # Set manual override
    conn.set_content_column("test_col", "custom_text")

    # Should return override even with schema that would detect differently
    schema = {"id": "int", "document": "text", "custom_text": "varchar", "embedding": "vector"}
    result = conn._detect_content_column("test_col", schema)
    assert result == "custom_text"


def test_get_content_column():
    """Test get_content_column method."""
    conn = PgVectorConnection()
    schema = {"id": "int", "text": "varchar", "embedding": "vector"}

    # First call detects and caches
    conn._detect_content_column("test_col", schema)

    # get_content_column should return cached value
    result = conn.get_content_column("test_col")
    assert result == "text"


def test_postgres_varchar_type():
    """Test detection with PostgreSQL varchar type."""
    conn = PgVectorConnection()
    schema = {"id": "uuid", "content": "character varying", "embedding": "vector"}
    result = conn._detect_content_column("test_col", schema)
    assert result == "content"


def test_empty_schema():
    """Test handling of empty schema."""
    conn = PgVectorConnection()
    schema = {}
    result = conn._detect_content_column("test_col", schema)
    assert result == "document"  # Should fallback to default


def test_reserved_columns_skipped():
    """Test that reserved columns are not selected as content."""
    conn = PgVectorConnection()
    # Schema with only reserved columns
    schema = {"id": "int", "embedding": "vector", "metadata": "jsonb", "_distance": "float"}
    result = conn._detect_content_column("test_col", schema)
    assert result == "document"  # Should fallback since no valid content column


def test_multiple_text_columns_priority():
    """Test priority when multiple text-type columns exist."""
    conn = PgVectorConnection()
    # Multiple candidates - should prefer 'document' first
    schema = {
        "id": "int",
        "summary": "text",
        "body": "text",
        "document": "text",
        "notes": "text",
        "embedding": "vector",
    }
    result = conn._detect_content_column("test_col", schema)
    assert result == "document"


def test_text_type_variants():
    """Test detection across various text type names."""
    conn = PgVectorConnection()

    # Test with 'varchar'
    schema1 = {"id": "int", "data": "varchar", "embedding": "vector"}
    result1 = conn._detect_content_column("test1", schema1)
    assert result1 == "data"

    # Test with 'character varying' (full PostgreSQL type)
    schema2 = {"id": "int", "data": "character varying", "embedding": "vector"}
    result2 = conn._detect_content_column("test2", schema2)
    assert result2 == "data"

    # Test with 'string'
    schema3 = {"id": "int", "data": "string", "embedding": "vector"}
    result3 = conn._detect_content_column("test3", schema3)
    assert result3 == "data"


def test_case_insensitive_detection():
    """Test that column name matching is case-sensitive (as designed)."""
    conn = PgVectorConnection()
    # 'Document' (capitalized) should not match 'document' priority
    schema = {"id": "int", "Document": "text", "embedding": "vector"}
    result = conn._detect_content_column("test_col", schema)
    # Should fall back to first text column since 'Document' != 'document'
    assert result == "Document"


def test_set_and_get_content_column_persistence():
    """Test that set_content_column persists across get_content_column calls."""
    conn = PgVectorConnection()

    # Set custom column
    conn.set_content_column("collection1", "my_custom_field")

    # Get should return the custom column
    result = conn.get_content_column("collection1")
    assert result == "my_custom_field"

    # Different collection should not be affected
    result2 = conn.get_content_column("collection2")
    # collection2 has never been accessed, should fallback
    assert result2 == "document"


def test_multiple_collections_independent():
    """Test that content columns are tracked independently per collection."""
    conn = PgVectorConnection()

    schema1 = {"id": "int", "text": "varchar", "embedding": "vector"}
    schema2 = {"id": "int", "content": "text", "embedding": "vector"}

    # Detect for first collection
    result1 = conn._detect_content_column("coll1", schema1)
    assert result1 == "text"

    # Detect for second collection
    result2 = conn._detect_content_column("coll2", schema2)
    assert result2 == "content"

    # Verify both are cached independently
    assert conn.get_content_column("coll1") == "text"
    assert conn.get_content_column("coll2") == "content"


def test_override_replaces_detected():
    """Test that manual override replaces auto-detected column."""
    conn = PgVectorConnection()

    # Auto-detect first
    schema = {"id": "int", "document": "text", "custom": "varchar", "embedding": "vector"}
    result1 = conn._detect_content_column("test_col", schema)
    assert result1 == "document"

    # Now override
    conn.set_content_column("test_col", "custom")

    # Future calls should use override
    result2 = conn.get_content_column("test_col")
    assert result2 == "custom"
