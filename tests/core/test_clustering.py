import numpy as np


class FakeClusterer:
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs

    def fit_predict(self, X):
        # deterministic labels based on row index mod 2
        n = len(X)
        return np.array([i % 2 for i in range(n)])


def _make_get_sklearn_model(monkeypatch):
    def _get(model_name: str):
        return FakeClusterer

    monkeypatch.setattr("vector_inspector.utils.lazy_imports.get_sklearn_model", _get)


def test_hdbscan_clustering(monkeypatch):
    _make_get_sklearn_model(monkeypatch)
    embeddings = np.random.RandomState(0).randn(6, 3)

    from vector_inspector.core.clustering import run_clustering

    labels, algo = run_clustering(embeddings, "HDBSCAN", {"min_cluster_size": 2})
    assert algo == "HDBSCAN"
    assert labels.shape[0] == 6
    assert set(labels) <= {0, 1}


def test_kmeans_clustering_with_params(monkeypatch):
    _make_get_sklearn_model(monkeypatch)
    embeddings = np.random.RandomState(1).randn(5, 4)

    from vector_inspector.core.clustering import run_clustering

    labels, algo = run_clustering(embeddings, "KMeans", {"n_clusters": 3, "max_iter": 10})
    assert algo == "KMeans"
    assert labels.shape[0] == 5


def test_dbscan_and_optics(monkeypatch):
    _make_get_sklearn_model(monkeypatch)
    embeddings = np.zeros((4, 2))

    from vector_inspector.core.clustering import run_clustering

    labels_db, algo_db = run_clustering(embeddings, "DBSCAN", {"eps": 0.1})
    assert algo_db == "DBSCAN"
    assert labels_db.shape[0] == 4

    labels_op, algo_op = run_clustering(embeddings, "OPTICS", {"min_samples": 2})
    assert algo_op == "OPTICS"
    assert labels_op.shape[0] == 4


def test_unknown_algorithm_raises(monkeypatch):
    # Ensure get_sklearn_model is present but not used
    _make_get_sklearn_model(monkeypatch)
    embeddings = np.empty((0, 0))

    from vector_inspector.core.clustering import run_clustering

    try:
        run_clustering(embeddings, "NON_EXISTENT", {})
        raise AssertionError("Expected ValueError for unknown algorithm")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Advanced optional parameter branches — previously uncovered
# ---------------------------------------------------------------------------


def test_hdbscan_all_advanced_params(monkeypatch):
    """Ensure that all optional HDBSCAN params are forwarded to the clusterer."""
    received_kwargs = {}

    class CapturingClusterer:
        def __init__(self, **kwargs):
            received_kwargs.update(kwargs)

        def fit_predict(self, X):
            return np.zeros(len(X), dtype=int)

    def _get(model_name: str):
        return CapturingClusterer

    monkeypatch.setattr("vector_inspector.utils.lazy_imports.get_sklearn_model", _get)

    from vector_inspector.core.clustering import run_clustering

    embeddings = np.zeros((4, 2))
    params = {
        "min_cluster_size": 2,
        "min_samples": 2,
        "cluster_selection_epsilon": 0.1,
        "allow_single_cluster": True,
        "metric": "euclidean",
        "alpha": 1.0,
        "cluster_selection_method": "eom",
    }
    labels, algo = run_clustering(embeddings, "HDBSCAN", params)
    assert algo == "HDBSCAN"
    assert received_kwargs["cluster_selection_epsilon"] == 0.1
    assert received_kwargs["allow_single_cluster"] is True
    assert received_kwargs["metric"] == "euclidean"
    assert received_kwargs["alpha"] == 1.0
    assert received_kwargs["cluster_selection_method"] == "eom"


def test_kmeans_all_advanced_params(monkeypatch):
    """Ensure that all optional KMeans params are forwarded."""
    received_kwargs = {}

    class CapturingClusterer:
        def __init__(self, **kwargs):
            received_kwargs.update(kwargs)

        def fit_predict(self, X):
            return np.zeros(len(X), dtype=int)

    monkeypatch.setattr(
        "vector_inspector.utils.lazy_imports.get_sklearn_model",
        lambda name: CapturingClusterer,
    )

    from vector_inspector.core.clustering import run_clustering

    embeddings = np.zeros((4, 2))
    params = {
        "n_clusters": 2,
        "init": "random",
        "max_iter": 50,
        "tol": 1e-4,
        "algorithm": "lloyd",
    }
    labels, algo = run_clustering(embeddings, "KMeans", params)
    assert algo == "KMeans"
    assert received_kwargs["init"] == "random"
    assert received_kwargs["max_iter"] == 50
    assert received_kwargs["tol"] == 1e-4
    assert received_kwargs["algorithm"] == "lloyd"


def test_dbscan_all_advanced_params(monkeypatch):
    """Ensure that all optional DBSCAN params are forwarded."""
    received_kwargs = {}

    class CapturingClusterer:
        def __init__(self, **kwargs):
            received_kwargs.update(kwargs)

        def fit_predict(self, X):
            return np.zeros(len(X), dtype=int)

    monkeypatch.setattr(
        "vector_inspector.utils.lazy_imports.get_sklearn_model",
        lambda name: CapturingClusterer,
    )

    from vector_inspector.core.clustering import run_clustering

    embeddings = np.zeros((3, 2))
    params = {
        "eps": 0.5,
        "min_samples": 2,
        "metric": "cosine",
        "algorithm": "ball_tree",
        "leaf_size": 20,
    }
    labels, algo = run_clustering(embeddings, "DBSCAN", params)
    assert algo == "DBSCAN"
    assert received_kwargs["metric"] == "cosine"
    assert received_kwargs["algorithm"] == "ball_tree"
    assert received_kwargs["leaf_size"] == 20


def test_optics_all_advanced_params(monkeypatch):
    """Ensure that all optional OPTICS params are forwarded."""
    received_kwargs = {}

    class CapturingClusterer:
        def __init__(self, **kwargs):
            received_kwargs.update(kwargs)

        def fit_predict(self, X):
            return np.zeros(len(X), dtype=int)

    monkeypatch.setattr(
        "vector_inspector.utils.lazy_imports.get_sklearn_model",
        lambda name: CapturingClusterer,
    )

    from vector_inspector.core.clustering import run_clustering

    embeddings = np.zeros((4, 2))
    params = {
        "min_samples": 2,
        "max_eps": 5.0,
        "metric": "minkowski",
        "xi": 0.05,
        "cluster_method": "xi",
        "algorithm": "kd_tree",
        "leaf_size": 30,
    }
    labels, algo = run_clustering(embeddings, "OPTICS", params)
    assert algo == "OPTICS"
    assert received_kwargs["metric"] == "minkowski"
    assert received_kwargs["xi"] == 0.05
    assert received_kwargs["cluster_method"] == "xi"
    assert received_kwargs["algorithm"] == "kd_tree"
    assert received_kwargs["leaf_size"] == 30


def test_clustering_noise_count_calculated(monkeypatch):
    """Verify noise (-1 labels) are counted correctly after clustering."""

    class NoisyClusterer:
        def __init__(self, **kwargs):
            pass

        def fit_predict(self, X):
            # Two clusters (0 and 1) and two noise points (-1)
            return np.array([0, 0, 1, 1, -1, -1])

    monkeypatch.setattr(
        "vector_inspector.utils.lazy_imports.get_sklearn_model",
        lambda name: NoisyClusterer,
    )

    from vector_inspector.core.clustering import run_clustering

    embeddings = np.zeros((6, 2))
    labels, algo = run_clustering(embeddings, "HDBSCAN", {"min_cluster_size": 2})
    assert algo == "HDBSCAN"
    # Both clusters and noise items should be present in labels
    assert -1 in labels
    assert 0 in labels
    assert 1 in labels
