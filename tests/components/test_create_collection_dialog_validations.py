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


def test_accept_rejects_empty_name(monkeypatch):
    dlg = CreateCollectionDialog()

    # Ensure warning is captured instead of showing a dialog
    called = {}

    def fake_warning(*args, **kwargs):
        called["warned"] = True

    monkeypatch.setattr("vector_inspector.ui.components.create_collection_dialog.QMessageBox.warning", fake_warning)

    dlg.name_input.setText("")
    dlg.accept()
    assert called.get("warned", False) is True


def test_accept_rejects_missing_model_when_sample_enabled(monkeypatch):
    _embeddings_available(monkeypatch)
    dlg = CreateCollectionDialog()

    # Clear model list so currentData() is None
    dlg.model_combo.clear()

    called = {}

    def fake_warning(*args, **kwargs):
        called["warned"] = True

    monkeypatch.setattr("vector_inspector.ui.components.create_collection_dialog.QMessageBox.warning", fake_warning)

    dlg.name_input.setText("valid_name")
    dlg.add_sample_check.setChecked(True)
    # No model selected -> should trigger warning
    dlg.accept()
    assert called.get("warned", False) is True
