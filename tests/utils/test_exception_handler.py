import sys

import pytest


def test_setup_global_exception_handler_calls_original_and_telemetry(monkeypatch):
    import vector_inspector.utils.exception_handler as eh

    called = {}

    def original_hook(exc_type, exc_value, exc_tb):
        called["original"] = True

    # Replace sys.excepthook before setup so it gets captured
    monkeypatch.setattr(sys, "excepthook", original_hook)

    # Provide a fake telemetry service
    class FakeTelemetry:
        def __init__(self, *args, **kwargs):
            self.sent = []

        def send_error_event(self, message, tb, event_name, extra=None, **kwargs):
            self.sent.append((message, event_name, extra))

    monkeypatch.setattr(eh, "_get_telemetry_service", lambda: FakeTelemetry())

    # Install handler
    eh.setup_global_exception_handler("0.0")

    # Trigger the new excepthook (simulate uncaught exception)
    try:
        raise RuntimeError("boom")
    except RuntimeError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        # Call the installed handler (which should call original_hook)
        sys.excepthook(exc_type, exc_value, exc_tb)

    assert called.get("original") is True


def test_exception_decorator_sends_telemetry_and_reraises(monkeypatch):
    import vector_inspector.utils.exception_handler as eh

    recorded = {}

    class FakeTelemetry:
        def __init__(self, *args, **kwargs):
            pass

        def send_error_event(self, message, tb, event_name, extra=None, **kwargs):
            recorded["sent"] = (message, event_name, extra)

    monkeypatch.setattr(eh, "_get_telemetry_service", lambda: FakeTelemetry())

    @eh.exception_telemetry(event_name="TestEvent", feature="unit")
    def will_raise(x):
        raise ValueError("ouch")

    with pytest.raises(ValueError):
        will_raise(1)

    assert "sent" in recorded
    msg, event, extra = recorded["sent"]
    assert event == "TestEvent"
    assert extra.get("function") == "will_raise"
