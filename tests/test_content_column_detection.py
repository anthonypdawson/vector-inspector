"""Test content column detection across different schemas."""

import pytest
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
