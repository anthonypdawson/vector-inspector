import os

from PySide6.QtCore import Qt


class FakeBackupService:
    def __init__(self, backups=None):
        self._backups = backups or []

    def list_backups(self, backup_dir):
        return list(self._backups)

    def delete_backup(self, path):
        # pretend deletion succeeds when path matches one of stored backups
        return any(b["file_path"] == path for b in self._backups)


class FakeSettingsService:
    def __init__(self, initial=None):
        self._store = dict(initial or {})
        self.set_calls = []

    def get(self, key, default=None):
        return self._store.get(key, default)

    def set(self, key, value):
        self.set_calls.append((key, value))
        self._store[key] = value


class FakeConnection:
    def __init__(self, name="db1", collections=None):
        self.name = name
        self.database = self  # simplified
        self.collections = collections or []

    def list_collections(self):
        return list(self.collections)


def make_dialog(monkeypatch, qtbot, backups=None, settings_initial=None, collection_name=""):
    # Patch BackupRestoreService and SettingsService in module
    import vector_inspector.ui.components.backup_restore_dialog as brd

    fake_backup_service = FakeBackupService(backups=backups)
    fake_settings = FakeSettingsService(initial=settings_initial)

    monkeypatch.setattr(brd, "BackupRestoreService", lambda: fake_backup_service)
    monkeypatch.setattr(brd, "SettingsService", lambda: fake_settings)

    # Patch LoadingDialog to a no-op class to avoid UI blocking
    class NoopLoading:
        def __init__(self, *args, **kwargs):
            pass

        def show_loading(self, *a, **k):
            pass

        def hide_loading(self):
            pass

    monkeypatch.setattr(brd, "LoadingDialog", NoopLoading)

    # Patch QMessageBox to safe no-op defaults to avoid modal popups
    monkeypatch.setattr(brd.QMessageBox, "warning", lambda *a, **k: None)
    monkeypatch.setattr(brd.QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(brd.QMessageBox, "question", lambda *a, **k: brd.QMessageBox.StandardButton.No)

    conn = FakeConnection()
    dlg = brd.BackupRestoreDialog(conn, collection_name=collection_name)
    qtbot.addWidget(dlg)
    return dlg, fake_backup_service, fake_settings


def test_refresh_backups_list_no_backups(monkeypatch, qtbot):
    dlg, service, settings = make_dialog(monkeypatch, qtbot, backups=[], settings_initial={})
    # After init, backups_list should show the no-backups item
    assert dlg.backups_list.count() == 1
    item = dlg.backups_list.item(0)
    assert "No backups found" in item.text()


def test_refresh_backups_list_with_backups(monkeypatch, qtbot):
    sample = {
        "collection_name": "colA",
        "timestamp": "2026-01-01T00:00:00",
        "item_count": 10,
        "file_name": "colA.zip",
        "file_path": os.path.join(os.getcwd(), "colA.zip"),
        "file_size": 1024 * 1024 * 2,
    }
    dlg, service, settings = make_dialog(monkeypatch, qtbot, backups=[sample], settings_initial={})
    assert dlg.backups_list.count() == 1
    item = dlg.backups_list.item(0)
    assert "colA" in item.text()
    assert item.data(Qt.ItemDataRole.UserRole) == sample["file_path"]


def test_select_backup_dir_updates_settings_and_refresh(monkeypatch, qtbot):
    # Patch QFileDialog to return a chosen directory
    import vector_inspector.ui.components.backup_restore_dialog as brd

    monkeypatch.setattr(brd.QFileDialog, "getExistingDirectory", lambda *a, **k: os.getcwd())

    dlg, service, settings = make_dialog(monkeypatch, qtbot, backups=[], settings_initial={})
    # Call select backup dir
    dlg._select_backup_dir()
    # backup_dir should be updated to cwd and settings.set called
    assert dlg.backup_dir == os.getcwd()
    assert ("backup_directory", os.getcwd()) in settings.set_calls


def test_create_backup_no_collection_shows_warning(monkeypatch, qtbot):
    # When no collection is selected, creating backup should warn and not start thread
    dlg, service, settings = make_dialog(monkeypatch, qtbot, backups=[], settings_initial={}, collection_name="")

    called = {}

    def fake_warning(parent, title, msg):
        called["warn"] = (title, msg)

    import vector_inspector.ui.components.backup_restore_dialog as brd

    monkeypatch.setattr(brd.QMessageBox, "warning", lambda *a, **k: fake_warning(*a, **k))

    dlg._create_backup()
    assert "warn" in called
    assert "No collection selected" in called["warn"][1]


def test_on_backup_selected_enables_buttons(monkeypatch, qtbot):
    sample = {
        "collection_name": "colA",
        "timestamp": "2026-01-01T00:00:00",
        "item_count": 1,
        "file_name": "colA.zip",
        "file_path": os.path.join(os.getcwd(), "colA.zip"),
        "file_size": 1024,
    }
    dlg, service, settings = make_dialog(monkeypatch, qtbot, backups=[sample], settings_initial={})
    # Select the item programmatically
    dlg.backups_list.setCurrentRow(0)
    dlg._on_backup_selected()
    assert dlg.restore_button.isEnabled() is True
    assert dlg.delete_backup_button.isEnabled() is True
