## Release Notes (0.6.1) — 2026-03-17

- UI: Ask-AI dialog — added a persistent "Configure LLM…" button, refreshed provider status when settings change or after closing Settings, and ensure the runtime manager is refreshed before sending so the dialog uses the currently-selected model.
- Core: LLM runtime manager — prefer provider-specific model settings (`llm.ollama_model` / `llm.openai_model`) when a provider is explicitly selected to avoid cross-provider model leakage.
- Bug Fix: fixed Ask-AI using a stale LLM model when preferences were changed while the dialog was open.
- Tests: added unit tests covering runtime manager model selection and an Ask-AI dialog status-label test validating provider/model text.
- Telemetry: optimized and updated — added UI and session telemetry events, caching for OS/HWID/provider/collection, and documentation consolidation to `docs/telemetry.md`.
- Data view: added total count label

---