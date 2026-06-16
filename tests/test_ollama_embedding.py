"""Tests for Ollama embedding support."""

import json
import pytest
from unittest.mock import Mock, patch
from vector_inspector.core.embedding_utils import load_embedding_model, encode_text


def test_load_embedding_model_ollama():
    """Test loading Ollama model returns model name string."""
    model = load_embedding_model("nomic-embed-text", "ollama")
    assert model == "nomic-embed-text"
    assert isinstance(model, str)


def test_encode_text_ollama_success():
    """Test encoding text with Ollama."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        # Mock HTTP response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "embeddings": [[0.1, 0.2, 0.3, 0.4]]
        }).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        # Test encoding
        result = encode_text("test document", "nomic-embed-text", "ollama")

        assert isinstance(result, list)
        assert len(result) == 4
        assert result == [0.1, 0.2, 0.3, 0.4]


def test_encode_text_ollama_empty_embeddings():
    """Test encoding with empty embeddings response raises error."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "embeddings": []
        }).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        with pytest.raises(RuntimeError, match="Ollama returned no embeddings"):
            encode_text("test", "nomic-embed-text", "ollama")


def test_encode_text_ollama_connection_error():
    """Test encoding handles connection errors."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_urlopen.side_effect = Exception("Connection refused")

        with pytest.raises(RuntimeError, match="Failed to get embedding from Ollama"):
            encode_text("test", "nomic-embed-text", "ollama")


def test_encode_text_ollama_request_format():
    """Test that Ollama request is formatted correctly."""
    with patch('urllib.request.Request') as mock_request, \
         patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"embeddings": [[0.5]]}).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        encode_text("hello world", "mxbai-embed-large", "ollama")

        # Verify request was created with correct URL and headers
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "http://localhost:11434/api/embed" in str(call_args)


def test_encode_text_with_sentence_transformer():
    """Test encoding with SentenceTransformer model object."""
    import numpy as np

    mock_model = Mock()
    # encode() returns numpy array which needs .tolist()
    mock_embedding = np.array([0.1, 0.2, 0.3])
    mock_model.encode.return_value = mock_embedding

    result = encode_text("test text", mock_model, "sentence-transformer")

    assert result == [0.1, 0.2, 0.3]
    mock_model.encode.assert_called_once_with("test text")


def test_encode_text_with_tuple_model():
    """Test encoding with tuple (model, processor) format for CLIP."""
    import torch
    import numpy as np

    mock_model = Mock()
    mock_processor = Mock()

    # Mock CLIP processor output
    mock_inputs = {"input_ids": torch.tensor([[1, 2, 3]])}
    mock_processor.return_value = mock_inputs

    # Mock CLIP text features output
    mock_features = torch.tensor([[0.4, 0.5, 0.6]])
    mock_model.get_text_features.return_value = mock_features

    result = encode_text("test text", (mock_model, mock_processor), "clip")

    # Should normalize and convert to list
    assert len(result) == 3
    assert isinstance(result, list)


def test_encode_text_with_string_sentence_transformer():
    """Test that string model name with sentence-transformer type raises error."""
    # If a string is passed when not using Ollama, Python's str.encode() is called (wrong!)
    # This should fail with either LookupError (if treated as encoding name) or AttributeError
    with pytest.raises((AttributeError, LookupError)):
        encode_text("test", "sentence-transformers/all-MiniLM-L6-v2", "sentence-transformer")


def test_encode_text_ollama_malformed_json():
    """Test handling of malformed JSON response from Ollama."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = b"not valid json"
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        with pytest.raises(RuntimeError, match="Failed to get embedding from Ollama"):
            encode_text("test", "nomic-embed-text", "ollama")


def test_encode_text_ollama_missing_embeddings_key():
    """Test handling of response without 'embeddings' key raises error."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"error": "model not found"}).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        # When embeddings key is missing, it raises an error
        with pytest.raises(RuntimeError, match="Ollama returned no embeddings"):
            encode_text("test", "unknown-model", "ollama")


def test_encode_text_ollama_http_error():
    """Test handling of HTTP error responses."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            url="http://localhost:11434/api/embed",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None
        )

        with pytest.raises(RuntimeError, match="Failed to get embedding from Ollama"):
            encode_text("test", "missing-model", "ollama")


def test_encode_text_ollama_url_error():
    """Test handling of URL/connection errors."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        from urllib.error import URLError
        mock_urlopen.side_effect = URLError("Connection refused")

        with pytest.raises(RuntimeError, match="Failed to get embedding from Ollama"):
            encode_text("test", "nomic-embed-text", "ollama")


def test_encode_text_ollama_multiple_embeddings():
    """Test that only first embedding is returned when multiple are present."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "embeddings": [[0.1, 0.2], [0.3, 0.4]]
        }).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        result = encode_text("test", "nomic-embed-text", "ollama")
        assert result == [0.1, 0.2]  # Only first embedding


def test_encode_text_empty_string():
    """Test encoding empty string with Ollama."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "embeddings": [[0.0, 0.0, 0.0]]
        }).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        result = encode_text("", "nomic-embed-text", "ollama")
        assert isinstance(result, list)
        assert len(result) == 3


def test_load_embedding_model_unknown_type():
    """Test loading model with unknown type falls through to sentence-transformer."""
    # Unknown types will attempt to load as sentence-transformer and likely fail
    # This test just verifies it doesn't crash immediately on the type check
    with pytest.raises(Exception):  # Will fail during actual model loading
        load_embedding_model("some-model", "unsupported-type")
