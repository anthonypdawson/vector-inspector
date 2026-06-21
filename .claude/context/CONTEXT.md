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

## Reference

- [Version Bump Workflow](reference/reference-version-bump-workflow.md) — Files that need updating when bumping release version
