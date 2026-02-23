from PySide6.QtWidgets import QApplication

from vector_inspector.ui.components.create_collection_dialog import CreateCollectionDialog

if QApplication.instance() is None:
    _qapp = QApplication([])


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


def test_sample_options_enable_and_random_flag():
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
