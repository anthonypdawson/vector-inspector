import sys
import types

import numpy as np
import pytest

from vector_inspector.core.embedding_providers.clip_provider import CLIPProvider


def test_get_metadata_fallback_when_transformers_missing(monkeypatch):
    # Simulate transformers not installed
    monkeypatch.setitem(sys.modules, "transformers", None)
    with pytest.raises(ImportError):
        CLIPProvider("openai/clip-vit-base-patch32").get_metadata()


def test_get_metadata_with_config(monkeypatch):
    # Provide a fake CLIPConfig with expected attributes
    class FakeTextConfig:
        max_position_embeddings = 128

    class FakeConfig:
        projection_dim = 123
        text_config = FakeTextConfig()

    fake_trans = types.SimpleNamespace(CLIPConfig=types.SimpleNamespace(from_pretrained=lambda name: FakeConfig()))
    monkeypatch.setitem(__import__("sys").modules, "transformers", fake_trans)

    md = CLIPProvider("openai/clip-vit-base-patch32").get_metadata()
    assert md.dimension == 123
    assert md.max_sequence_length == 128


def test_encode_raises_without_torch(monkeypatch):
    prov = CLIPProvider("some-model")
    # Mark loaded so encode attempts to import torch
    prov._is_loaded = True
    prov._processor = object()

    # Ensure torch missing
    monkeypatch.setitem(__import__("sys").modules, "torch", None)

    with pytest.raises(ImportError):
        prov.encode("hello")


def test_similarity_uses_encode(monkeypatch):
    prov = CLIPProvider("m")
    # Prevent warmup from attempting to load heavy models
    prov._is_loaded = True

    # Stub encode to return deterministic arrays sized to the input length
    def fake_encode(inputs, normalize=True, input_type="text"):
        # Strings are single items
        if isinstance(inputs, str) or not isinstance(inputs, (list, tuple)):
            n = 1
        else:
            n = len(inputs)
        return np.tile(np.array([1.0, 0.0]), (n, 1))

    monkeypatch.setattr(prov, "encode", fake_encode)

    # similarity(query, corpus) should compute dot product
    sim = prov.similarity("q", ["a", "b"], query_type="text", corpus_type="text")
    assert sim.shape[0] == 2
