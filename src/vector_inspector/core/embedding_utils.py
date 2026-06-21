"""Utilities for managing embedding models and vector dimensions."""

from __future__ import annotations  # Allows us to use class names in typehints while lazyloading

from typing import Any

# Lazy import: see below
from vector_inspector.core.logging import log_info
from vector_inspector.core.model_registry import get_model_registry

# Default model to use when dimension is unknown or not mapped
DEFAULT_MODEL = ("all-MiniLM-L6-v2", "sentence-transformer")


def _get_dimension_to_model_dict():
    """Build dimension->models dictionary from registry.

    Returns:
        Dict mapping dimension to list of (name, type, description) tuples
    """
    registry = get_model_registry()
    dimension_map = {}

    for dimension in registry.get_all_dimensions():
        models = registry.get_models_by_dimension(dimension)
        dimension_map[dimension] = [(m.name, m.type, m.description) for m in models]

    return dimension_map


# For backward compatibility - dynamically loads from registry
DIMENSION_TO_MODEL = _get_dimension_to_model_dict()


def get_model_for_dimension(dimension: int, prefer_multimodal: bool = True) -> tuple[str, str]:
    """
    Get the appropriate embedding model name and type for a given vector dimension.

    Args:
        dimension: The vector dimension size
        prefer_multimodal: If True and multiple models exist for this dimension,
                          prefer multi-modal (CLIP) over text-only models

    Returns:
        Tuple of (model_name, model_type) where model_type is "sentence-transformer" or "clip"
    """
    registry = get_model_registry()
    models = registry.get_models_by_dimension(dimension)

    if not models:
        # Find the closest dimension if exact match not found
        closest_dim = registry.find_closest_dimension(dimension)
        if closest_dim:
            models = registry.get_models_by_dimension(closest_dim)

    if not models:
        return DEFAULT_MODEL

    if len(models) == 1:
        return (models[0].name, models[0].type)

    # Multiple models available - apply preference
    if prefer_multimodal:
        # Prefer CLIP/multimodal
        for model in models:
            if model.modality == "multimodal" or model.type == "clip":
                return (model.name, model.type)

    # Default to first option
    return (models[0].name, models[0].type)


def get_available_models_for_dimension(dimension: int) -> list:
    """
    Get all available model options for a given dimension.
    Includes both predefined (from registry) and custom user-added models.

    Args:
        dimension: The vector dimension size

    Returns:
        List of tuples: [(model_name, model_type, description), ...]
    """
    # Start with models from registry
    registry = get_model_registry()
    registry_models = registry.get_models_by_dimension(dimension)
    models = [(m.name, m.type, m.description) for m in registry_models]

    # Add custom models from settings
    try:
        from vector_inspector.services.settings_service import SettingsService

        settings = SettingsService()
        custom_models = settings.get_custom_embedding_models(dimension)

        for model in custom_models:
            # Format: (model_name, model_type, description)
            models.append((model["name"], model["type"], f"{model['description']} (custom)"))
    except Exception as e:
        log_info("Warning: Could not load custom models: %s", e)

    return models


def load_embedding_model(model_name: str, model_type: str) -> SentenceTransformer | Any:
    """
    Load an embedding model (sentence-transformer, CLIP, or Ollama).

    Uses disk cache when available to speed up repeated loads.

    Args:
        model_name: Name of the model to load
        model_type: Type of model ("sentence-transformer", "clip", or "ollama")

    Returns:
        Loaded model (SentenceTransformer, CLIP model, or Ollama client stub)
    """
    from vector_inspector.core.model_cache import (
        is_cache_enabled,
        load_cached_path,
        save_model_to_cache,
    )

    # Ollama models don't need loading - just return the model name
    if model_type == "ollama":
        log_info(f"Using Ollama model: {model_name}")
        return model_name  # Return model name as-is for Ollama

    # Try to load from cache first
    cached_path = load_cached_path(model_name)

    if model_type == "clip":
        # Delegate to the shared, thread-safe in-memory cache in lazy_imports so
        # that the ingestion code path and the search code path always receive the
        # same model object and loading never races across QThreads (which can
        # corrupt torch_cpu.dll native state and cause a silent access-violation
        # crash).  Disk-cache saving for cold-start speed-up is skipped here
        # because the in-memory cache already handles within-process reuse.
        from vector_inspector.utils.lazy_imports import get_clip_model_and_processor

        return get_clip_model_and_processor(model_name)
    from sentence_transformers import SentenceTransformer

    if cached_path:
        try:
            # Load from cache
            model = SentenceTransformer(str(cached_path))
            log_info(f"Loaded sentence-transformer from cache: {model_name}")
            return model
        except Exception as e:
            log_info(f"Failed to load from cache, downloading: {e}")

    # Load from HuggingFace
    model = SentenceTransformer(model_name)

    # Cache for future use
    if is_cache_enabled():
        save_model_to_cache(model, model_name, model_type)

    # Returns a SentenceTransformer instance
    return model


def encode_text(text: str, model: SentenceTransformer | tuple | str, model_type: str) -> list:
    """
    Encode text using the appropriate model.

    Args:
        text: Text to encode
        model: The loaded model (SentenceTransformer, (CLIPModel, CLIPProcessor) tuple, or Ollama model name)
        model_type: Type of model ("sentence-transformer", "clip", or "ollama")

    Returns:
        Embedding vector as a list
    """
    if model_type == "ollama":
        import json
        import os
        import urllib.request

        # model is the model name string for Ollama
        # Use HTTP API directly (no extra dependencies needed)
        base_url = "http://localhost:11434"
        url = f"{base_url}/api/embed"

        # Allow timeout override via environment variable (default: 30s)
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "30"))

        data = json.dumps({"model": model, "input": text}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                embeddings = result.get("embeddings", [])
                if not embeddings:
                    raise RuntimeError(f"Ollama returned no embeddings for model {model}")
                return embeddings[0]
        except Exception as e:
            from vector_inspector.core.logging import log_tracked_error
            log_tracked_error(
                "Ollama embedding failed: %s. Ensure Ollama is running (http://localhost:11434)",
                e,
                category="embedding",
                operation="ollama_embed",
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise RuntimeError(f"Failed to get embedding from Ollama: {e}") from e

    if model_type == "clip":
        import torch

        clip_model, processor = model
        inputs = processor(text=[text], return_tensors="pt", padding=True)
        with torch.no_grad():
            text_features = clip_model.get_text_features(**inputs)
        # Some HuggingFace CLIP variants return BaseModelOutputWithPooling instead of
        # a raw tensor.  Unwrap to the pooled tensor before normalising.
        if not isinstance(text_features, torch.Tensor):
            if hasattr(text_features, "pooler_output") and text_features.pooler_output is not None:
                text_features = text_features.pooler_output
            elif hasattr(text_features, "last_hidden_state"):
                text_features = text_features.last_hidden_state[:, 0]
            else:
                raise TypeError(
                    f"CLIP get_text_features returned unexpected type {type(text_features).__name__}; "
                    "expected a Tensor or BaseModelOutputWithPooling"
                )
        # Normalize the features (CLIP embeddings are typically normalized)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
        return text_features[0].cpu().numpy().tolist()
    # sentence-transformer
    # Lazy import for type hint only
    # from sentence_transformers import SentenceTransformer
    embedding = model.encode(text)
    return embedding.tolist()


def get_embedding_model_for_dimension(
    dimension: int,
) -> tuple[SentenceTransformer | tuple, str, str]:
    """
    Get a loaded embedding model for a specific dimension.

    Args:
        dimension: The vector dimension size

    Returns:
        Tuple of (loaded_model, model_name, model_type)
    """
    model_name, model_type = get_model_for_dimension(dimension)
    model = load_embedding_model(model_name, model_type)
    # Returns a tuple: (loaded_model, model_name, model_type)
    return (model, model_name, model_type)
