from PySide6.QtWidgets import QMessageBox, QWidget

from vector_inspector.ui.views.metadata.metadata_io import (
    export_data,
    import_data,
)


class DummyCtx:
    def __init__(self):
        self.current_collection = None
        self.current_data = None
        self.connection = None


def test_export_no_collection(monkeypatch, qtbot):
    ctx = DummyCtx()
    parent = QWidget()
    qtbot.addWidget(parent)

    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)

    assert export_data(parent, ctx, "json") is False


def test_export_no_data(monkeypatch, qtbot):
    ctx = DummyCtx()
    ctx.current_collection = "col1"
    ctx.current_data = {"ids": []}
    parent = QWidget()
    qtbot.addWidget(parent)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)

    assert export_data(parent, ctx, "json") is False


def test_export_success_json(monkeypatch, tmp_path, qtbot):
    ctx = DummyCtx()
    ctx.current_collection = "col1"
    ctx.current_data = {"ids": ["id1"], "documents": ["d1"]}

    # Patch file dialog to return a path
    monkeypatch.setattr(
        "vector_inspector.ui.views.metadata.metadata_io.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(tmp_path / "out.json"), ""),
    )

    class FakeService:
        def export_to_json(self, data, path):
            return True

    monkeypatch.setattr(
        "vector_inspector.ui.views.metadata.metadata_io.ImportExportService",
        lambda: FakeService(),
    )

    # Patch SettingsService.set to capture directory
    class FakeSettings:
        def __init__(self):
            self._store = {}

        def get(self, key, default=None):
            return ""

        def set(self, key, val):
            self._store[key] = val

    monkeypatch.setattr(
        "vector_inspector.ui.views.metadata.metadata_io.SettingsService",
        lambda: FakeSettings(),
    )

    # Ensure message boxes don't block
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)

    parent = QWidget()
    qtbot.addWidget(parent)
    assert export_data(parent, ctx, "json") is True


def test_import_no_collection(monkeypatch, qtbot):
    ctx = DummyCtx()
    parent = QWidget()
    loading = type("L", (), {"show_loading": lambda *a, **k: None, "hide_loading": lambda *a, **k: None})()
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)
    qtbot.addWidget(parent)
    assert import_data(parent, ctx, "json", loading) is None


def test_import_success(monkeypatch, tmp_path, qtbot):
    ctx = DummyCtx()
    ctx.current_collection = "col1"

    # Fake connection that records add_items call
    class FakeConn:
        def __init__(self):
            self.added = None

        def add_items(self, collection, documents, metadatas=None, ids=None, embeddings=None):
            self.added = (collection, documents)
            return True

    ctx.connection = FakeConn()

    # Patch file dialog to return a path
    p = tmp_path / "in.json"
    p.write_text('{"ids":["id1"], "documents":["d1"]}')
    monkeypatch.setattr(
        "vector_inspector.ui.views.metadata.metadata_io.QFileDialog.getOpenFileName", lambda *a, **k: (str(p), "")
    )

    class FakeService:
        def import_from_json(self, path):
            return {"ids": ["id1"], "documents": ["d1"]}

    monkeypatch.setattr("vector_inspector.ui.views.metadata.metadata_io.ImportExportService", lambda: FakeService())

    # Patch SettingsService to provide get/set
    class FakeSettings2:
        def __init__(self):
            self._store = {}

        def get(self, key, default=None):
            return ""

        def set(self, key, val):
            self._store[key] = val

    monkeypatch.setattr("vector_inspector.ui.views.metadata.metadata_io.SettingsService", lambda: FakeSettings2())

    # Prevent message boxes from showing during tests
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: None)

    loading = type("L", (), {"show_loading": lambda *a, **k: None, "hide_loading": lambda *a, **k: None})()
    parent = QWidget()
    qtbot.addWidget(parent)
    res = import_data(parent, ctx, "json", loading)
    assert res is not None
    assert ctx.connection.added[0] == "col1"
