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
    """Test encoding with empty embeddings response."""
    with patch('urllib.request.urlopen') as mock_urlopen:
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "embeddings": []
        }).encode('utf-8')
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=None)
        mock_urlopen.return_value = mock_response

        result = encode_text("test", "nomic-embed-text", "ollama")
        assert result == []


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
