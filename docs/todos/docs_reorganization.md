# Docs Directory Reorganization

## Purpose

The `docs/` directory has grown organically and is now hard to navigate.
Files are a mix of architecture references, guides, feature specs, release
docs, and planning notes all at the root level, with some subdirectories
that were added inconsistently.

## Current State

```
docs/
  *.md              ← 27 files, mixed purposes at root
  upcoming/         ← feature specs for unbuilt features
  todos/            ← unscheduled work items (new)
  telemetry/        ← telemetry-specific docs
  llm_providers/    ← LLM provider docs
  models/           ← model support docs
  TODO.md           ← duplicates the intent of todos/
```

## Proposed Structure

```
docs/
  reference/        ← architecture, settings, metadata_mapping,
                       database_provider_abstraction, core_vs_pro_architecture,
                       coding_rules, telemetry.md, known_embedding_models
  guides/           ← getting_started, quick_reference, llm_providers/,
                       bootstrap_installer
  features/         ← upcoming/ + feature specs (rag_builder, artifact_resolution,
                       user_selected_models, two_step_model_selection,
                       vector_inspector_stubbing, performance_optimization,
                       future_optimizations, llm_integration)
  todos/            ← unscheduled work items (keep as-is)
  telemetry/        ← already organized, keep as-is
  models/           ← already organized, keep as-is
  release/          ← release_reason, release_process, roadmap, project_status
  copilot-working-notes.md  ← keep at root (Copilot memory mirror)
```

## Notes

- `docs/TODO.md` should be merged into `docs/todos/` or removed — it duplicates intent
- `docs/upcoming/` maps to `docs/features/` (specs for planned but unbuilt features)
- Any internal links between docs will need updating after the move
- Check if any CI or tooling references specific doc paths before moving
