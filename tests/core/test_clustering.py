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
