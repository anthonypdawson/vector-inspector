from PySide6.QtWidgets import QApplication

from vector_inspector.core.provider_detection import FeatureInfo
from vector_inspector.ui.components.create_collection_dialog import CreateCollectionDialog

if QApplication.instance() is None:
    _qapp = QApplication([])


def _embeddings_available(monkeypatch):
    """Pretend the embeddings feature is installed.

    Toggling the sample-data checkbox opens a modal ProviderInstallDialog
    when embeddings are missing, which blocks forever in a headless test
    (nobody dismisses it). Stub the feature check so the dialog never opens
    and the test exercises the dialog's own state logic.
    """
    monkeypatch.setattr(
        "vector_inspector.core.provider_detection.get_feature_info",
        lambda feature_id: (
            FeatureInfo(
                id="embeddings",
                name="Text Embeddings",
                available=True,
                install_command="pip install vector-inspector[embeddings]",
                description="Generate embeddings for semantic search",
            )
            if feature_id == "embeddings"
            else None
        ),
    )


class DummyConnection:
    def __init__(self, name):
        self.name = name


def test_dialog_initial_connection_label():
    dlg = CreateCollectionDialog()
    # Initially no connection
    assert dlg.connection_label.text() == "(no connection)"


def test_dialog_updates_connection_label_on_set():
    dlg = CreateCollectionDialog()
    conn = DummyConnection("TestConn")
    dlg.set_connection(conn)
    assert dlg.connection_label.text() == "TestConn"


def test_sample_options_enable_and_random_flag(monkeypatch):
    _embeddings_available(monkeypatch)
    dlg = CreateCollectionDialog()

    # By default sample options are disabled
    assert not dlg.count_spin.isEnabled()
    assert not dlg.random_data_checkbox.isEnabled()

    # Enable sample data and check options become enabled
    dlg.add_sample_check.setChecked(True)
    assert dlg.count_spin.isEnabled()
    assert dlg.random_data_checkbox.isEnabled()

    # Default random_data should be True
    cfg = dlg.get_configuration()
    assert cfg["add_sample"] is True
    assert cfg["random_data"] is True

    # Toggle random flag and verify configuration reflects it
    dlg.random_data_checkbox.setChecked(False)
    cfg2 = dlg.get_configuration()
    assert cfg2["random_data"] is False
