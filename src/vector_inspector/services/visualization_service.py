"""Visualization service for dimensionality reduction."""

from typing import Any
import warnings
from vector_inspector.core.logging import log_error


class VisualizationService:
    """Service for vector dimensionality reduction and visualization."""

    @staticmethod
    def reduce_dimensions(
        embeddings: list[list[float]], method: str = "pca", n_components: int = 2, **kwargs
    ) -> Any | None:
        """
        Reduce dimensionality of embeddings.

        Args:
            embeddings: List of embedding vectors
            method: Reduction method ('pca', 'tsne', or 'umap')
            n_components: Target number of dimensions (2 or 3)
            **kwargs: Additional method-specific parameters

        Returns:
            Reduced embeddings as numpy array, or None if failed
        """
        if embeddings is None or len(embeddings) == 0:
            return None

        try:
            # Lazy import numpy and models
            from vector_inspector.utils.lazy_imports import get_numpy, get_sklearn_model

            np = get_numpy()

            X = np.array(embeddings)

            if method.lower() == "pca":
                PCA = get_sklearn_model("PCA")
                reducer = PCA(n_components=n_components)
                reduced = reducer.fit_transform(X)

            elif method.lower() in ["t-sne", "tsne"]:
                TSNE = get_sklearn_model("TSNE")
                perplexity = kwargs.get("perplexity", min(30, len(embeddings) - 1))
                reducer = TSNE(n_components=n_components, perplexity=perplexity, random_state=42)
                reduced = reducer.fit_transform(X)

            elif method.lower() == "umap":
                UMAP = get_sklearn_model("UMAP")
                n_neighbors = kwargs.get("n_neighbors", min(15, len(embeddings) - 1))
                # Suppress n_jobs warning when using random_state
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=".*n_jobs.*overridden.*")
                    reducer = UMAP(
                        n_components=n_components, n_neighbors=n_neighbors, random_state=42
                    )
                    reduced = reducer.fit_transform(X)

            else:
                log_error("Unknown method: %s", method)
                return None

            return reduced

        except Exception as e:
            log_error("Dimensionality reduction failed: %s", e)
            return None

    @staticmethod
    def prepare_plot_data(
        reduced_embeddings: Any,
        labels: list[str] | None = None,
        metadata: list[dict] | None = None,
        color_by: str | None = None,
    ) -> tuple[Any, list[str], list[str]]:
        """
        Prepare data for plotting.

        Args:
            reduced_embeddings: Reduced dimension embeddings
            labels: Text labels for each point
            metadata: Metadata dictionaries for each point
            color_by: Metadata field to use for coloring

        Returns:
            Tuple of (embeddings, labels, colors)
        """
        n_points = len(reduced_embeddings)

        # Prepare labels
        if labels is None:
            labels = [f"Point {i}" for i in range(n_points)]

        # Prepare colors
        colors = ["blue"] * n_points
        if color_by and metadata:
            unique_values = set()
            values = []
            for meta in metadata:
                value = meta.get(color_by, "unknown")
                values.append(str(value))
                unique_values.add(str(value))

            # Map values to colors
            color_map = {}
            color_palette = [
                "red",
                "blue",
                "green",
                "orange",
                "purple",
                "cyan",
                "magenta",
                "yellow",
                "pink",
                "brown",
            ]
            for i, val in enumerate(sorted(unique_values)):
                color_map[val] = color_palette[i % len(color_palette)]

            colors = [color_map[val] for val in values]

        return reduced_embeddings, labels, colors
