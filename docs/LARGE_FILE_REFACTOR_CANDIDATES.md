# Large-file refactor candidates

Summary
-------
Scanned tracked files by line count and collected the largest files that are good candidates for breaking into smaller modules. Below are the top candidates with short rationale and suggested splits.

Top candidates
--------------

- `site/images/demo.gif` — 31841 lines (binary asset)
  - Why: Very large but binary image; not refactorable. Keep as an asset.

- `pdm.lock` — 4478 lines (lockfile)
  - Why: Auto-generated package lock. Not a refactor target; consider keeping in VCS or regenerating when needed.

- `src/vector_inspector/core/connections/pinecone_connection.py` — 1275 lines
  - Why: Large provider connection with client code, helpers, and serialization mixed together.
  - Suggested split: `pinecone_client.py` (HTTP/SDK wrapper), `pinecone_models.py` (schemas/DTOs), `pinecone_utils.py` (helpers/pagination), and keep a slim `pinecone_connection.py` as the public connection class.

- `src/vector_inspector/ui/views/metadata_view.py` — ~~1178 lines~~ **REFACTORED** ✅
  - **Status:** Refactored into modular subpackage `metadata/`
  - **New structure:**
    - `metadata_view.py` (820 lines) — Orchestrator/coordinator
    - `metadata/metadata_threads.py` (38 lines) — Background data loading
    - `metadata/metadata_table.py` (276 lines) — Table population, pagination, context menu
    - `metadata/metadata_filters.py` (28 lines) — Filter field management
    - `metadata/metadata_io.py` (250 lines) — Import/export with Qdrant-specific handling
    - `metadata/__init__.py` (11 lines) — Public API exports
  - **Total:** 1,423 lines across 6 files (30% reduction in main view)
  - **Extension compatibility:** ✅ Preserved `table_context_menu_hook` interface for vector-studio

- `src/vector_inspector/core/connections/pgvector_connection.py` — 980 lines
  - Why: Monolithic SQL provider with query builders and I/O mixed in.
  - Suggested split: `pgvector_client.py`, `pgvector_query_builder.py`, `pgvector_models.py`, helpers for paging/streaming.

- `src/vector_inspector/core/connections/qdrant_connection.py` — 859 lines
  - Why: HTTP client, request/response handling, and utility functions mixed together.
  - Suggested split: `qdrant_client.py`, `qdrant_models.py`, `qdrant_utils.py`.

- `src/vector_inspector/ui/components/profile_manager_panel.py` — 792 lines
  - Why: Large UI component combining multiple widgets and persistence logic.
  - Suggested split: `profile_manager_panel.py` (container), `profile_list_widget.py`, `profile_edit_dialog.py`, move persistence to `profile_service.py` (if not already present).

- `src/vector_inspector/ui/main_window.py` — 708 lines
  - Why: Main window that defines menus, toolbars, actions and layout.
  - Suggested split: `main_window.py` (thin coordinator), `menus.py`, `toolbars.py`, `actions.py`, and `layout_helpers.py`.

- `src/vector_inspector/ui/views/info_panel.py` — 671 lines
  - Why: Large info/help panel mixing static content with runtime widgets.
  - Suggested split: static content file(s), `info_widgets.py`, `about_dialog.py`.

- `src/vector_inspector/core/connections/chroma_connection.py` — 578 lines
  - Why: Provider connection with multiple responsibilities.
  - Suggested split: `chroma_client.py`, `chroma_models.py`, `chroma_utils.py`.

- `src/vector_inspector/ui/views/search_view.py` — 523 lines
  - Why: Search UI mixed with query and result-handling logic.
  - Suggested split: `search_view.py` (UI), `search_service.py` (search execution/logic), `search_result_models.py`.

Notes & next steps
------------------

- All suggested splits aim to: (1) separate UI from business logic, (2) extract provider SDK/HTTP clients from orchestration, and (3) group models/schemas separately.
- If you want, I can: open a specific candidate and produce a concrete extraction plan (new filenames, moved functions/classes), or implement a small refactor extracting helpers into new files and updating imports.

Generated: February 12, 2026
