"""Tests for the FastEmbed embedding provider.

The model-id resolution and DEFAULT_MODEL tests need no model
download. The encode/metadata tests use the real all-MiniLM-L6-v2
ONNX model (downloads ~90 MB on first use) and skip when fastembed
is not installed.
"""

import importlib.util

import numpy as np
import pytest

from vector_inspector.core.embedding_providers.fastembed_provider import (
    FastEmbedProvider,
    resolve_fastembed_model_id,
)
from vector_inspector.core.embedding_utils import DEFAULT_MODEL, encode_text

FASTEmbed_AVAILABLE = importlib.util.find_spec("fastembed") is not None
needs_fastembed = pytest.mark.skipif(not FASTEmbed_AVAILABLE, reason="fastembed not installed")


class TestResolveFastembedModelId:
    def test_known_bare_name_maps_to_org(self):
        assert resolve_fastembed_model_id("all-MiniLM-L6-v2") == "sentence-transformers/all-MiniLM-L6-v2"

    def test_slash_name_passes_through(self):
        assert resolve_fastembed_model_id("BAAI/bge-small-en-v1.5") == "BAAI/bge-small-en-v1.5"

    def test_unknown_bare_name_gets_sentence_transformers_prefix(self):
        assert resolve_fastembed_model_id("some-model") == "sentence-transformers/some-model"


class TestDefaultModel:
    def test_default_model_is_sentence_transformer(self):
        # Reverted from fastembed: the default stays sentence-transformer
        # (fastembed remains available for explicit use via the provider factory).
        assert DEFAULT_MODEL == ("all-MiniLM-L6-v2", "sentence-transformer")


@needs_fastembed
class TestFastEmbedProviderRealModel:
    def test_get_metadata_dim_without_loading(self):
        provider = FastEmbedProvider("all-MiniLM-L6-v2")
        metadata = provider.get_metadata()
        assert metadata.dimension == 384
        assert metadata.model_type == "fastembed"
        assert not provider._is_loaded, "get_metadata must not load the model"

    def test_encode_shape_and_norms(self):
        provider = FastEmbedProvider("all-MiniLM-L6-v2")
        embeddings = provider.encode(["hello world", "vector databases"])
        assert embeddings.shape == (2, 384)
        assert embeddings.dtype == np.float32
        norms = np.linalg.norm(embeddings, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-5)

    def test_encode_single_string_returns_one_row(self):
        # Provider contract is shape (n, dim) even for one string;
        # callers that want a flat vector (encode_text) take row 0.
        provider = FastEmbedProvider("all-MiniLM-L6-v2")
        embeddings = provider.encode("hello world")
        assert embeddings.shape == (1, 384)

    def test_encode_accepts_show_progress_bar_kwarg(self):
        # The connection layer's batch path passes this kwarg.
        provider = FastEmbedProvider("all-MiniLM-L6-v2")
        embeddings = provider.encode(["hello world"], show_progress_bar=False)
        assert embeddings.shape == (1, 384)

    def test_encode_text_returns_flat_vector(self):
        # encode_text is what the Chroma query path uses: it must
        # return a flat 384-float list, not a nested [[...]].
        provider = FastEmbedProvider("all-MiniLM-L6-v2")
        vector = encode_text("hello world", provider, "fastembed")
        assert isinstance(vector, list)
        assert len(vector) == 384
        assert all(isinstance(x, float) for x in vector)
