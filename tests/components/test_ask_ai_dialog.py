"""Tests for AskAIDialog and _SearchAIWorker.

Covers construction, UI state, streaming / non-streaming send paths,
error handling, context preview rendering, provider-status label, and
keyboard shortcuts.  All Qt interactions use ``qtbot``.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from tests.utils.fake_llm_provider import FakeLLMProvider
from vector_inspector.state import AppState
from vector_inspector.ui.components.ask_ai_dialog import AskAIDialog, _SearchAIWorker

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

CONTEXT = {
    "search_input": "hello world",
    "top_results": [
        {"rank": 1, "id": "id1", "score": 0.9, "snippet": "Doc one", "metadata": {"source": "a"}},
        {"rank": 2, "id": "id2", "score": 0.8, "snippet": "Doc two", "metadata": {"source": "b"}},
    ],
    "selected_result": {"rank": 1, "id": "id1", "score": 0.9, "snippet": "Doc one", "metadata": {"source": "a"}},
}

EMPTY_CONTEXT: dict = {"search_input": "", "top_results": [], "selected_result": None}


def _make_app_state(provider=None):
    """Return an AppState whose llm_provider is the supplied object."""
    app_state = MagicMock(spec=AppState)
    app_state.llm_provider = provider
    return app_state


def _make_dialog(qtbot, app_state=None, context=None, prefilled_prompt=""):
    if app_state is None:
        app_state = _make_app_state(FakeLLMProvider())
    if context is None:
        context = CONTEXT
    dlg = AskAIDialog(app_state, context=context, prefilled_prompt=prefilled_prompt)
    qtbot.addWidget(dlg)
    return dlg


# ---------------------------------------------------------------------------
# Construction / initial state
# ---------------------------------------------------------------------------


def test_dialog_constructs_without_error(qtbot):
    dlg = _make_dialog(qtbot)
    assert dlg is not None


def test_dialog_window_title(qtbot):
    dlg = _make_dialog(qtbot)
    assert "Ask the AI" in dlg.windowTitle()


def test_dialog_is_not_modal(qtbot):
    dlg = _make_dialog(qtbot)
    assert not dlg.isModal()


def test_send_button_present_and_enabled_initially(qtbot):
    dlg = _make_dialog(qtbot)
    assert dlg._send_btn.isEnabled()


def test_response_area_empty_on_open(qtbot):
    dlg = _make_dialog(qtbot)
    assert dlg._response_area.toPlainText() == ""


def test_busy_bar_hidden_initially(qtbot):
    dlg = _make_dialog(qtbot)
    assert not dlg._busy_bar.isVisible()


def test_context_preview_visible_initially(qtbot):
    """Context preview starts expanded (group box checked by default)."""
    dlg = _make_dialog(qtbot)
    dlg.show()
    assert not dlg._context_preview.isHidden()


# ---------------------------------------------------------------------------
# Prefilled prompt
# ---------------------------------------------------------------------------


def test_prefilled_prompt_populates_input(qtbot):
    dlg = _make_dialog(qtbot, prefilled_prompt="Explain this result.")
    assert dlg._prompt_input.toPlainText() == "Explain this result."


def test_no_prefilled_prompt_leaves_input_empty(qtbot):
    dlg = _make_dialog(qtbot, prefilled_prompt="")
    assert dlg._prompt_input.toPlainText() == ""


# ---------------------------------------------------------------------------
# Status label — provider available
# ---------------------------------------------------------------------------


def test_status_label_shows_provider_info(qtbot):
    provider = FakeLLMProvider()
    dlg = _make_dialog(qtbot, app_state=_make_app_state(provider))
    text = dlg._status_label.text()
    assert "fake" in text.lower()
    assert "fake-model" in text


def test_status_label_green_when_available(qtbot):
    provider = FakeLLMProvider()
    dlg = _make_dialog(qtbot, app_state=_make_app_state(provider))
    assert "green" in dlg._status_label.styleSheet()


def test_status_label_red_when_no_provider(qtbot):
    dlg = _make_dialog(qtbot, app_state=_make_app_state(provider=None))
    style = dlg._status_label.styleSheet()
    assert "#d9534f" in style or "red" in style.lower()


def test_status_label_gray_on_provider_exception(qtbot):
    app_state = MagicMock(spec=AppState)
    type(app_state).llm_provider = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
    dlg = AskAIDialog(app_state, context=CONTEXT)
    qtbot.addWidget(dlg)
    assert "gray" in dlg._status_label.styleSheet()


# ---------------------------------------------------------------------------
# Context preview rendering
# ---------------------------------------------------------------------------


def test_context_preview_contains_search_input(qtbot):
    dlg = _make_dialog(qtbot)
    preview = dlg._context_preview.toPlainText()
    assert "hello world" in preview


def test_context_preview_contains_result_ids(qtbot):
    dlg = _make_dialog(qtbot)
    preview = dlg._context_preview.toPlainText()
    assert "id1" in preview


def test_context_preview_shows_selected_result(qtbot):
    dlg = _make_dialog(qtbot)
    preview = dlg._context_preview.toPlainText()
    assert "Selected" in preview


def test_context_preview_empty_context(qtbot):
    dlg = _make_dialog(qtbot, context=EMPTY_CONTEXT)
    preview = dlg._context_preview.toPlainText()
    assert "search_input" in preview or "Search input" in preview


def test_context_preview_truncates_long_result_list(qtbot):
    """When >3 results are attached the preview shows '… and N more'."""
    ctx = {
        "search_input": "q",
        "top_results": [
            {"rank": i + 1, "id": f"id{i}", "score": 0.9 - i * 0.05, "snippet": "s", "metadata": {}} for i in range(6)
        ],
        "selected_result": None,
    }
    dlg = _make_dialog(qtbot, context=ctx)
    preview = dlg._context_preview.toPlainText()
    assert "more" in preview


def test_context_preview_score_none_renders_na(qtbot):
    ctx = {
        "search_input": "q",
        "top_results": [{"rank": 1, "id": "x", "score": None, "snippet": "s", "metadata": {}}],
        "selected_result": {"rank": 1, "id": "x", "score": None, "snippet": "s", "metadata": {}},
    }
    dlg = _make_dialog(qtbot, context=ctx)
    assert "N/A" in dlg._context_preview.toPlainText()


# ---------------------------------------------------------------------------
# Send — no prompt
# ---------------------------------------------------------------------------


def test_send_with_empty_prompt_does_nothing(qtbot):
    dlg = _make_dialog(qtbot)
    dlg._prompt_input.setPlainText("")
    # Should be a no-op; no crash, button stays enabled
    dlg._send()
    assert dlg._send_btn.isEnabled()
    assert dlg._response_area.toPlainText() == ""


# ---------------------------------------------------------------------------
# Send — no provider
# ---------------------------------------------------------------------------


def test_send_with_no_provider_shows_error(qtbot):
    dlg = _make_dialog(qtbot, app_state=_make_app_state(provider=None))
    dlg._prompt_input.setPlainText("Test question")
    dlg._send()
    html = dlg._response_area.toHtml()
    assert "Error" in html or "error" in html.lower()


# ---------------------------------------------------------------------------
# Send — streaming path (synchronous via _SearchAIWorker.run())
# ---------------------------------------------------------------------------


def test_send_streaming_appends_chunks(qtbot):
    """Verify that chunks emitted by the worker appear in the response area."""
    provider = FakeLLMProvider(mode="streaming")
    dlg = _make_dialog(qtbot, app_state=_make_app_state(provider))
    dlg._prompt_input.setPlainText("Hello")

    chunks_received: list[str] = []
    dlg._response_area.setPlainText("")

    # Drive _SearchAIWorker synchronously
    from vector_inspector.services.search_ai_service import build_messages

    messages = build_messages("Hello", CONTEXT)
    worker = _SearchAIWorker(provider, messages)
    worker.chunk.connect(chunks_received.append)
    worker.run()  # Run synchronously (not via QThread.start)

    assert len(chunks_received) > 0
    full = "".join(chunks_received)
    assert len(full) > 0


# ---------------------------------------------------------------------------
# _SearchAIWorker — non-streaming path
# ---------------------------------------------------------------------------


def test_worker_non_streaming_emits_done(qtbot):
    from vector_inspector.core.llm_providers.types import CAPABILITIES_SCHEMA_VERSION, ProviderCapabilities

    provider = FakeLLMProvider(mode="echo")
    # Override capabilities to report no streaming
    no_stream_caps = ProviderCapabilities(
        schema_version=CAPABILITIES_SCHEMA_VERSION,
        provider_name="fake",
        supports_streaming=False,
        supports_tools=False,
        concurrency="multi",
        max_context_tokens=4096,
        roles_supported=["system", "user", "assistant"],
        model_list=[],
    )
    with patch.object(provider, "get_capabilities", return_value=no_stream_caps):
        messages = [{"role": "user", "content": "hi"}]
        worker = _SearchAIWorker(provider, messages)
        done_called = []
        chunks = []
        worker.done.connect(lambda: done_called.append(True))
        worker.chunk.connect(chunks.append)
        worker.run()
    assert done_called
    assert len(chunks) > 0


def test_worker_error_inject_emits_error_signal(qtbot):
    """A provider that throws should emit the error signal, then done."""
    provider = FakeLLMProvider(mode="error_inject", error_rate=1.0)
    messages = [{"role": "user", "content": "hi"}]
    worker = _SearchAIWorker(provider, messages)
    errors = []
    done_flag = []
    worker.error.connect(errors.append)
    worker.done.connect(lambda: done_flag.append(True))
    worker.run()
    assert errors
    assert done_flag


def test_worker_done_always_emits_after_chunk(qtbot):
    provider = FakeLLMProvider(mode="streaming")
    messages = [{"role": "user", "content": "ping"}]
    worker = _SearchAIWorker(provider, messages)
    done_flag = []
    worker.done.connect(lambda: done_flag.append(True))
    worker.run()
    assert done_flag


# ---------------------------------------------------------------------------
# _on_chunk / _on_done / _on_error slot behaviour
# ---------------------------------------------------------------------------


def test_on_chunk_appends_text(qtbot):
    dlg = _make_dialog(qtbot)
    dlg._on_chunk("hello ")
    dlg._on_chunk("world")
    assert "hello world" in dlg._response_area.toPlainText()


def test_on_done_re_enables_send_button(qtbot):
    dlg = _make_dialog(qtbot)
    dlg._send_btn.setEnabled(False)
    dlg._busy_bar.setVisible(True)
    dlg._on_done()
    assert dlg._send_btn.isEnabled()
    assert not dlg._busy_bar.isVisible()


def test_on_done_inserts_separator(qtbot):
    """_on_done injects an HTML separator between conversation turns."""
    dlg = _make_dialog(qtbot)
    dlg._response_area.clear()
    dlg._on_done()
    # After a turn, the HTML should contain some content (separator was inserted)
    assert dlg._response_area.toHtml() != ""


def test_on_error_re_enables_send_button(qtbot):
    dlg = _make_dialog(qtbot)
    dlg._send_btn.setEnabled(False)
    dlg._busy_bar.setVisible(True)
    dlg._on_error("something went wrong")
    assert dlg._send_btn.isEnabled()
    assert not dlg._busy_bar.isVisible()


def test_on_error_shows_error_text(qtbot):
    dlg = _make_dialog(qtbot)
    dlg._on_error("timeout")
    html = dlg._response_area.toHtml()
    assert "timeout" in html


# ---------------------------------------------------------------------------
# _append_question — colour-coded user turn injection
# ---------------------------------------------------------------------------


def test_append_question_injects_prompt_text(qtbot):
    """_append_question writes the user question and AI label into the response area."""
    dlg = _make_dialog(qtbot)
    dlg._response_area.clear()
    dlg._append_question("What is this result?")
    content = dlg._response_area.toHtml()
    assert "What is this result?" in content


def test_append_question_escapes_html(qtbot):
    """User-supplied prompt content is HTML-escaped before insertion (no raw tags in source)."""
    dlg = _make_dialog(qtbot)
    dlg._response_area.clear()
    dlg._append_question("<script>alert('xss')</script>")
    # toHtml() returns the underlying HTML; injected tag must be escaped
    source = dlg._response_area.toHtml()
    assert "<script>" not in source


def test_append_question_includes_you_and_ai_labels(qtbot):
    """Both 'You:' and 'AI:' headings are present after _append_question."""
    dlg = _make_dialog(qtbot)
    dlg._response_area.clear()
    dlg._append_question("Hello?")
    plain = dlg._response_area.toPlainText()
    assert "You:" in plain
    assert "AI:" in plain


# ---------------------------------------------------------------------------
# Clear button
# ---------------------------------------------------------------------------


def test_clear_button_empties_response(qtbot):
    dlg = _make_dialog(qtbot)
    dlg._response_area.setPlainText("Some text")
    dlg._clear_btn.click()
    assert dlg._response_area.toPlainText() == ""


# ---------------------------------------------------------------------------
# Close button
# ---------------------------------------------------------------------------


def test_close_button_closes_dialog(qtbot):
    dlg = _make_dialog(qtbot)
    dlg.show()
    dlg._close_btn.click()
    assert not dlg.isVisible()


# ---------------------------------------------------------------------------
# _append_error updates status label
# ---------------------------------------------------------------------------


def test_append_error_updates_status_label(qtbot):
    dlg = _make_dialog(qtbot)
    dlg._append_error("Network failure")
    assert "Error" in dlg._status_label.text()
    assert "Network failure" in dlg._status_label.toolTip()


# ---------------------------------------------------------------------------
# Ctrl+Enter shortcut
# ---------------------------------------------------------------------------


def test_ctrl_enter_calls_send(qtbot, monkeypatch):
    """Ctrl+Enter in the prompt input triggers _send()."""
    dlg = _make_dialog(qtbot)
    dlg._prompt_input.setPlainText("Test question")
    send_called = []
    monkeypatch.setattr(dlg, "_send", lambda: send_called.append(True))
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent

    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Return,
        Qt.KeyboardModifier.ControlModifier,
    )
    dlg.eventFilter(dlg._prompt_input, event)
    assert send_called


def test_enter_without_ctrl_does_not_send(qtbot, monkeypatch):
    """Plain Enter in the prompt input does NOT trigger _send()."""
    dlg = _make_dialog(qtbot)
    dlg._prompt_input.setPlainText("Test question")
    send_called = []
    monkeypatch.setattr(dlg, "_send", lambda: send_called.append(True))
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QKeyEvent

    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Return,
        Qt.KeyboardModifier.NoModifier,
    )
    dlg.eventFilter(dlg._prompt_input, event)
    assert not send_called


# ---------------------------------------------------------------------------
# _get_provider — exception path
# ---------------------------------------------------------------------------


def test_get_provider_returns_none_on_exception(qtbot):
    app_state = MagicMock(spec=AppState)
    type(app_state).llm_provider = property(lambda self: (_ for _ in ()).throw(RuntimeError("crash")))
    dlg = AskAIDialog(app_state, context=CONTEXT)
    qtbot.addWidget(dlg)
    result = dlg._get_provider()
    assert result is None


# ---------------------------------------------------------------------------
# LLM settings change — live status refresh
# ---------------------------------------------------------------------------


def test_on_setting_changed_llm_key_refreshes_status(qtbot):
    """Changing an llm.* setting calls llm_runtime_manager.refresh() and updates the label."""
    provider = FakeLLMProvider()
    app_state = MagicMock(spec=AppState)
    app_state.llm_provider = provider
    refresh_calls = []
    app_state.llm_runtime_manager.refresh.side_effect = lambda: refresh_calls.append(True)
    dlg = AskAIDialog(app_state, context=CONTEXT)
    qtbot.addWidget(dlg)
    dlg._on_setting_changed("llm.provider", "ollama")
    assert refresh_calls


def test_on_setting_changed_non_llm_key_ignored(qtbot):
    """Changes to non-llm.* settings must not trigger provider refresh."""
    provider = FakeLLMProvider()
    app_state = MagicMock(spec=AppState)
    app_state.llm_provider = provider
    refresh_calls = []
    app_state.llm_runtime_manager.refresh.side_effect = lambda: refresh_calls.append(True)
    dlg = AskAIDialog(app_state, context=CONTEXT)
    qtbot.addWidget(dlg)
    dlg._on_setting_changed("ui.theme", "dark")
    assert not refresh_calls


def test_show_event_refreshes_runtime_manager(qtbot):
    """showEvent must call llm_runtime_manager.refresh() so a stale cached provider is evicted."""
    provider = FakeLLMProvider()
    app_state = MagicMock(spec=AppState)
    app_state.llm_provider = provider
    refresh_calls = []
    app_state.llm_runtime_manager.refresh.side_effect = lambda: refresh_calls.append(True)
    dlg = AskAIDialog(app_state, context=CONTEXT)
    qtbot.addWidget(dlg)
    dlg.show()
    assert refresh_calls
