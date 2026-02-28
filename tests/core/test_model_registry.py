"""Tests for EmbeddingModelRegistry and ModelInfo."""

import pytest

from vector_inspector.core.model_registry import (
    EmbeddingModelRegistry,
    ModelInfo,
    get_model_registry,
)

# ---------------------------------------------------------------------------
# ModelInfo dataclass
# ---------------------------------------------------------------------------


class TestModelInfo:
    def test_to_dict_contains_expected_keys(self):
        m = ModelInfo(
            name="all-MiniLM-L6-v2",
            type="sentence-transformer",
            dimension=384,
            modality="text",
            normalization="cosine",
            source="huggingface",
            description="Compact text model",
        )
        d = m.to_dict()
        assert d["name"] == "all-MiniLM-L6-v2"
        assert d["dimension"] == 384
        assert d["type"] == "sentence-transformer"
        assert d["modality"] == "text"

    def test_from_dict_round_trip(self):
        original = ModelInfo(
            name="test-model",
            type="clip",
            dimension=512,
            modality="multimodal",
            normalization="cosine",
            source="openai",
            description="Test CLIP model",
        )
        recreated = ModelInfo.from_dict(original.to_dict())
        assert recreated.name == original.name
        assert recreated.type == original.type
        assert recreated.dimension == original.dimension
        assert recreated.modality == original.modality


# ---------------------------------------------------------------------------
# EmbeddingModelRegistry
# ---------------------------------------------------------------------------


class TestEmbeddingModelRegistry:
    def test_singleton_returns_same_instance(self):
        r1 = EmbeddingModelRegistry()
        r2 = EmbeddingModelRegistry()
        assert r1 is r2

    def test_get_model_registry_returns_instance(self):
        registry = get_model_registry()
        assert isinstance(registry, EmbeddingModelRegistry)

    def test_get_all_models_returns_list(self):
        registry = get_model_registry()
        models = registry.get_all_models()
        assert isinstance(models, list)

    def test_get_all_dimensions_returns_sorted_list(self):
        registry = get_model_registry()
        dims = registry.get_all_dimensions()
        assert dims == sorted(dims)

    def test_get_models_by_dimension_returns_list(self):
        registry = get_model_registry()
        # 384 is a common dimension present in most known-model json
        models = registry.get_models_by_dimension(384)
        assert isinstance(models, list)

    def test_get_model_by_name_case_insensitive(self):
        registry = get_model_registry()
        all_models = registry.get_all_models()
        if not all_models:
            pytest.skip("No models in registry")
        first = all_models[0]
        found = registry.get_model_by_name(first.name.upper())
        assert found is not None
        assert found.name == first.name

    def test_get_model_by_name_unknown_returns_none(self):
        registry = get_model_registry()
        assert registry.get_model_by_name("definitely-not-a-real-model-xyz") is None

    def test_get_models_by_type_filters_correctly(self):
        registry = get_model_registry()
        st_models = registry.get_models_by_type("sentence-transformer")
        for m in st_models:
            assert m.type == "sentence-transformer"

    def test_get_models_by_source_returns_list(self):
        registry = get_model_registry()
        hf_models = registry.get_models_by_source("huggingface")
        assert isinstance(hf_models, list)

    def test_find_closest_dimension_returns_valid(self):
        registry = get_model_registry()
        dims = registry.get_all_dimensions()
        if not dims:
            pytest.skip("No models in registry")
        # Search for a dimension that doesn't exist → closest should be found
        closest = registry.find_closest_dimension(999999)
        assert closest in dims

    def test_find_closest_dimension_none_when_empty(self, monkeypatch):
        """Returns None when dimension index is empty."""
        registry = get_model_registry()
        # Temporarily clear the index
        original = registry._dimension_index.copy()
        registry._dimension_index.clear()
        result = registry.find_closest_dimension(384)
        registry._dimension_index.update(original)
        assert result is None

    def test_search_models_finds_by_name(self):
        registry = get_model_registry()
        all_models = registry.get_all_models()
        if not all_models:
            pytest.skip("No models in registry")
        # Search for a partial name of first model
        partial = all_models[0].name[:4]
        results = registry.search_models(partial)
        assert isinstance(results, list)

    def test_reload_preserves_models(self):
        registry = get_model_registry()
        count_before = len(registry.get_all_models())
        registry.reload()
        count_after = len(registry.get_all_models())
        assert count_after == count_before
