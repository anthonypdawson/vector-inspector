## Release Notes (0.6.0) — 2026-03-10

### Ask the AI — Search Results
- Add **Ask the AI** button to the Search Results toolbar and **Explain result** right-click context menu entry in the Search view.
- Clicking "Ask the AI" or "Explain result" opens a non-modal streaming dialog (`ui/components/ask_ai_dialog.py`) pre-filled with the current search context: search query, top-N results (id, snippet, score, metadata), and the selected result.
- "Explain result" pre-populates the prompt with a ranked-result explanation question; the user can edit the prompt before sending.
- Responses stream in real time from the configured LLM provider (Ollama, llama-cpp, or OpenAI-compatible) via the existing `app_state.llm_provider` — no new provider config required.
- Attached context preview is shown in a collapsible group so users can inspect what is sent before submission.
- Add `services/search_ai_service.py` — pure-Python payload builder and prompt formatter; no Qt dependencies, fully unit-tested.
- Add 22 unit tests in `tests/services/test_search_ai_service.py` covering payload building, nested result unwrapping, snippet truncation, prompt generation, and context formatting.



---