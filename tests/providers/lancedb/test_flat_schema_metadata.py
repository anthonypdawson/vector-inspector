"""Test LanceDB flat schema metadata extraction (e.g., Contextus-style databases)."""

import pytest

pytest.importorskip("lancedb")

import uuid
import lancedb


def test_flat_schema_metadata_extraction(tmp_path):
    """Test that flat schema columns (non-nested) are correctly extracted as metadata."""
    # Create a LanceDB database with flat schema like Contextus uses
    db_path = str(tmp_path)
    db = lancedb.connect(db_path)

    # Create a table with flat schema columns (like Contextus)
    table_name = f"contextus_test_{uuid.uuid4().hex[:8]}"
    data = [
        {
            "id": "1",
            "vector": [0.1, 0.2, 0.3],
            "document": "First document",
            "project": "test-project",
            "filename": "test.md",
            "heading": "Introduction",
            "type": "decision",
            "chunk_index": 0,
        },
        {
            "id": "2",
            "vector": [0.4, 0.5, 0.6],
            "document": "Second document",
            "project": "test-project",
            "filename": "guide.md",
            "heading": "Setup",
            "type": "reference",
            "chunk_index": 1,
        },
    ]

    db.create_table(table_name, data=data, mode="overwrite")

    # Test with Vector Inspector connection
    from vector_inspector.core.connections.lancedb_connection import LanceDBConnection

    conn = LanceDBConnection(uri=db_path)
    assert conn.connect()

    # Test get_collection_info returns flat schema columns as metadata_fields
    info = conn.get_collection_info(table_name)
    assert info is not None
    assert info["count"] == 2

    # All non-reserved columns except content column should be in metadata_fields
    metadata_fields = info["metadata_fields"]
    # "document" is the content column and should be excluded from metadata
    expected_fields = {"project", "filename", "heading", "type", "chunk_index"}
    assert expected_fields.issubset(set(metadata_fields)), (
        f"Missing fields in metadata_fields. Expected {expected_fields}, got {set(metadata_fields)}"
    )
    # Verify document is NOT in metadata_fields (it's the content column)
    assert "document" not in metadata_fields, "Content column 'document' should not be in metadata_fields"

    # Test get_all_items extracts flat columns as metadata (excluding content column)
    items = conn.get_all_items(table_name, limit=10)
    assert items is not None
    assert len(items["ids"]) == 2
    assert len(items["metadatas"]) == 2

    # Check first item's metadata contains the flat schema columns (but not document)
    first_meta = items["metadatas"][0]
    assert "project" in first_meta
    assert "filename" in first_meta
    assert "heading" in first_meta
    assert "type" in first_meta
    assert "chunk_index" in first_meta
    # Verify document is NOT duplicated in metadata
    assert "document" not in first_meta, "Content column should not appear in metadata"

    assert first_meta["project"] == "test-project"
    assert first_meta["filename"] == "test.md"
    assert first_meta["heading"] == "Introduction"
    assert first_meta["type"] == "decision"
    assert first_meta["chunk_index"] == 0

    # Verify documents are properly extracted to the documents field
    assert items["documents"][0] == "First document"
    assert items["documents"][1] == "Second document"


def test_nested_metadata_column_still_works(tmp_path):
    """Test that legacy nested metadata column format still works."""
    from vector_inspector.core.connections.lancedb_connection import LanceDBConnection

    collection_name = f"test_nested_{uuid.uuid4().hex[:8]}"
    db_path = str(tmp_path)

    conn = LanceDBConnection(uri=db_path)
    assert conn.connect()

    # Create collection with nested metadata (old format)
    assert conn.create_collection(collection_name, vector_size=2)

    # Add items with metadata in the traditional nested format
    test_docs = ["doc1", "doc2"]
    test_metadata = [{"key1": "value1"}, {"key2": "value2"}]
    test_ids = ["id1", "id2"]
    test_vectors = [[0.1, 0.2], [0.3, 0.4]]

    assert conn.add_items(
        collection_name,
        documents=test_docs,
        metadatas=test_metadata,
        ids=test_ids,
        embeddings=test_vectors,
    )

    # Verify nested metadata still works
    items = conn.get_all_items(collection_name, limit=10)
    assert items is not None
    assert len(items["metadatas"]) == 2
    assert items["metadatas"][0].get("key1") == "value1"
    assert items["metadatas"][1].get("key2") == "value2"
