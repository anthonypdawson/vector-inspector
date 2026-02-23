from vector_inspector.ui.views.visualization.histogram_panel import HistogramPanel


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
