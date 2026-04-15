"""Tests for vector_inspector.core.logging helpers."""

import importlib
import logging
from unittest.mock import patch


class TestLogTrackedError:
    def test_emits_error_log(self, caplog):
        """log_tracked_error forwards the message to the error logger."""
        from vector_inspector.core.logging import log_tracked_error

        with caplog.at_level(logging.ERROR, logger="vector_inspector"):
            log_tracked_error("something went wrong: %s", "detail", category="ingestion")

        assert "something went wrong: detail" in caplog.text

    def test_sends_telemetry_event(self):
        """log_tracked_error calls TelemetryService.send_event with the given category."""
        from vector_inspector.core.logging import log_tracked_error

        with patch("vector_inspector.services.telemetry_service.TelemetryService.send_event") as mock_send:
            log_tracked_error("oops", category="connection")

        mock_send.assert_called_once()
        event_name, payload = mock_send.call_args[0]
        assert event_name == "tracked_error"
        assert payload["metadata"]["category"] == "connection"

    def test_telemetry_exception_does_not_propagate(self):
        """A broken TelemetryService must never raise from log_tracked_error."""
        from vector_inspector.core.logging import log_tracked_error

        with patch(
            "vector_inspector.services.telemetry_service.TelemetryService.send_event",
            side_effect=RuntimeError("telemetry down"),
        ):
            log_tracked_error("error")  # must not raise

    def test_category_defaults_to_general(self):
        """Omitting category sends 'general' in the telemetry payload."""
        from vector_inspector.core.logging import log_tracked_error

        with patch("vector_inspector.services.telemetry_service.TelemetryService.send_event") as mock_send:
            log_tracked_error("bare error")

        _, payload = mock_send.call_args[0]
        assert payload["metadata"]["category"] == "general"

    def test_optional_metadata_fields_included_in_telemetry(self):
        """error_type, operation, provider, error_code are forwarded to telemetry."""
        from vector_inspector.core.logging import log_tracked_error

        with patch("vector_inspector.services.telemetry_service.TelemetryService.send_event") as mock_send:
            log_tracked_error(
                "db error",
                category="data",
                error_type="ValueError",
                operation="add_items",
                provider="chromadb",
                error_code="DB_ERR",
            )

        _, payload = mock_send.call_args[0]
        meta = payload["metadata"]
        assert meta["error_type"] == "ValueError"
        assert meta["operation"] == "add_items"
        assert meta["provider"] == "chromadb"
        assert meta["error_code"] == "DB_ERR"

    def test_summary_truncated_to_100_chars(self):
        """Summary longer than 100 characters is truncated before sending to telemetry."""
        from vector_inspector.core.logging import log_tracked_error

        long_summary = "x" * 150

        with patch("vector_inspector.services.telemetry_service.TelemetryService.send_event") as mock_send:
            log_tracked_error("error", category="data", summary=long_summary)

        _, payload = mock_send.call_args[0]
        assert len(payload["metadata"]["summary"]) == 100

    def test_exc_info_forwarded_to_logger(self, caplog):
        """exc_info=True is forwarded to the logger but not included in telemetry metadata."""
        from vector_inspector.core.logging import log_tracked_error

        with patch("vector_inspector.services.telemetry_service.TelemetryService.send_event") as mock_send:
            try:
                raise ValueError("boom")
            except ValueError:
                with caplog.at_level(logging.ERROR, logger="vector_inspector"):
                    log_tracked_error("caught error", exc_info=True, category="test")

        _, payload = mock_send.call_args[0]
        # exc_info must NOT appear in the telemetry metadata
        assert "exc_info" not in payload["metadata"]
        # The traceback should appear in the log record
        assert any(r.exc_info is not None for r in caplog.records)

    def test_telemetry_keys_not_forwarded_to_logger(self, caplog):
        """Telemetry-specific kwargs are stripped before reaching the logger."""
        from vector_inspector.core.logging import log_tracked_error

        # If telemetry keys were passed to the logger it would raise TypeError
        with caplog.at_level(logging.ERROR, logger="vector_inspector"):
            log_tracked_error(
                "test",
                category="connection",
                error_type="IOError",
                operation="connect",
                provider="qdrant",
                error_code="CONN_ERR",
                summary="short",
            )
        assert "test" in caplog.text


class TestLogWarning:
    def test_log_warning_emits_warning(self, caplog):
        """log_warning forwards to the warning level."""
        from vector_inspector.core.logging import log_warning

        with caplog.at_level(logging.WARNING, logger="vector_inspector"):
            log_warning("something is suspicious: %s", "detail")

        assert "something is suspicious: detail" in caplog.text
        assert any(r.levelno == logging.WARNING for r in caplog.records)


class TestLogLevelEnvVar:
    def test_invalid_log_level_falls_back_to_warning(self, monkeypatch):
        """An invalid LOG_LEVEL env var must not raise; the level falls back to WARNING."""
        import vector_inspector.core.logging as logging_module

        monkeypatch.setenv("LOG_LEVEL", "NOTAVALIDLEVEL")
        # Reload to re-execute module-level initialisation with the bad env var.
        # We reload only when no handlers are present to trigger the init block.
        original_handlers = logging_module._logger.handlers[:]
        logging_module._logger.handlers.clear()
        try:
            importlib.reload(logging_module)
            assert logging_module._logger.level == logging.WARNING
        finally:
            # Restore original state so other tests aren't affected.
            logging_module._logger.handlers.clear()
            for h in original_handlers:
                logging_module._logger.addHandler(h)
            monkeypatch.delenv("LOG_LEVEL", raising=False)
            importlib.reload(logging_module)
