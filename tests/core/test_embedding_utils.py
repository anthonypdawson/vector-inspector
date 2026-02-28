"""Tests for vector_inspector.core.embedding_utils."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# get_model_for_dimension
# ---------------------------------------------------------------------------


class FakeModelInfo:
    def __init__(self, name, type_, modality="text"):
        self.name = name
        self.type = type_
        self.modality = modality


class FakeRegistry:
    def __init__(self, models_by_dim):
        self._models = models_by_dim

    def get_models_by_dimension(self, dim):
        return self._models.get(dim, [])

    def find_closest_dimension(self, dim):
        dims = list(self._models.keys())
        if not dims:
            return None
        return min(dims, key=lambda d: abs(d - dim))


def _patch_registry(models_by_dim):
    registry = FakeRegistry(models_by_dim)
    return patch("vector_inspector.core.embedding_utils.get_model_registry", return_value=registry)


def test_get_model_for_dimension_single_model():
    """When only one model matches the dimension, it is returned directly."""
    from vector_inspector.core.embedding_utils import get_model_for_dimension

    m = FakeModelInfo("all-MiniLM-L6-v2", "sentence-transformer")
    with _patch_registry({384: [m]}):
        result = get_model_for_dimension(384)
    assert result == ("all-MiniLM-L6-v2", "sentence-transformer")


def test_get_model_for_dimension_multiple_prefer_multimodal():
    """Multiple models + prefer_multimodal=True should pick the clip model."""
    from vector_inspector.core.embedding_utils import get_model_for_dimension

    text_model = FakeModelInfo("all-MiniLM-L6-v2", "sentence-transformer", modality="text")
    clip_model = FakeModelInfo("openai/clip-vit-base-patch32", "clip", modality="multimodal")
    with _patch_registry({512: [text_model, clip_model]}):
        result = get_model_for_dimension(512, prefer_multimodal=True)
    assert result == ("openai/clip-vit-base-patch32", "clip")


def test_get_model_for_dimension_multiple_prefer_multimodal_no_clip():
    """Multiple models + prefer_multimodal=True but no clip → fallback to first."""
    from vector_inspector.core.embedding_utils import get_model_for_dimension

    m1 = FakeModelInfo("model-a", "sentence-transformer", modality="text")
    m2 = FakeModelInfo("model-b", "sentence-transformer", modality="text")
    with _patch_registry({384: [m1, m2]}):
        result = get_model_for_dimension(384, prefer_multimodal=True)
    assert result == ("model-a", "sentence-transformer")


def test_get_model_for_dimension_multiple_prefer_multimodal_false():
    """prefer_multimodal=False should skip CLIP check and return first model."""
    from vector_inspector.core.embedding_utils import get_model_for_dimension

    m1 = FakeModelInfo("model-a", "sentence-transformer")
    m2 = FakeModelInfo("clip-m", "clip", modality="multimodal")
    with _patch_registry({512: [m1, m2]}):
        result = get_model_for_dimension(512, prefer_multimodal=False)
    assert result == ("model-a", "sentence-transformer")


def test_get_model_for_dimension_no_exact_uses_closest():
    """No exact match → find_closest_dimension used, then returns single model."""
    from vector_inspector.core.embedding_utils import get_model_for_dimension

    m = FakeModelInfo("all-MiniLM-L6-v2", "sentence-transformer")
    with _patch_registry({384: [m]}):
        result = get_model_for_dimension(385)  # no exact match for 385
    assert result == ("all-MiniLM-L6-v2", "sentence-transformer")


def test_get_model_for_dimension_no_models_anywhere():
    """When no models exist at all, DEFAULT_MODEL is returned."""
    from vector_inspector.core.embedding_utils import DEFAULT_MODEL, get_model_for_dimension

    with _patch_registry({}):
        result = get_model_for_dimension(999)
    assert result == DEFAULT_MODEL


# ---------------------------------------------------------------------------
# get_available_models_for_dimension
# ---------------------------------------------------------------------------


def test_get_available_models_for_dimension_with_custom_models():
    """Custom models from settings are appended to registry results."""
    from vector_inspector.core.embedding_utils import get_available_models_for_dimension

    m = FakeModelInfo("all-MiniLM-L6-v2", "sentence-transformer")
    m.description = "Efficient text model"

    custom_models = [{"name": "my-custom-model", "type": "sentence-transformer", "description": "My model"}]

    mock_settings = MagicMock()
    mock_settings.get_custom_embedding_models.return_value = custom_models

    registry = FakeRegistry({384: [m]})

    with (
        patch("vector_inspector.core.embedding_utils.get_model_registry", return_value=registry),
        patch(
            "vector_inspector.services.settings_service.SettingsService",
            return_value=mock_settings,
        ),
    ):
        results = get_available_models_for_dimension(384)

    names = [r[0] for r in results]
    assert "all-MiniLM-L6-v2" in names
    assert "my-custom-model" in names
    # Custom model description gets "(custom)" suffix
    custom_entry = next(r for r in results if r[0] == "my-custom-model")
    assert "(custom)" in custom_entry[2]


def test_get_available_models_for_dimension_settings_exception():
    """When SettingsService raises, custom models are silently skipped."""
    from vector_inspector.core.embedding_utils import get_available_models_for_dimension

    m = FakeModelInfo("all-MiniLM-L6-v2", "sentence-transformer")
    m.description = "desc"
    registry = FakeRegistry({384: [m]})

    with (
        patch("vector_inspector.core.embedding_utils.get_model_registry", return_value=registry),
        patch(
            "vector_inspector.services.settings_service.SettingsService",
            side_effect=RuntimeError("no settings"),
        ),
    ):
        results = get_available_models_for_dimension(384)

    assert len(results) == 1
    assert results[0][0] == "all-MiniLM-L6-v2"
