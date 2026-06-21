"""Tests for content column persistence across sessions."""
from vector_inspector.core.connections.lancedb_connection import LanceDBConnection


def test_content_column_persists_across_instances():
    """Test that manually set content columns persist across connection instances."""
    # First connection - set override
    conn1 = LanceDBConnection()
    conn1.set_content_column("test_collection", "custom_column")

    # Verify it was set
    assert conn1.get_content_column("test_collection") == "custom_column"
    assert conn1.is_content_column_overridden("test_collection") is True

    # Second connection - should load the persisted override
    conn2 = LanceDBConnection()

    # Should have the override from settings
    assert conn2.get_content_column("test_collection") == "custom_column"
    assert conn2.is_content_column_overridden("test_collection") is True


def test_auto_detected_columns_not_persisted():
    """Test that auto-detected columns don't pollute settings."""
    from vector_inspector.core.connections.pgvector_connection import PgVectorConnection

    conn = PgVectorConnection()

    # Auto-detect from schema (not manually set)
    schema = {"id": "integer", "text": "text", "embedding": "vector"}
    result = conn._detect_content_column("auto_collection", schema)

    assert result == "text"
    assert conn.is_content_column_overridden("auto_collection") is False

    # Now create a new connection - should NOT have this cached
    conn2 = PgVectorConnection()
    # Cache should be empty (not persisted)
    with conn2._cache_lock:
        assert "auto_collection" not in conn2._content_column_cache


def test_override_replaces_auto_detected():
    """Test that manual override replaces auto-detected value and persists."""
    from vector_inspector.core.connections.pgvector_connection import PgVectorConnection

    conn1 = PgVectorConnection()

    # First auto-detect
    schema = {"id": "integer", "text": "text", "content": "text", "embedding": "vector"}
    auto_detected = conn1._detect_content_column("my_collection", schema)
    assert auto_detected == "text"  # First match
    assert conn1.is_content_column_overridden("my_collection") is False

    # Now manually override
    conn1.set_content_column("my_collection", "content")
    assert conn1.get_content_column("my_collection") == "content"
    assert conn1.is_content_column_overridden("my_collection") is True

    # New connection should have the override
    conn2 = PgVectorConnection()
    assert conn2.get_content_column("my_collection") == "content"
    assert conn2.is_content_column_overridden("my_collection") is True
