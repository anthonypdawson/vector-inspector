"""Tests for LanceDB metadata array padding fixes."""

import pandas as pd
import pytest
from unittest.mock import Mock
from vector_inspector.core.connections.lancedb_connection import LanceDBConnection


@pytest.fixture
def lancedb_conn():
    """Create LanceDB connection for testing."""
    conn = LanceDBConnection()
    conn._db = Mock()
    conn._connected = True
    return conn


def test_query_collection_metadata_padding(lancedb_conn):
    """Test that query_collection pads metadatas to match result count."""
    # Mock table with results that have no metadata column
    mock_table = Mock()
    mock_results_df = pd.DataFrame({
        "id": ["id1", "id2", "id3"],
        "document": ["doc1", "doc2", "doc3"],
        "_distance": [0.1, 0.2, 0.3],
        "vector": [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    })

    mock_search = Mock()
    mock_search.limit.return_value.to_pandas.return_value = mock_results_df
    mock_table.search.return_value = mock_search
    lancedb_conn._db.open_table.return_value = mock_table

    # Query with embeddings
    result = lancedb_conn.query_collection(
        "test_collection",
        query_embeddings=[[0.1, 0.2]],
        n_results=3
    )

    assert result is not None
    assert len(result["ids"]) == 3
    assert len(result["documents"]) == 3
    assert len(result["metadatas"]) == 3  # Should be padded!
    # All metadatas should be empty dicts since no metadata column
    assert all(m == {} for m in result["metadatas"])


def test_get_all_items_metadata_padding(lancedb_conn):
    """Test that get_all_items pads metadatas to match result count."""
    # Mock table with no metadata column
    mock_table = Mock()
    mock_df = pd.DataFrame({
        "id": ["id1", "id2"],
        "document": ["content1", "content2"],
        "vector": [[1.0, 2.0], [3.0, 4.0]]
    })
    mock_table.to_pandas.return_value = mock_df
    lancedb_conn._db.open_table.return_value = mock_table

    result = lancedb_conn.get_all_items("test_collection")

    assert result is not None
    assert len(result["ids"]) == 2
    assert len(result["documents"]) == 2
    assert len(result["metadatas"]) == 2  # Should be padded!
    assert all(m == {} for m in result["metadatas"])


def test_query_collection_with_sparse_metadata(lancedb_conn):
    """Test query with sparse metadata (fewer metadata than results)."""
    mock_table = Mock()

    # Simulate sparse metadata - some rows have no metadata
    mock_results_df = pd.DataFrame({
        "id": ["id1", "id2", "id3"],
        "document": ["doc1", "doc2", "doc3"],
        "metadata": ['{"key": "value1"}', None, None],  # Only first has metadata
        "_distance": [0.1, 0.2, 0.3],
        "vector": [[0.1], [0.2], [0.3]]
    })

    mock_search = Mock()
    mock_search.limit.return_value.to_pandas.return_value = mock_results_df
    mock_table.search.return_value = mock_search
    lancedb_conn._db.open_table.return_value = mock_table

    result = lancedb_conn.query_collection(
        "test_collection",
        query_embeddings=[[0.1]],
        n_results=3
    )

    assert len(result["ids"]) == 3
    assert len(result["metadatas"]) == 3
    # Should handle None/missing metadata gracefully
    assert isinstance(result["metadatas"][0], dict)
    assert isinstance(result["metadatas"][1], dict)
    assert isinstance(result["metadatas"][2], dict)


def test_get_all_items_empty_collection(lancedb_conn):
    """Test get_all_items with empty collection."""
    mock_table = Mock()
    mock_df = pd.DataFrame({
        "id": [],
        "document": [],
        "vector": []
    })
    mock_table.to_pandas.return_value = mock_df
    lancedb_conn._db.open_table.return_value = mock_table

    result = lancedb_conn.get_all_items("empty_collection")

    assert result is not None
    assert len(result["ids"]) == 0
    assert len(result["documents"]) == 0
    assert len(result["metadatas"]) == 0


def test_query_collection_metadata_matches_documents(lancedb_conn):
    """Test that metadata array always matches document/id array length."""
    mock_table = Mock()

    # Create results with 5 items but metadata column missing
    mock_results_df = pd.DataFrame({
        "id": [f"id{i}" for i in range(5)],
        "document": [f"doc{i}" for i in range(5)],
        "_distance": [0.1 * i for i in range(5)],
        "vector": [[float(i)] for i in range(5)]
        # No metadata column at all
    })

    mock_search = Mock()
    mock_search.limit.return_value.to_pandas.return_value = mock_results_df
    mock_table.search.return_value = mock_search
    lancedb_conn._db.open_table.return_value = mock_table

    result = lancedb_conn.query_collection(
        "test_collection",
        query_embeddings=[[0.5]],
        n_results=5
    )

    # All arrays must have same length
    assert len(result["ids"]) == len(result["documents"])
    assert len(result["ids"]) == len(result["metadatas"])
    assert len(result["ids"]) == len(result["distances"])
    assert len(result["ids"]) == 5
