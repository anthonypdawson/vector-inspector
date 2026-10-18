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
