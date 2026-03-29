"""Tests for status reporter integration in MetadataView handlers.

Covers the status-bar reporting added to _on_item_add_finished,
_on_item_add_error, _on_data_loaded, _on_load_error, and the delete
callbacks inside _delete_selected.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QTableWidgetItem

from vector_inspector.state import AppState
from vector_inspector.ui.views.metadata_view import MetadataView

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mv(qtbot, fake_provider, task_runner):
    """MetadataView backed by a fake provider, with a suppressed loading dialog."""
    fake_provider.create_collection(
        "col1",
        ["doc1", "doc2"],
        [{"k": "v1"}, {"k": "v2"}],
        [[0.1, 0.2], [0.3, 0.4]],
        ids=["id1", "id2"],
    )
    app_state = AppState()
    app_state.provider = fake_provider
    view = MetadataView(app_state, task_runner)
    qtbot.addWidget(view)
    view.ctx.current_collection = "col1"
    view.ctx.current_database = "test_db"
    # Suppress loading dialog so tests don't block
    view.loading_dialog = MagicMock()
    return view


# ---------------------------------------------------------------------------
# _on_item_add_finished
# ---------------------------------------------------------------------------


class TestOnItemAddFinished:
    def test_success_calls_report_action(self, mv, monkeypatch):
        """Success path calls status_reporter.report_action('Item added', ...)."""
        mock_reporter = MagicMock()
        mv.app_state.status_reporter = mock_reporter
        mv._add_start_time = time.time() - 0.1
        monkeypatch.setattr(mv, "_load_data", lambda: None)

        mv._on_item_add_finished(True)

        mock_reporter.report_action.assert_called_once()
        call_args = mock_reporter.report_action.call_args
        assert call_args[0][0] == "Item added"
        assert call_args[1]["result_count"] == 1
        assert call_args[1]["result_label"] == "item"
        assert call_args[1]["elapsed_seconds"] >= 0.0

    def test_success_reloads_data(self, mv, monkeypatch):
        """Success path calls _load_data after reporting status."""
        mv.app_state.status_reporter = MagicMock()
        mv._add_start_time = time.time()
        loaded = []
        monkeypatch.setattr(mv, "_load_data", lambda: loaded.append(True))

        mv._on_item_add_finished(True)

        assert loaded, "_load_data should be called on success"

    def test_success_invalidates_cache(self, mv, monkeypatch):
        """Success path invalidates the cache entry for the current collection."""
        mock_reporter = MagicMock()
        mv.app_state.status_reporter = mock_reporter
        mv._add_start_time = time.time()
        monkeypatch.setattr(mv, "_load_data", lambda: None)

        mock_invalidate = MagicMock()
        monkeypatch.setattr(mv.ctx.cache_manager, "invalidate", mock_invalidate)

        mv._on_item_add_finished(True)

        mock_invalidate.assert_called_once_with("test_db", "col1")

    def test_failure_shows_warning(self, mv, monkeypatch):
        """Failure path shows a QMessageBox warning instead of reporting."""
        warned = []
        monkeypatch.setattr(
            "vector_inspector.ui.views.metadata_view.QMessageBox.warning",
            lambda *a, **k: warned.append(True),
        )

        mv._on_item_add_finished(False)

        assert warned, "Expected QMessageBox.warning on add failure"

    def test_failure_does_not_call_report_action(self, mv, monkeypatch):
        """Failure path does NOT call status_reporter.report_action."""
        mock_reporter = MagicMock()
        mv.app_state.status_reporter = mock_reporter
        monkeypatch.setattr(
            "vector_inspector.ui.views.metadata_view.QMessageBox.warning",
            lambda *a, **k: None,
        )

        mv._on_item_add_finished(False)

        mock_reporter.report_action.assert_not_called()


# ---------------------------------------------------------------------------
# _on_item_add_error
# ---------------------------------------------------------------------------


class TestOnItemAddError:
    def test_reports_error_to_status_bar(self, mv, monkeypatch):
        """_on_item_add_error calls status_reporter.report with level='error'."""
        mock_reporter = MagicMock()
        mv.app_state.status_reporter = mock_reporter
        monkeypatch.setattr(
            "vector_inspector.ui.views.metadata_view.QMessageBox.warning",
            lambda *a, **k: None,
        )

        mv._on_item_add_error("disk full")

        mock_reporter.report.assert_called_once()
        call_args = mock_reporter.report.call_args
        assert "disk full" in call_args[0][0]
        assert call_args[1].get("level") == "error"

    def test_shows_warning_dialog(self, mv, monkeypatch):
        """_on_item_add_error also shows a QMessageBox warning to the user."""
        mv.app_state.status_reporter = MagicMock()
        warned = []
        monkeypatch.setattr(
            "vector_inspector.ui.views.metadata_view.QMessageBox.warning",
            lambda *a, **k: warned.append(True),
        )

        mv._on_item_add_error("network timeout")

        assert warned

    def test_hides_loading_dialog(self, mv, monkeypatch):
        """_on_item_add_error hides the loading dialog."""
        mv.app_state.status_reporter = MagicMock()
        monkeypatch.setattr(
            "vector_inspector.ui.views.metadata_view.QMessageBox.warning",
            lambda *a, **k: None,
        )

        mv._on_item_add_error("some error")

        mv.loading_dialog.hide_loading.assert_called()


# ---------------------------------------------------------------------------
# _on_data_loaded — status reporter call
# ---------------------------------------------------------------------------


class TestOnDataLoadedStatusReporting:
    def test_reports_data_loaded_on_success(self, mv, monkeypatch):
        """_on_data_loaded calls status_reporter.report_action('Data loaded', ...) on success."""
        mock_reporter = MagicMock()
        mv.app_state.status_reporter = mock_reporter
        mv._load_start_time = time.time() - 0.3

        # Build minimal payload that process_loaded_data understands
        data = {
            "ids": ["id1", "id2"],
            "documents": ["doc1", "doc2"],
            "metadatas": [{"k": "v1"}, {"k": "v2"}],
            "embeddings": [[0.1, 0.2], [0.3, 0.4]],
            "has_more": False,
            "total_count": 2,
            "applied_filters": [],
            "server_filter": None,
            "client_filters": [],
        }

        # Monkeypatch process_loaded_data so we skip table rendering complexity
        monkeypatch.setattr(
            "vector_inspector.ui.views.metadata_view.process_loaded_data",
            lambda *a, **k: None,
        )

        mv._on_data_loaded(data)

        mock_reporter.report_action.assert_called_once()
        call_args = mock_reporter.report_action.call_args
        assert call_args[0][0] == "Data loaded"
        assert call_args[1]["result_label"] == "item"
        assert call_args[1]["elapsed_seconds"] >= 0.0

    def test_reports_error_on_load_failure(self, mv):
        """_on_load_error calls status_reporter.report with level='error'."""
        mock_reporter = MagicMock()
        mv.app_state.status_reporter = mock_reporter

        mv._on_load_error("connection refused")

        mock_reporter.report.assert_called_once()
        call_args = mock_reporter.report.call_args
        assert "connection refused" in call_args[0][0]
        assert call_args[1].get("level") == "error"


# ---------------------------------------------------------------------------
# _delete_selected — delete callbacks via synchronous task_runner=None path
# ---------------------------------------------------------------------------


class TestDeleteSelectedStatusReporting:
    def _setup_table_row(self, mv, row_id: str = "id1") -> None:
        """Populate the table with one row and select it."""
        mv.table.setColumnCount(3)
        mv.table.setRowCount(1)
        mv.table.setItem(0, 0, QTableWidgetItem(row_id))
        mv.table.selectRow(0)

    def test_delete_success_reports_to_status_bar(self, mv, monkeypatch):
        """Successful delete calls status_reporter.report_action with elapsed time."""
        self._setup_table_row(mv)

        mock_reporter = MagicMock()
        mv.app_state.status_reporter = mock_reporter

        # Use the synchronous (task_runner=None) code path
        mv.task_runner = None

        monkeypatch.setattr(
            "vector_inspector.ui.views.metadata_view.QMessageBox.question",
            lambda *a, **k: __import__("PySide6.QtWidgets", fromlist=["QMessageBox"]).QMessageBox.StandardButton.Yes,
        )
        monkeypatch.setattr(mv, "_load_data", lambda: None)

        mv._delete_start_time = time.time() - 0.1
        mv._delete_selected()

        mock_reporter.report_action.assert_called_once()
        call_args = mock_reporter.report_action.call_args
        assert "Deleted" in call_args[0][0]
        assert call_args[1]["elapsed_seconds"] >= 0.0

    def test_delete_error_reports_to_status_bar(self, mv, monkeypatch):
        """When delete_items raises, _on_delete_error reports with level='error'."""
        self._setup_table_row(mv)

        mock_reporter = MagicMock()
        mv.app_state.status_reporter = mock_reporter

        # Force delete_items to raise so the error path is exercised
        mv.ctx.connection.delete_items = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("DB error"))
        mv.task_runner = None

        monkeypatch.setattr(
            "vector_inspector.ui.views.metadata_view.QMessageBox.question",
            lambda *a, **k: __import__("PySide6.QtWidgets", fromlist=["QMessageBox"]).QMessageBox.StandardButton.Yes,
        )
        monkeypatch.setattr(
            "vector_inspector.ui.views.metadata_view.QMessageBox.warning",
            lambda *a, **k: None,
        )

        mv._delete_selected()

        mock_reporter.report.assert_called_once()
        call_args = mock_reporter.report.call_args
        assert call_args[1].get("level") == "error"
