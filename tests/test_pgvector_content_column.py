"""Tests for PgVector-specific content column detection and schema introspection."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from vector_inspector.core.connections.pgvector_connection import PgVectorConnection


def test_get_table_schema_basic():
    """Test _get_table_schema extracts correct schema."""
    conn = PgVectorConnection()

    # Mock cursor and connection
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        ("id", "integer", "int4"),
        ("content", "text", "text"),
        ("embedding", "USER-DEFINED", "vector"),
    ]
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=None)

    mock_db_conn = Mock()
    mock_db_conn.cursor.return_value = mock_cursor
    conn._client = mock_db_conn

    schema = conn._get_table_schema("test_table")

    # Uses data_type for standard types, udt_name for USER-DEFINED
    assert schema == {
        "id": "integer",
        "content": "text",
        "embedding": "vector"
    }


def test_get_table_schema_varchar_variations():
    """Test schema extraction with various varchar types."""
    conn = PgVectorConnection()

    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        ("id", "uuid", "uuid"),
        ("title", "character varying", "varchar"),
        ("body", "character varying", "varchar"),
        ("notes", "text", "text"),
        ("embedding", "USER-DEFINED", "vector"),
    ]
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=None)

    mock_db_conn = Mock()
    mock_db_conn.cursor.return_value = mock_cursor
    conn._client = mock_db_conn

    schema = conn._get_table_schema("documents")

    assert "title" in schema
    assert "body" in schema
    # data_type is used (not udt_name) for non-USER-DEFINED types
    assert schema["title"] == "character varying"
    assert schema["body"] == "character varying"


def test_get_table_schema_empty_result():
    """Test _get_table_schema with empty result (table doesn't exist)."""
    conn = PgVectorConnection()

    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = []

    mock_db_conn = Mock()
    mock_db_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
    mock_db_conn.cursor.return_value.__exit__ = Mock(return_value=None)
    conn.conn = mock_db_conn

    schema = conn._get_table_schema("nonexistent_table")

    assert schema == {}


def test_get_table_schema_connection_error():
    """Test _get_table_schema handles database connection errors gracefully."""
    conn = PgVectorConnection()
    conn._client = None  # No connection

    # Should return empty dict instead of raising
    schema = conn._get_table_schema("test_table")
    assert schema == {}


def test_content_column_with_postgres_types():
    """Test content column detection with PostgreSQL-specific types."""
    conn = PgVectorConnection()

    # jsonb should not be selected as content
    schema1 = {"id": "integer", "metadata": "jsonb", "text": "text", "embedding": "vector"}
    result1 = conn._detect_content_column("coll1", schema1)
    assert result1 == "text"

    # array types should not be selected
    schema2 = {"id": "integer", "tags": "text[]", "content": "text", "embedding": "vector"}
    result2 = conn._detect_content_column("coll2", schema2)
    assert result2 == "content"


def test_content_column_with_uuid_id():
    """Test content detection with UUID primary key."""
    conn = PgVectorConnection()

    schema = {"id": "uuid", "document": "text", "created_at": "timestamp", "embedding": "vector"}
    result = conn._detect_content_column("test", schema)
    assert result == "document"


def test_content_column_with_vector_dimensions():
    """Test that vector columns with dimensions are handled."""
    conn = PgVectorConnection()

    schema = {
        "id": "integer",
        "content": "text",
        "embedding_768": "vector(768)",
        "embedding_384": "vector(384)"
    }
    result = conn._detect_content_column("test", schema)
    assert result == "content"


def test_integration_get_schema_and_detect():
    """Test integration of schema extraction and content detection."""
    conn = PgVectorConnection()

    # Mock cursor
    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        ("id", "uuid", "uuid"),
        ("document", "text", "text"),
        ("metadata", "jsonb", "jsonb"),
        ("embedding", "USER-DEFINED", "vector"),
    ]
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=None)

    mock_db_conn = Mock()
    mock_db_conn.cursor.return_value = mock_cursor
    conn._client = mock_db_conn

    # Get schema
    schema = conn._get_table_schema("articles")
    assert "document" in schema

    # Detect content column
    content_col = conn._detect_content_column("articles", schema)
    assert content_col == "document"


def test_content_column_persistence_across_calls():
    """Test that content column persists correctly for PgVector."""
    conn = PgVectorConnection()

    schema = {"id": "integer", "body": "text", "embedding": "vector"}

    # First detection
    result1 = conn._detect_content_column("test_coll", schema)
    assert result1 == "body"

    # Should be cached
    result2 = conn.get_content_column("test_coll")
    assert result2 == "body"

    # Override
    conn.set_content_column("test_coll", "custom_field")
    result3 = conn.get_content_column("test_coll")
    assert result3 == "custom_field"


def test_detect_with_mixed_case_columns():
    """Test detection with mixed-case column names."""
    conn = PgVectorConnection()

    schema = {
        "Id": "integer",
        "Content": "text",
        "Embedding": "vector"
    }

    # Case-sensitive match should not find 'content' but should find 'Content'
    result = conn._detect_content_column("test", schema)
    # Falls back to first text column
    assert result == "Content"


def test_schema_with_special_postgres_types():
    """Test schema extraction with special PostgreSQL types."""
    conn = PgVectorConnection()

    mock_cursor = Mock()
    mock_cursor.fetchall.return_value = [
        ("id", "bigint", "int8"),
        ("content", "text", "text"),
        ("created", "timestamp with time zone", "timestamptz"),
        ("data", "jsonb", "jsonb"),
        ("embedding", "USER-DEFINED", "vector"),
    ]
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=None)

    mock_db_conn = Mock()
    mock_db_conn.cursor.return_value = mock_cursor
    conn._client = mock_db_conn

    schema = conn._get_table_schema("test_table")

    # Uses data_type, not udt_name, for non-USER-DEFINED types
    assert schema["id"] == "bigint"
    assert schema["created"] == "timestamp with time zone"
    assert schema["data"] == "jsonb"


def test_null_connection_handling():
    """Test graceful handling when connection is not established."""
    conn = PgVectorConnection()
    # No connection established
    assert conn._client is None

    # Getting content column for unknown collection should fallback
    result = conn.get_content_column("unknown")
    assert result == "document"
