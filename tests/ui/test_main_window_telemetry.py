from __future__ import annotations

from unittest.mock import MagicMock


def test_close_event_calls_flush_on_shutdown(qtbot, monkeypatch):
    # Patch TelemetryService.get_instance to a dummy object
    fake = MagicMock()
    fake.flush_on_shutdown = MagicMock()
    monkeypatch.setattr("vector_inspector.services.telemetry_service.TelemetryService.get_instance", lambda: fake)

    # Import MainWindow after patch so behavior is stable
    from vector_inspector.ui.main_window import MainWindow

    # Prevent the splash window from blocking in headless test runs
    # (same pattern as tests/views/test_main_window.py and
    # tests/ui/test_main_window_default_left_tab.py)
    monkeypatch.setattr(MainWindow, "_maybe_show_splash", lambda self: None)

    mw = MainWindow()
    qtbot.addWidget(mw)
    # Create a dummy event object with accept method
    ev = MagicMock()
    mw.closeEvent(ev)

    fake.flush_on_shutdown.assert_called_once()
