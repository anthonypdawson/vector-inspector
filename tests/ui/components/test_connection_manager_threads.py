"""Tests for connection_manager_threads background thread classes."""

from unittest.mock import MagicMock

from vector_inspector.ui.components.connection_manager_threads import (
    DeleteCollectionThread,
    RefreshCollectionsThread,
)


def _capture_signal(obj, signal_name: str):
    captured = []
    getattr(obj, signal_name).connect(lambda *args: captured.append(args))
    return captured


class TestRefreshCollectionsThread:
    def test_run_emits_finished_with_collections(self, qapp):
        mock_conn = MagicMock()
        mock_conn.list_collections.return_value = ["col1", "col2"]

        thread = RefreshCollectionsThread(connection_instance=mock_conn)
        finished = _capture_signal(thread, "finished")
        errors = _capture_signal(thread, "error")

        thread.run()

        assert finished == [(["col1", "col2"],)]
        assert errors == []

    def test_run_emits_error_on_exception(self, qapp):
        mock_conn = MagicMock()
        mock_conn.list_collections.side_effect = RuntimeError("timeout")

        thread = RefreshCollectionsThread(connection_instance=mock_conn)
        finished = _capture_signal(thread, "finished")
        errors = _capture_signal(thread, "error")

        thread.run()

        assert finished == []
        assert len(errors) == 1
        assert "timeout" in errors[0][0]


class TestDeleteCollectionThread:
    def _make_thread(self, mock_conn, collection_name="test_col", profile_name="p"):
        return DeleteCollectionThread(
            connection_instance=mock_conn,
            collection_name=collection_name,
            profile_name=profile_name,
        )

    def test_run_emits_finished_with_updated_collections_on_success(self, qapp):
        mock_conn = MagicMock()
        mock_conn.delete_collection.return_value = True
        mock_conn.list_collections.return_value = ["other_col"]

        thread = self._make_thread(mock_conn, collection_name="test_col")
        finished = _capture_signal(thread, "finished")
        errors = _capture_signal(thread, "error")

        thread.run()

        assert finished == [(["other_col"],)]
        assert errors == []

    def test_run_emits_error_when_delete_fails(self, qapp):
        mock_conn = MagicMock()
        mock_conn.delete_collection.return_value = False

        thread = self._make_thread(mock_conn, collection_name="bad_col")
        finished = _capture_signal(thread, "finished")
        errors = _capture_signal(thread, "error")

        thread.run()

        assert finished == []
        assert len(errors) == 1
        assert "bad_col" in errors[0][0]

    def test_run_emits_error_on_exception(self, qapp):
        mock_conn = MagicMock()
        mock_conn.delete_collection.side_effect = ConnectionError("lost connection")

        thread = self._make_thread(mock_conn)
        errors = _capture_signal(thread, "error")

        thread.run()

        assert len(errors) == 1
        assert "lost connection" in errors[0][0]
