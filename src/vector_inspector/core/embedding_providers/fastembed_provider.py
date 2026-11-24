"""FastEmbed embedding provider with lazy loading.

FastEmbed runs ONNX models via ONNX Runtime — no torch install, which
is why it is the default for the MCP server (a ``uvx`` install must
stay small). The same model as the old sentence-transformers default,
``all-MiniLM-L6-v2`` (384 dims), so existing collections keep working.

Privacy note: ONNX Runtime 1.29+ ships with telemetry ON by default
on Linux, POSTing trace events (including a persistent device ID) to
Microsoft's 1DS backend. ``ORT_DISABLE_TELEMETRY=1`` — set before
ONNX Runtime initializes — is the only reliable opt-out; the
library's ``disable_telemetry_events()`` call does not stop it, and
an initialization event may already have been emitted by the time it
runs. This provider sets the variable (without overriding an
explicit user setting) before importing fastembed, and the MCP
server CLI sets it for the whole process. To opt back in to ONNX
Runtime telemetry, set ``ORT_DISABLE_TELEMETRY=0`` before launch.
"""

import os

import numpy as np

from .base_provider import EmbeddingMetadata, EmbeddingProvider, Modality, Normalization

# FastEmbed model IDs for bare names the app uses. Names that already
# contain an organisation (``org/model``) are passed through unchanged.
_BARE_NAME_TO_FASTEMBED_ID = {
    "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
    "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2",
    "paraphrase-multilingual-MiniLM-L12-v2": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "bge-small-en-v1.5": "BAAI/bge-small-en-v1.5",
    "bge-base-en-v1.5": "BAAI/bge-base-en-v1.5",
    "bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
    "e5-small-v2": "intfloat/e5-small-v2",
    "e5-base-v2": "intfloat/e5-base-v2",
    "e5-large-v2": "intfloat/e5-large-v2",
    "nomic-embed-text-v1": "nomic-ai/nomic-embed-text-v1",
    "jina-embeddings-v2-small-en": "jinaai/jina-embeddings-v2-small-en",
}


def resolve_fastembed_model_id(model_name: str) -> str:
    """Map the app's bare model name to the FastEmbed model ID.

    FastEmbed model IDs are ``org/model`` (e.g.
    ``sentence-transformers/all-MiniLM-L6-v2``). A name that already
    contains a ``/`` is used as-is; a known bare name is mapped via
    the table above; anything else falls back to the
    ``sentence-transformers/`` organisation and lets FastEmbed raise
    a clear error if the model does not exist.
    """
    if "/" in model_name:
        return model_name
    if model_name in _BARE_NAME_TO_FASTEMBED_ID:
        return _BARE_NAME_TO_FASTEMBED_ID[model_name]
    return f"sentence-transformers/{model_name}"


class FastEmbedProvider(EmbeddingProvider):
    """Provider for FastEmbed (ONNX Runtime) models.

    Lazy-loads the fastembed library and model on first use. FastEmbed
    returns L2-normalized embeddings, so ``normalize`` is accepted but
    has no effect on the returned vectors (they are already unit
    length); the flag is kept for interface compatibility.
    Supports the models FastEmbed ships as ONNX, including:
    - all-MiniLM-L6-v2 (the default, 384 dims)
    - all-mpnet-base-v2
    - BGE, E5 families
    """

    def __init__(self, model_name: str):
        """Initialize the FastEmbed provider.

        Args:
            model_name: Bare model name (``all-MiniLM-L6-v2``) or a
                FastEmbed model ID (``sentence-transformers/all-MiniLM-L6-v2``).
        """
        super().__init__(model_name)
        self._fastembed_model_id = resolve_fastembed_model_id(model_name)
        self._metadata = None

    def get_metadata(self) -> EmbeddingMetadata:
        """Get metadata about the FastEmbed model.

        The dimension comes from FastEmbed's static supported-model
        list, so this does not download or load the model. If the
        model is not in that list, the model is loaded and probed.
        """
        if self._metadata is not None:
            return self._metadata

        dimension = None
        description = f"FastEmbed (ONNX) model: {self.model_name}"
        try:
            from fastembed import TextEmbedding

            for supported in TextEmbedding.list_supported_models():
                if supported["model"] == self._fastembed_model_id:
                    dimension = int(supported["dim"])
                    description = supported.get("description") or description
                    break
        except ImportError:
            raise ImportError("fastembed library not installed. Install with: pip install fastembed")
        except Exception:
            dimension = None

        if dimension is None:
            # Unknown model: load it and probe the dimension with one encode.
            if not self._is_loaded:
                self._load_model()
            probe = self.encode(["probe"], normalize=True)
            dimension = int(probe.shape[1])
            description = f"{description} (dimension probed, not in supported list)"

        self._metadata = EmbeddingMetadata(
            name=self.model_name,
            dimension=dimension,
            modality=Modality.TEXT,
            normalization=Normalization.L2,  # FastEmbed returns normalized vectors
            model_type="fastembed",
            source="huggingface",
            description=description,
        )
        return self._metadata

    def _load_model(self):
        """Load the FastEmbed model (downloads it on first use, ~90 MB)."""
        # ONNX Runtime telemetry is on by default and POSTs to Microsoft;
        # it must be disabled before ONNX Runtime initializes, which
        # happens on the fastembed import below. setdefault keeps an
        # explicit user setting (ORT_DISABLE_TELEMETRY=0 opts back in).
        os.environ.setdefault("ORT_DISABLE_TELEMETRY", "1")
        try:
            from fastembed import TextEmbedding
        except ImportError:
            raise ImportError("fastembed library not installed. Install with: pip install fastembed")

        self._model = TextEmbedding(model_name=self._fastembed_model_id)

    def encode(
        self, inputs: str | list[str], normalize: bool = True, show_progress: bool = False, **kwargs
    ) -> np.ndarray:
        """Encode text inputs into embeddings.

        Args:
            inputs: Single string or list of strings
            normalize: Accepted for interface compatibility; FastEmbed
                already returns L2-normalized vectors.
            show_progress: Ignored (FastEmbed shows no progress bar).
            **kwargs: Accepted for compatibility with callers that pass
                ``show_progress_bar`` (the connection layer's batch path).

        Returns:
            numpy array of embeddings, shape (n_inputs, dimension)
        """
        # Ensure model is loaded
        if not self._is_loaded:
            self.warmup()

        # Convert single string to list
        if isinstance(inputs, str):
            inputs = [inputs]

        # FastEmbed returns a generator of normalized float32 vectors.
        return np.asarray(list(self._model.embed(inputs)), dtype=np.float32)

    def encode_batch(
        self,
        inputs: list[str],
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = True,
        **kwargs,
    ) -> np.ndarray:
        """Encode a large batch of texts efficiently.

        Args:
            inputs: List of strings
            batch_size: Batch size for encoding
            normalize: Accepted for interface compatibility (see encode).
            show_progress: Ignored.
            **kwargs: Accepted for compatibility (see encode).

        Returns:
            numpy array of embeddings
        """
        if not self._is_loaded:
            self.warmup()

        return np.asarray(
            list(self._model.embed(inputs, batch_size=batch_size)),
            dtype=np.float32,
        )

    def similarity(self, query: str | np.ndarray, corpus: list[str]) -> np.ndarray:
        """Compute similarity between query and corpus.

        Args:
            query: Query string or embedding
            corpus: List of corpus strings

        Returns:
            Similarity scores (cosine similarity; embeddings are normalized)
        """
        if not self._is_loaded:
            self.warmup()

        # Get embeddings
        if isinstance(query, str):
            query_emb = self.encode(query, normalize=True)
        else:
            query_emb = query

        corpus_emb = self.encode(corpus, normalize=True)

        # Compute cosine similarity (dot product if normalized)
        return np.dot(corpus_emb, query_emb.T).squeeze()
