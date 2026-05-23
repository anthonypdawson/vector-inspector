# Ask the AI — Search Results (Upcoming)

Status: Draft

## Overview

Add an "Ask the AI" action to the Search Results panel that opens a lightweight AI assistant bound to the current search context. Prompts issued from the panel will automatically attach:
- the current search input
- the top-N search results (summary for each)
- the selected result (if any)

This enables queries like "Why is this result ranked 5?" and "What caused this item to match my query?" with context-aware, explainable responses.

## Goals

- Surface an inline, discoverable AI assistant in the Search Results view.
- Reuse existing LLM console logic where possible (console currently launched via CLI arg).
- Keep payloads minimal and privacy-aware (no raw embeddings unless consented).
- Provide clear UI affordances: preview of attached context, configurable top-N, and an explainability-first response layout.

## UX / Interaction

- Add an `Ask the AI` button to the Search Results toolbar and right-click context menu.
- Clicking opens a modal or docked pane containing:
  - Prompt input box (editable)
  - Toggle/summary showing attached context (search input, N results, selected item)
  - Send button and streaming response area
- Default attached context: search input + top-5 results + selected item (if present).
- Allow users to inspect / redact attached fields before sending.

## Data Payload (proposal)

- `query`: user's free-text prompt
- `search_input`: the raw search string
- `top_results`: list of up to N items, each with:
  - `id`, `title`, `snippet` (textual preview), `score` (ranking/score), `metadata` (selected keys)
- `selected_result`: same shape as an item above (nullable)
- `config`: { `top_n`: int, `include_snippets`: bool }

Notes:
- Do not include raw vector embeddings by default. If advanced features require them, gate behind explicit opt-in and a privacy warning.
- Strip any PII from attached snippets where possible (configurable).

## Reuse Plan — LLM Console Code

Inventory complete. Key reusable pieces identified:

| Component | Location | What to reuse |
|---|---|---|
| `_GenerateWorker` | `tools/llm_console.py` | QThread pattern for streaming; extract to shared module |
| `app_state.llm_provider` | `state/app_state.py` | Already wired — returns `LLMProvider` via `LLMRuntimeManager` |
| `StreamEvent` | `core/llm_providers/types.py` | `"delta"` / `"done"` events for streaming |
| `LLMProviderFactory` | `core/llm_providers/provider_factory.py` | Provider construction from settings |
| `FakeLLMProvider` | `tests/utils/fake_llm_provider.py` | Use in tests for deterministic responses |

Plan:
- Create `services/search_ai_service.py` — builds the LLM search context payload and manages the prompt.
- Create `ui/components/ask_ai_dialog.py` — modal with streaming response area; uses a `SearchAIWorker` (same pattern as `_GenerateWorker`).
- No new `llm_client` abstraction needed — `app_state.llm_provider` already serves this role.

## Backend & Providers

- Implement a service in `services/` (e.g., `search_ai_service.py`) that:
  - Builds the payload from current UI state
  - Calls the shared `llm_client` and returns streamed responses
  - Logs requests locally (opt-in) and enforces rate-limits
- Keep provider-agnostic: `llm_client` should support multiple adapters (OpenAI, local LLMs) via config.

## Privacy & Security

- Show a clear consent/preview dialog before sending context to an external API.
- Default to minimal context; provide user controls to expand.
- Respect application-level settings for telemetry and external API usage.

## Tests & Acceptance Criteria

- Unit: payload builder — ensure correct fields attached for combinations (no selection, selection present, N results)
- Integration: mock `llm_client` to verify UI sends expected payload and displays streaming text
- UX: user can redact fields and set top-N before sending
- AI response presentation: verify that explanations highlight relevant fields and ranking logic when possible
- Accessibility: keyboard navigation and screen reader support tested
- Localization: UI strings and privacy warnings are translatable
- Error handling: simulate LLM failures and verify fallback behavior
- Manual QA: collect user feedback on explainability and usability

Acceptance:
- Feature visible in Search Results panel
- Prompts include correct context by default
- Responses stream and render reliably, with highlighted explanations
- Privacy preview shown before first external call
- Accessibility and localization criteria met
- Error handling and fallback tested
- 80%+ test coverage on new service and UI components

## Risks & Mitigations

- Over-sharing sensitive data: mitigate via preview, opt-in, and defaults that exclude embeddings.
- Long payloads from large results: limit to snippets, top-N default 5, and allow user adjustment.
- Reuse complexity: if console code is tightly coupled to CLI, build a small shared adapter rather than large refactor.

## Implementation Milestones (rough)

1. Inventory console code & extract `llm_client` (1–2 days)
2. Draft payload schema and small service (1 day)
3. UI: Add button + modal + context preview (2–3 days)
4. Wire UI -> service -> `llm_client` with streaming (1–2 days)
5. Tests, privacy wording, polish (1–2 days)

## Next Steps (immediate)

- Locate the LLM console entry and helpers to determine extraction scope.
- Produce a technical task list for the first implementation PR.

## AI Response Presentation

- Responses will be rendered as streaming text, with optional highlighting of relevant fields (e.g., ranking explanations, matched terms).
- Consider adding expandable sections for detailed explanations or references to specific result metadata.
- Support both free-text and structured output (e.g., bullet points, score breakdowns) as returned by the LLM.

## Accessibility & Localization

- Ensure keyboard navigation for all modal/pane controls.
- Support screen reader labels for prompt input, context preview, and response area.
- Plan for localization of UI strings and privacy warnings.

## Error Handling & Fallback

- If the LLM is unavailable or returns an error, show a clear error message and offer retry or fallback suggestions.
- Provide a local-only fallback (e.g., basic keyword explanation) if external LLM is disabled.
- Log errors for diagnostics and user feedback.

## LLM Search Context Shortcut

- Add a right-click shortcut in the Search Results panel for each result, labeled as "Explain result".
- The shortcut launches the "Ask the AI" modal with a prefilled query such as:
  - "Explain this result"
  - "Why did this match my search?"
- Prefilled query can be edited before sending.
- The shortcut attaches the selected result and search input automatically, leveraging the LLM search context for explainability and relevance analysis.

Note: "LLM search context" can be used as an internal technical term for the attached data and logic, but the user-facing label should be "Explain result".
