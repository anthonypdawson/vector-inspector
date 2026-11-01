# Project Context Index

This directory holds curated patterns, decisions, and gotchas for this project.
claude-contextus embeds these and injects the relevant ones into each prompt
automatically — no searching required.

Add files under category folders (`decisions/`, `gotchas/`, `architecture/`,
`reference/`, …). Each file carries frontmatter:

```markdown
---
name: short-slug
description: one-line summary used for retrieval relevance
metadata:
  type: decision        # decision | gotcha | arch | reference | …
  tags: [optional, topic, tags]
---

The pattern itself.
```

## Decisions

- [Branch Protection Workflow](decisions/decision-branch-protection-workflow.md) — Never push directly to master; all changes via feature branches and PRs

## Implementation

- [LanceDB Flat Schema Support](implementation/implementation-lancedb-flat-schema.md) — Handle both flat schemas (Contextus) and nested metadata with content column detection

## Reference

- [Subtitle Test Data](reference/reference-subtitle-test-data.md) — Subtitle files as ideal test data for semantic search and embedding validation
- [Version Bump Workflow](reference/reference-version-bump-workflow.md) — Files that need updating when bumping release version
- [test-coverage-requirement](decisions/decision-test-coverage-requirement.md) — Vector Inspector maintains an 80% test coverage policy, enforced via pytest-cov
- [python-bytecode-cache-hides-changes](gotchas/gotcha-python-bytecode-cache-hides-changes.md) — Code changes (especially UI) silently fail to appear in the running app due to stale __pycache__ bytecode
- [singleton-state-leaks-across-tests](gotchas/gotcha-singleton-state-leaks-across-tests.md) — Class-level singletons (TelemetryService, CacheManager, SettingsService) leak state across tests unless reset in an autouse fixture, causing tests that pass alone to fail in the full suite
- [test-settings-not-isolated](gotchas/gotcha-test-settings-not-isolated.md) — Test settings are not isolated: SettingsService persists to the real home-dir file and conftest only resets telemetry, so settings writes leak across tests and runs
- [content-column-resolution-layers](reference/reference-content-column-resolution-layers.md) — Content column resolution order: persisted manual override short-circuits detection, then fingerprint-validated cache, then fresh detection
- [test-cache-behavior-contract-mismatch](gotchas/gotcha-test-cache-behavior-contract-mismatch.md) — test_cache_behavior fails standalone because it expects the cache to survive a schema change the fingerprint logic explicitly invalidates
