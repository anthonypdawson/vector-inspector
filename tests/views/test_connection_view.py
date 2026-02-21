def make_fake_connection(success=True, raise_exc=False):
    class Fake:
        def __init__(self):
            self.connected = False

        def connect(self):
            if raise_exc:
                raise RuntimeError("connect fail")
            self.connected = success
            return success

        def list_collections(self):
            if raise_exc:
                raise RuntimeError("list fail")
            return ["c1", "c2"]

        def disconnect(self):
            self.connected = False

    return Fake()


def test_connection_thread_success(monkeypatch):
    mod = __import__("vector_inspector.ui.views.connection_view", fromlist=["*"])
    fake = make_fake_connection(success=True)
    t = mod.ConnectionThread(fake)
    captured = {}

    def on_finished(ok, cols):
        captured["ok"] = ok
        captured["cols"] = cols

    t.finished.connect(on_finished)
    t.run()
    assert captured.get("ok") is True
    assert captured.get("cols") == ["c1", "c2"]


def test_connection_thread_exception(monkeypatch):
    mod = __import__("vector_inspector.ui.views.connection_view", fromlist=["*"])
    fake = make_fake_connection(raise_exc=True)
    t = mod.ConnectionThread(fake)
    captured = {}

    def on_finished(ok, cols):
        captured["ok"] = ok

    t.finished.connect(on_finished)
    t.run()
    assert captured.get("ok") is False


def test_get_connection_config_and_browse(monkeypatch, tmp_path, qtbot):
    mod = __import__("vector_inspector.ui.views.connection_view", fromlist=["*"])
    dialog = mod.ConnectionDialog()
    qtbot.addWidget(dialog)
    # Pinecone branch
    idx = dialog.provider_combo.findData("pinecone")
    dialog.provider_combo.setCurrentIndex(idx)
    dialog.api_key_input.setText("key123")
    cfg = dialog.get_connection_config()
    assert cfg["provider"] == "pinecone"
    assert cfg["api_key"] == "key123"

    # Browse for path: patch QFileDialog in the module namespace (never mutate Shiboken types directly)
    class _FakeQFileDialog:
        @staticmethod
        def getExistingDirectory(*a, **k):
            return str(tmp_path)

    monkeypatch.setattr(mod, "QFileDialog", _FakeQFileDialog)
    dialog.path_input.setText(".")
    dialog._browse_for_path()
    assert dialog.path_input.text() != ""


def test_provider_changes_enable_fields(qtbot):
    mod = __import__("vector_inspector.ui.views.connection_view", fromlist=["*"])
    dialog = mod.ConnectionDialog()
    qtbot.addWidget(dialog)
    # pgvector enables host/port/database fields
    idx = dialog.provider_combo.findData("pgvector")
    dialog.provider_combo.setCurrentIndex(idx)
    dialog._on_provider_changed()
    assert dialog.host_input.isEnabled()
    assert dialog.database_input.isEnabled()


def test_connect_with_config_success(monkeypatch, qtbot):
    mod = __import__("vector_inspector.ui.views.connection_view", fromlist=["*"])

    # Replace real connection classes with simple fakes
    class FakeConn:
        def __init__(self, **kwargs):
            self.host = kwargs.get("host")
            self.port = kwargs.get("port")
            self.path = kwargs.get("path")
            self.is_connected = True

        def connect(self):
            return True

        def list_collections(self):
            return ["x"]

        def disconnect(self):
            self.is_connected = False

    monkeypatch.setattr(mod, "ChromaDBConnection", FakeConn)
    monkeypatch.setattr(mod, "QdrantConnection", FakeConn)
    monkeypatch.setattr(mod, "PgVectorConnection", FakeConn)
    monkeypatch.setattr(mod, "PineconeConnection", FakeConn)

    # Fake thread that immediately emits finished
    class Emittable:
        def __init__(self):
            self._cb = None

        def connect(self, cb):
            self._cb = cb

        def emit(self, *a, **k):
            if self._cb:
                self._cb(*a, **k)

    class FakeThread:
        def __init__(self, connection):
            self.connection = connection
            self.finished = Emittable()

        def start(self):
            try:
                self.finished.emit(True, ["a", "b"])  # type: ignore
            except Exception:
                pass

    # Monkeypatch ConnectionThread used in _connect_with_config
    monkeypatch.setattr(mod, "ConnectionThread", FakeThread)

    view = mod.ConnectionView()
    qtbot.addWidget(view)

    # Connect with chromadb persistent
    cfg = {"provider": "chromadb", "type": "persistent", "path": "./data"}
    view._connect_with_config(cfg)
    # After fake thread, UI should reflect connected
    assert "Connected" in view.status_label.text()


def test_connect_with_config_missing_api_key(monkeypatch, qtbot):
    mod = __import__("vector_inspector.ui.views.connection_view", fromlist=["*"])
    view = mod.ConnectionView()
    qtbot.addWidget(view)

    # QMessageBox is imported lazily inside _connect_with_config, so patch it on
    # the PySide6.QtWidgets module (a Python module object, not a Shiboken type).
    import PySide6.QtWidgets as _qtw

    class _FakeMB:
        @staticmethod
        def warning(*a, **k):
            pass

    monkeypatch.setattr(_qtw, "QMessageBox", _FakeMB)

    # Pinecone without api_key
    view._connect_with_config({"provider": "pinecone", "type": "cloud", "api_key": ""})
    # Loading dialog hidden and no connection created
    assert not getattr(view, "connection", None) or not isinstance(view.connection, mod.PineconeConnection)
