**Test Plan — Cover _restore_backup in BackupRestoreDialog**

**Target file**: [backup_restore_dialog.py](src/vector_inspector/ui/components/backup_restore_dialog.py#L1)

**Goal**: Provide a concrete, low-risk testing approach that exercises the `_restore_backup` flow (happy path and error cases) without launching real UI processes or external services. Tests should verify metadata parsing, selection/confirmation logic, overwrite handling, embedding-choice flow, and interaction with `RestoreThread` / `BackupRestoreService`.

**Scope & Strategy**
- Prefer unit tests that mock file-system and UI interactions (QMessageBox, QFileDialog, QDialog) and stub out threads (`RestoreThread`) so logic executes synchronously where necessary.
- Use pytest + pytest-qt (`qtbot`) for minimal Qt integration: create the dialog widget, simulate selection and user choices, and assert calls/signals.
- Keep heavy I/O (real ZIP reading, long-running restore) mocked — validate that the dialog reads metadata correctly and that it starts the restore with the expected arguments.

**Test Matrix**
- Happy path — restore to original collection
  - Backup file selected contains metadata.json with collection_name and include_embeddings=False
  - Confirm dialog accepted → `RestoreThread` created with final_name==original_name, overwrite False
  - Verify loading dialog shown and `_on_restore_finished` path invoked when thread emits finished

- Happy path — restore to new collection name
  - User enters `restore_name_input` → confirm final_name==entered name

- Overwrite flow
  - Backup's original name exists in connection.list_collections()
  - overwrite unchecked → expect `QMessageBox.warning` and return (no restore started)
  - overwrite checked → confirmation message contains WARNING and restore starts

- Metadata read failure
  - `zipfile.ZipFile` raises or metadata missing → expect `QMessageBox.warning` and no restore started

- Embeddings handling options
  - Backup metadata includes include_embeddings True and embedding_model present
  - Simulate user choosing each radio option (Use stored, Recompute, Omit)
  - Ensure `RestoreThread` receives recompute_choice None / True / False accordingly

- Existing restore_thread running
  - Simulate an active `restore_thread.isRunning()` → verify it is quit/waited before starting new one

- Restore error path
  - `RestoreThread.error` emits → `_on_restore_error` hides loading and shows warning

- Permission / deletion flow (delete button)
  - Simulate delete confirmation and `backup_service.delete_backup` returning True/False and observe notifications

**Fixtures & Mocks**
- Shared fixtures (put in tests/core/llm_providers/conftest.py or tests/ui/conftest.py):
  - `tmp_backup_zip` — create a small zipfile with `metadata.json` and sample content under tmp_path; provide path string.
  - `mock_connection` — a lightweight object with `.database` exposing `list_collections()` and/or `.collections` attribute.
  - `mock_backup_service` — patch `BackupRestoreService` instance to control `list_backups`, `delete_backup` behaviors.
  - `patch_restore_thread_factory` — monkeypatch `RestoreThread` class in the dialog module to a test-double where `.start()` triggers immediate `finished` or `error` signals.

- Qt helpers: use `qtbot` to create widgets and to wait for signals.

**Key Implementation Notes**
- Avoid running real `RestoreThread`/`BackupThread`. Replace them with a fake class:

```python
class FakeThread(QObject):
    finished = Signal(str)
    error = Signal(str)
    def __init__(self, *args, **kwargs):
        super().__init__()
        self._running = False
    def isRunning(self):
        return self._running
    def start(self):
        self._running = True
        # call finished synchronously in tests when desired:
        self.finished.emit('restored-collection')
```

Monkeypatch `vector_inspector.ui.components.backup_restore_dialog.RestoreThread` to `FakeThread` before instantiating the dialog.

- To simulate `QMessageBox` actions (Yes/No or warnings), monkeypatch QMessageBox.question/warning/information to return the desired button or record calls. Example:

```python
from PySide6.QtWidgets import QMessageBox
monkeypatch.setattr(QMessageBox, 'question', lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
``` 

- For ZIP metadata read, either generate a real zip in `tmp_path` containing `metadata.json` (recommended for realism) or monkeypatch `zipfile.ZipFile` to a fake context manager that returns expected metadata bytes.

**Suggested Test Examples (concise)**
- Happy path (restore original name):

```python
def test_restore_happy_path(qtbot, tmp_path, monkeypatch, mock_connection):
    # create a zip with metadata.json
    zip_path = tmp_path / 'backup.zip'
    metadata = {'collection_name': 'orig', 'include_embeddings': False}
    import zipfile, json
    with zipfile.ZipFile(zip_path, 'w') as z:
        z.writestr('metadata.json', json.dumps(metadata))

    # Mock BackupRestoreService.list_backups to return an entry with file_path
    monkeypatch.setattr(BackupRestoreService, 'list_backups', lambda self, d: [{'file_path': str(zip_path), 'collection_name':'orig', 'file_name': 'backup.zip', 'file_size': 10, 'timestamp':'t','item_count':1}])

    # Fake RestoreThread and make start() emit finished synchronously
    class FakeRestore(FakeThread):
        def start(self):
            self.finished.emit('orig')

    monkeypatch.setattr('vector_inspector.ui.components.backup_restore_dialog.RestoreThread', FakeRestore)
    monkeypatch.setattr('PySide6.QtWidgets.QMessageBox.question', lambda *a, **k: QMessageBox.StandardButton.Yes)

    dialog = BackupRestoreDialog(mock_connection)
    qtbot.addWidget(dialog)

    # select the backup
    dialog._refresh_backups_list()
    dialog.backups_list.setCurrentRow(0)

    # click restore
    dialog.restore_button.click()

    # assert loading dialog hidden after finished and information called
    # (monkeypatch QMessageBox.information to record call)
```

**Edge Cases and Robustness Tests**
- Corrupted zip: create a non-zip file or have `zipfile.ZipFile` raise; ensure `QMessageBox.warning` is shown and no thread created.
- Missing metadata.json: zip exists but metadata missing — same expectation.
- Connection API variations: `connection` may be a wrapper with `.database` or may expose `.collections` directly — tests should cover both branches by providing mock_connection variations.

**Where to add tests**
- Test file: `tests/ui/test_backup_restore_dialog.py`
- Use `pytest-qt` for `qtbot` fixture
- Keep helper fixtures in `tests/ui/conftest.py` or reuse `tests/core/llm_providers/conftest.py` where appropriate

**Run/Debug commands**

```bash
# Run only backup/restore tests
pdm run pytest tests/ui/test_backup_restore_dialog.py -q

# Run a single test
pdm run pytest tests/ui/test_backup_restore_dialog.py::test_restore_happy_path -q
```

**Acceptance Criteria**
- Unit tests exercise metadata parsing, overwrite/confirmation logic, embedding-option flow, and correct construction of `RestoreThread` arguments.
- Tests avoid long-running operations and do not require network or real DB connections.
- Tests are deterministic and run under `pytest-qt`.

**Next actions I can take**
- Implement the `tests/ui/test_backup_restore_dialog.py` scaffold with the most important 4–6 tests (happy path, overwrite block, metadata failure, embeddings choice) and the `FakeThread` helper.
- Run the new tests and iterate on failures.

If you want, I can implement the test file now and run it. Which next action do you prefer?