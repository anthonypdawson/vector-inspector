"""Tests for backup_restore_threads background thread classes.

Calls .run() directly (synchronous) to avoid starting actual QThreads,
and uses signal spies via simple callable captures.
"""

from unittest.mock import MagicMock

from vector_inspector.ui.components.backup_restore_threads import BackupThread, RestoreThread


def _capture_signal(obj, signal_name: str):
    """Connect a signal to a list collector and return the list."""
    captured = []
    getattr(obj, signal_name).connect(lambda *args: captured.append(args))
    return captured


class TestBackupThread:
    def _make_thread(
        self,
        backup_service,
        connection="conn",
        collection="col",
        backup_dir="/tmp",
        include_embeddings=True,
        profile_name="p",
    ):
        return BackupThread(
            backup_service=backup_service,
            connection=connection,
            collection_name=collection,
            backup_dir=backup_dir,
            include_embeddings=include_embeddings,
            profile_name=profile_name,
        )

    def test_run_emits_finished_on_success(self, qapp):
        svc = MagicMock()
        svc.backup_collection.return_value = "/tmp/backup.zip"

        thread = self._make_thread(svc)
        finished = _capture_signal(thread, "finished")
        errors = _capture_signal(thread, "error")

        thread.run()

        assert finished == [("/tmp/backup.zip",)]
        assert errors == []

    def test_run_emits_error_when_backup_returns_none(self, qapp):
        svc = MagicMock()
        svc.backup_collection.return_value = None

        thread = self._make_thread(svc)
        finished = _capture_signal(thread, "finished")
        errors = _capture_signal(thread, "error")

        thread.run()

        assert finished == []
        assert len(errors) == 1
        assert "Failed" in errors[0][0]

    def test_run_emits_error_on_exception(self, qapp):
        svc = MagicMock()
        svc.backup_collection.side_effect = RuntimeError("disk full")

        thread = self._make_thread(svc)
        errors = _capture_signal(thread, "error")

        thread.run()

        assert len(errors) == 1
        assert "disk full" in errors[0][0]


class TestRestoreThread:
    def _make_thread(
        self,
        backup_service,
        backup_file="/tmp/b.zip",
        collection_name=None,
        overwrite=False,
        recompute_embeddings=None,
        profile_name="p",
    ):
        mock_conn = MagicMock()
        return RestoreThread(
            backup_service=backup_service,
            connection=mock_conn,
            backup_file=backup_file,
            collection_name=collection_name,
            overwrite=overwrite,
            recompute_embeddings=recompute_embeddings,
            profile_name=profile_name,
        )

    def test_run_emits_finished_with_provided_collection_name(self, qapp, tmp_path):
        svc = MagicMock()
        svc.restore_collection.return_value = True

        thread = self._make_thread(svc, collection_name="my_col")
        finished = _capture_signal(thread, "finished")
        errors = _capture_signal(thread, "error")

        thread.run()

        assert finished == [("my_col",)]
        assert errors == []

    def test_run_reads_collection_name_from_zip(self, qapp, tmp_path):
        import json
        import zipfile

        # Create a minimal backup zip with metadata
        backup_file = str(tmp_path / "backup.zip")
        with zipfile.ZipFile(backup_file, "w") as zf:
            metadata = {"collection_name": "col_from_zip"}
            zf.writestr("metadata.json", json.dumps(metadata))
            zf.writestr("data.json", json.dumps({"ids": []}))

        svc = MagicMock()
        svc.restore_collection.return_value = True

        thread = self._make_thread(svc, backup_file=backup_file, collection_name=None)
        finished = _capture_signal(thread, "finished")

        thread.run()

        assert finished == [("col_from_zip",)]

    def test_run_emits_error_when_restore_fails(self, qapp):
        svc = MagicMock()
        svc.restore_collection.return_value = False

        thread = self._make_thread(svc)
        errors = _capture_signal(thread, "error")

        thread.run()

        assert len(errors) == 1
        assert "Failed" in errors[0][0]

    def test_run_emits_error_on_exception(self, qapp):
        svc = MagicMock()
        svc.restore_collection.side_effect = OSError("file not found")

        thread = self._make_thread(svc)
        errors = _capture_signal(thread, "error")

        thread.run()

        assert len(errors) == 1
        assert "file not found" in errors[0][0]
