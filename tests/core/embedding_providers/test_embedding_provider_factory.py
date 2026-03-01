"""Tests for the embedding ProviderFactory."""

from unittest.mock import MagicMock, patch

import pytest

from vector_inspector.core.embedding_providers.provider_factory import ProviderFactory


class TestProviderFactoryCreate:
    def test_sentence_transformer_explicit(self):
        MockST = MagicMock(return_value=MagicMock())
        with patch.dict(ProviderFactory._PROVIDER_REGISTRY, {"sentence-transformer": MockST}):
            ProviderFactory.create("all-MiniLM-L6-v2", model_type="sentence-transformer")
            MockST.assert_called_once_with("all-MiniLM-L6-v2")

    def test_clip_explicit(self):
        MockCLIP = MagicMock(return_value=MagicMock())
        with patch.dict(ProviderFactory._PROVIDER_REGISTRY, {"clip": MockCLIP}):
            ProviderFactory.create("openai/clip-vit-base-patch32", model_type="clip")
            MockCLIP.assert_called_once_with("openai/clip-vit-base-patch32")

    def test_unknown_type_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown provider type"):
            ProviderFactory.create("some-model", model_type="unsupported-type")

    def test_cloud_provider_raises_not_implemented(self):
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            ProviderFactory.create("text-embedding-ada-002", model_type="openai")

    def test_auto_detect_via_registry(self, monkeypatch):
        mock_model_info = MagicMock()
        mock_model_info.type = "sentence-transformer"
        mock_registry = MagicMock()
        mock_registry.get_model_by_name.return_value = mock_model_info

        monkeypatch.setattr(
            "vector_inspector.core.embedding_providers.provider_factory.get_model_registry",
            lambda: mock_registry,
        )
        MockST = MagicMock(return_value=MagicMock())
        with patch.dict(ProviderFactory._PROVIDER_REGISTRY, {"sentence-transformer": MockST}):
            ProviderFactory.create("all-MiniLM-L6-v2")
            MockST.assert_called_once_with("all-MiniLM-L6-v2")

    def test_auto_detect_via_pattern_clip(self, monkeypatch):
        mock_registry = MagicMock()
        mock_registry.get_model_by_name.return_value = None

        monkeypatch.setattr(
            "vector_inspector.core.embedding_providers.provider_factory.get_model_registry",
            lambda: mock_registry,
        )
        MockCLIP = MagicMock(return_value=MagicMock())
        with patch.dict(ProviderFactory._PROVIDER_REGISTRY, {"clip": MockCLIP}):
            ProviderFactory.create("openai/clip-model-v1")
            MockCLIP.assert_called_once()

    def test_auto_detect_via_pattern_sentence_transformer(self, monkeypatch):
        mock_registry = MagicMock()
        mock_registry.get_model_by_name.return_value = None

        monkeypatch.setattr(
            "vector_inspector.core.embedding_providers.provider_factory.get_model_registry",
            lambda: mock_registry,
        )
        MockST = MagicMock(return_value=MagicMock())
        with patch.dict(ProviderFactory._PROVIDER_REGISTRY, {"sentence-transformer": MockST}):
            ProviderFactory.create("sentence-transformers/all-MiniLM-L6-v2")
            MockST.assert_called_once()

    def test_auto_detect_hf_slash_model(self, monkeypatch):
        """A model with a slash that is not an http URL defaults to sentence-transformer."""
        mock_registry = MagicMock()
        mock_registry.get_model_by_name.return_value = None

        monkeypatch.setattr(
            "vector_inspector.core.embedding_providers.provider_factory.get_model_registry",
            lambda: mock_registry,
        )
        MockST = MagicMock(return_value=MagicMock())
        with patch.dict(ProviderFactory._PROVIDER_REGISTRY, {"sentence-transformer": MockST}):
            # Pattern: no known pattern but has "/" and not http
            ProviderFactory.create("some-org/novel-embedding-model")
            MockST.assert_called_once()

    def test_detect_unknown_raises_value_error(self, monkeypatch):
        mock_registry = MagicMock()
        mock_registry.get_model_by_name.return_value = None

        monkeypatch.setattr(
            "vector_inspector.core.embedding_providers.provider_factory.get_model_registry",
            lambda: mock_registry,
        )
        with pytest.raises(ValueError, match="Cannot auto-detect"):
            ProviderFactory.create("completely-unknown-model-xyz123")
