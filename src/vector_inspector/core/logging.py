"""Tiny logging wrapper for consistent logs across the project.

Provides `log_info`, `log_error`, and `log_debug` helpers that delegate
to the standard `logging` module but keep call sites concise.
"""

import logging
import os
from typing import Any

_logger = logging.getLogger("vector_inspector")
if not _logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    # Set log level from LOG_LEVEL env var if present, else default to WARNING
    log_level_str = os.environ.get("LOG_LEVEL", "WARNING").upper()
    try:
        _logger.setLevel(getattr(logging, log_level_str))
    except Exception:
        _logger.setLevel(logging.WARNING)

    # Silence verbose third-party libraries so their output doesn't bury our errors.
    for _noisy in ("chromadb", "sentence_transformers", "transformers", "httpx", "httpcore"):
        logging.getLogger(_noisy).setLevel(logging.WARNING)


def log_info(msg: str, *args: Any, **kwargs: Any) -> None:
    _logger.info(msg, *args, **kwargs)


def log_error(msg: str, *args: Any, **kwargs: Any) -> None:
    _logger.error(msg, *args, **kwargs)


def log_warning(msg: str, *args: Any, **kwargs: Any) -> None:
    _logger.warning(msg, *args, **kwargs)


def log_debug(msg: str, *args: Any, **kwargs: Any) -> None:
    _logger.debug(msg, *args, **kwargs)


def log_tracked_error(msg: str, *args: Any, category: str = "general", **kwargs: Any) -> None:
    """
    Log an error and emit an opt-in telemetry event for important failures.

    Use this instead of ``log_error`` for caught exceptions worth tracking in
    telemetry (e.g. ingestion failures, connection errors). For routine
    expected errors (e.g. "no collection selected") use ``log_error`` only.

    Telemetry payload includes:
      - category: High-level error category (required)
      - error_type: Exception class name (optional, e.g. "ValueError")
      - operation: Operation or function name (optional, e.g. "add_items")
      - provider: Provider/connection type (optional, e.g. "weaviate")
      - error_code: Error code or enum (optional)
      - summary: Short sanitized error summary (optional, truncated to 100 chars)

    Do NOT include raw exception messages, file paths, or user data in telemetry fields.
    Pass extra fields as keyword arguments, e.g.:

        log_tracked_error(
            "Failed to add items: %s", err,
            category="provider",
            error_type=type(err).__name__,
            operation="add_items",
            provider="weaviate",
            summary=str(err),
        )
    """
    _logger.error(msg, *args)
    try:
        # Lazy import avoids a circular dependency (telemetry_service imports logging).
        from vector_inspector.services.telemetry_service import TelemetryService

        # Build safe metadata for telemetry
        metadata = {"category": category}
        # Allowlist of extra fields to include if present in kwargs
        for key in ("error_type", "operation", "provider", "error_code", "summary"):
            value = kwargs.get(key)
            if value is not None:
                # Optionally truncate summary to 100 chars to avoid accidental PII
                if key == "summary" and isinstance(value, str):
                    value = value[:100]
                metadata[key] = value

        TelemetryService.send_event(
            "tracked_error",
            {"metadata": metadata},
        )
    except Exception:
        pass
