# Ensure a QApplication exists for QWidget creation during tests
from PySide6.QtWidgets import QApplication

from vector_inspector.ui.views.visualization.histogram_panel import (
    HistogramPanel,
    _CollectionDimScanThread,
    _CompareLoadThread,
)

if QApplication.instance() is None:
    _qapp = QApplication([])


class DummyConnection:
    def __init__(self, name: str):
        self.name = name


def make_data(embeddings):
    return {"embeddings": embeddings, "documents": [], "metadatas": []}


def test_histogram_includes_connection_names(monkeypatch):
    # Primary connection provided
    conn = DummyConnection("LocalConn")

    panel = HistogramPanel()
    panel.set_connection(conn)

    # Primary collection data
    panel.set_data(make_data([[1.0, 0.0], [0.0, 1.0]]), collection_name="test_collection")

    # Prepare comparison data and label (simulate scan result label)
    compare_label = "OtherConn / other_collection"
    # Add option and select it
    panel._compare_options[compare_label] = ("other_collection", DummyConnection("OtherConn"))
    panel.compare_combo.addItem(compare_label)
    panel.compare_combo.setCurrentIndex(0)
    panel._compare_data = make_data([[0.5, 0.5]])

    # Generate histogram (will produce Plotly HTML)
    panel.generate_histogram()

    html = panel.get_current_html()
    assert html is not None
    # Both primary and comparison trace names should include connection prefixes
    assert "LocalConn / test_collection" in html
    assert "OtherConn / other_collection" in html


def test_extract_values_norm_and_dimension():
    panel = HistogramPanel()
    data = make_data([[3.0, 4.0], [0.0, 2.0]])

    # Norm metric
    panel.metric_combo.setCurrentIndex(0)  # Norm
    vals = panel._extract_values(data)
    assert vals == [5.0, 2.0]

    # Dimension metric
    panel.metric_combo.setCurrentIndex(1)  # Dimension
    panel.dim_spin.setValue(1)
    vals2 = panel._extract_values(data)
    assert vals2 == [4.0, 2.0]


def test_on_clear_resets_state():
    panel = HistogramPanel()
    panel.set_data(make_data([[1.0, 0.0]]), collection_name="col")
    panel._compare_data = make_data([[0.5, 0.5]])
    panel._compare_options["X"] = ("other", DummyConnection("Other"))
    panel.compare_combo.addItem("X")

    panel._on_clear()

    assert panel._current_data is None
    assert panel._compare_data is None
    assert not panel.generate_button.isEnabled()


def test_collection_dim_scan_thread_emits_labels():
    # Create two dummy connections that expose the minimal API used by the thread
    class Conn:
        def __init__(self, name, collections, embeddings_map):
            self.name = name
            self._collections = collections
            self._embeddings = embeddings_map

        def list_collections(self):
            return self._collections

        def get_all_items(self, name, limit=None):
            emb = self._embeddings.get(name)
            if emb is None:
                return None
            return {"embeddings": emb}

    c1 = Conn("A", ["c1"], {"c1": [[1.0, 0.0]]})
    c2 = Conn("B", ["c2"], {"c2": [[0.5, 0.5]]})

    results = []

    t = _CollectionDimScanThread([c1, c2], exclude_collection="none", target_dim=2)

    def on_finished(value):
        results.append(value)

    t.finished.connect(on_finished)
    # Call run() directly to avoid creating a real thread
    t.run()

    assert len(results) == 1
    found = results[0]
    # Should contain labels prefixed with connection name
    labels = [lbl for lbl, _, _ in found]
    assert "A / c1" in labels or "B / c2" in labels


def test_compare_load_thread_emits_finished_and_error():
    class ConnGood:
        def get_all_items(self, collection, limit=None):
            return {"embeddings": [[1.0, 0.0]]}

    class ConnBad:
        def get_all_items(self, collection, limit=None):
            return None

    good = ConnGood()
    bad = ConnBad()

    finished_vals = []
    errors = []

    t_good = _CompareLoadThread(good, "c", None)
    t_good.finished.connect(lambda d: finished_vals.append(d))
    t_good.error.connect(lambda e: errors.append(e))
    t_good.run()

    assert len(finished_vals) == 1

    t_bad = _CompareLoadThread(bad, "c", None)
    t_bad.finished.connect(lambda d: finished_vals.append(d))
    t_bad.error.connect(lambda e: errors.append(e))
    t_bad.run()

    assert len(errors) == 1
