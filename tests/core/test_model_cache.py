"""Tests for vector_inspector.core.model_cache."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_valid_cache_entry(cache_dir: Path, model_name: str) -> Path:
    """Create a minimal valid cache directory for *model_name* under *cache_dir*."""
    from vector_inspector.core.model_cache import _sanitize_model_name

    safe_name = _sanitize_model_name(model_name)
    model_dir = cache_dir / safe_name
    model_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "original_name": model_name,
        "model_type": "sentence-transformer",
        "cached_at": "2024-01-01T00:00:00",
        "last_accessed": "2024-01-01T00:00:00",
    }
    (model_dir / "cache_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    return model_dir


# ---------------------------------------------------------------------------
# get_cache_dir
# ---------------------------------------------------------------------------


def test_get_cache_dir_uses_custom_dir_from_settings(tmp_path):
    """get_cache_dir returns custom path when SettingsService provides one."""
    from vector_inspector.core import model_cache

    custom_dir = str(tmp_path / "custom_embed_cache")
    mock_settings = MagicMock()
    mock_settings.get.return_value = custom_dir

    with patch("vector_inspector.services.settings_service.SettingsService", return_value=mock_settings):
        result = model_cache.get_cache_dir()

    assert result == Path(custom_dir)


def test_get_cache_dir_falls_back_to_default_when_no_custom(tmp_path, monkeypatch):
    """get_cache_dir uses default dir when SettingsService returns None."""
    from vector_inspector.core import model_cache

    mock_settings = MagicMock()
    mock_settings.get.return_value = None  # no custom dir configured

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path / "default")

    with patch("vector_inspector.services.settings_service.SettingsService", return_value=mock_settings):
        result = model_cache.get_cache_dir()

    assert "default" in str(result)


# ---------------------------------------------------------------------------
# save_model_to_cache
# ---------------------------------------------------------------------------


def test_save_model_to_cache_cache_disabled(tmp_path, monkeypatch):
    """save_model_to_cache returns False immediately when cache is disabled."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: False)

    model = MagicMock()
    result = model_cache.save_model_to_cache(model, "test-model", "sentence-transformer")
    assert result is False


def test_save_model_to_cache_save_pretrained(tmp_path, monkeypatch):
    """save_model_to_cache uses save_pretrained when available (method 1)."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    class FakeModel:
        def save_pretrained(self, path: str):
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            (p / "config.json").write_text("{}", encoding="utf-8")

    result = model_cache.save_model_to_cache(FakeModel(), "pretrained-model", "sentence-transformer")
    assert result is True
    assert model_cache.is_cached("pretrained-model")


def test_save_model_to_cache_save_method(tmp_path, monkeypatch):
    """save_model_to_cache falls back to .save() when no save_pretrained (method 2)."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    class FakeModelWithSave:
        def save(self, path: str):
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            (p / "config.json").write_text("{}", encoding="utf-8")

    result = model_cache.save_model_to_cache(FakeModelWithSave(), "save-method-model", "custom")
    assert result is True


def test_save_model_to_cache_tuple_clip(tmp_path, monkeypatch):
    """save_model_to_cache handles (model, processor) CLIP tuple (method 3)."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    class FakeClipModel:
        def save_pretrained(self, path: str):
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            (p / "config.json").write_text("{}", encoding="utf-8")

    class FakeProcessor:
        def save_pretrained(self, path: str):
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            (p / "preprocessor_config.json").write_text("{}", encoding="utf-8")

    result = model_cache.save_model_to_cache((FakeClipModel(), FakeProcessor()), "openai/clip-test", "clip")
    assert result is True
    assert model_cache.is_cached("openai/clip-test")


def test_save_model_to_cache_no_save_method(tmp_path, monkeypatch):
    """save_model_to_cache returns False when model has no save mechanism."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    class NoSaveModel:
        pass  # no save_pretrained, no save

    result = model_cache.save_model_to_cache(NoSaveModel(), "no-save-model", "other")
    assert result is False


# ---------------------------------------------------------------------------
# load_cached_path
# ---------------------------------------------------------------------------


def test_load_cached_path_returns_path_and_updates_access_time(tmp_path, monkeypatch):
    """load_cached_path returns the cache path and updates last_accessed metadata."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    model_dir = _make_valid_cache_entry(tmp_path, "my-cached-model")

    result = model_cache.load_cached_path("my-cached-model")
    assert result is not None
    assert result == model_dir

    # Access time should have been updated in metadata
    metadata = json.loads((model_dir / "cache_metadata.json").read_text(encoding="utf-8"))
    assert "last_accessed" in metadata


def test_load_cached_path_returns_none_when_not_cached(tmp_path, monkeypatch):
    """load_cached_path returns None when model is not cached."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    result = model_cache.load_cached_path("nonexistent-model")
    assert result is None


def test_load_cached_path_returns_none_when_cache_disabled(tmp_path, monkeypatch):
    """load_cached_path returns None immediately when cache is disabled."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: False)

    _make_valid_cache_entry(tmp_path, "my-model")

    result = model_cache.load_cached_path("my-model")
    assert result is None


# ---------------------------------------------------------------------------
# clear_cache
# ---------------------------------------------------------------------------


def test_clear_cache_specific_model(tmp_path, monkeypatch):
    """clear_cache removes only the specified model directory."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    model_dir = _make_valid_cache_entry(tmp_path, "remove-me")
    other_dir = _make_valid_cache_entry(tmp_path, "keep-me")

    result = model_cache.clear_cache("remove-me")
    assert result is True
    assert not model_dir.exists()
    assert other_dir.exists()


def test_clear_cache_nonexistent_model(tmp_path, monkeypatch):
    """clear_cache with absent model name returns True without error."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    result = model_cache.clear_cache("ghost-model")
    assert result is True


def test_clear_cache_all(tmp_path, monkeypatch):
    """clear_cache with no model_name clears everything."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    _make_valid_cache_entry(tmp_path, "model-a")
    _make_valid_cache_entry(tmp_path, "model-b")

    result = model_cache.clear_cache()
    assert result is True
    assert not tmp_path.exists()


# ---------------------------------------------------------------------------
# get_cache_info
# ---------------------------------------------------------------------------


def test_get_cache_info_no_cache_dir(tmp_path, monkeypatch):
    """get_cache_info returns exists=False when cache dir doesn't exist."""
    from vector_inspector.core import model_cache

    nonexistent = tmp_path / "no_cache_here"
    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: nonexistent)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    info = model_cache.get_cache_info()
    assert info["exists"] is False
    assert info["model_count"] == 0


def test_get_cache_info_with_models(tmp_path, monkeypatch):
    """get_cache_info returns correct counts when models are cached."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    _make_valid_cache_entry(tmp_path, "model-x")
    _make_valid_cache_entry(tmp_path, "model-y")

    info = model_cache.get_cache_info()
    assert info["exists"] is True
    assert info["model_count"] == 2
    assert info["total_size_mb"] >= 0
    assert info["enabled"] is True


def test_get_cache_info_empty_dir(tmp_path, monkeypatch):
    """get_cache_info with existing but empty dir returns model_count=0."""
    from vector_inspector.core import model_cache

    monkeypatch.setattr(model_cache, "_get_default_cache_dir", lambda: tmp_path)
    monkeypatch.setattr(model_cache, "is_cache_enabled", lambda: True)

    # Cache dir exists but has no valid model entries
    tmp_path.mkdir(exist_ok=True)

    info = model_cache.get_cache_info()
    assert info["exists"] is True
    assert info["model_count"] == 0
