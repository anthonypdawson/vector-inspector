---
name: version-bump-workflow
description: Version bump checklist - always update pyproject.toml, src/vector_inspector/__init__.py __version__, and docs/RELEASE_REASON.md together when changing release version numbers
metadata:
  type: reference
  tags: [release, versioning, workflow, version-bump, release-prep, changelog, pyproject, __init__, RELEASE_REASON]
  trigger_files: [pyproject.toml, src/vector_inspector/__init__.py, docs/RELEASE_REASON.md]
---

# Version Bump Workflow

When bumping a release version in vector-inspector (changing version numbers, updating pyproject.toml version field, preparing for release), **three files** must be updated to stay in sync:

**Critical**: Never update just pyproject.toml or just __init__.py alone — all three files must change together or the release will be incomplete.

## Files to Update

### 1. `pyproject.toml`
```toml
[project]
version = "X.Y.Z"
```

This is the canonical version source. The release workflow (`release-and-publish.yml`) reads this to trigger releases.

### 2. `src/vector_inspector/__init__.py`
```python
__version__ = "X.Y.Z"  # Keep in sync with pyproject.toml for dev mode fallback
```

This fallback is used when the package isn't installed (dev mode). Must match `pyproject.toml`.

### 3. `docs/RELEASE_REASON.md`
```markdown
# Release Notes (X.Y.Z) — Date

Summary of changes...
```

The release workflow prepends this to the GitHub release body. Update the version number in the heading and document what's new.

## Workflow

```bash
# 1. Update version in pyproject.toml
# 2. Update __version__ in src/vector_inspector/__init__.py
# 3. Update heading and content in docs/RELEASE_REASON.md

git add pyproject.toml src/vector_inspector/__init__.py docs/RELEASE_REASON.md
git commit -m "chore: bump version to X.Y.Z and update release notes"
```

## What Happens on Merge to Master

When a PR with version changes merges to `master`:

1. `release-and-publish.yml` detects version change in `pyproject.toml`
2. Creates GitHub release tag `vX.Y.Z`
3. Builds and publishes to PyPI
4. Attaches wheel and tarball to release
5. Uses `docs/RELEASE_REASON.md` content in release notes
6. `build-installer.yml` triggers and attaches platform installers

## Version Sync Checker

The `get_version()` function in `__init__.py` prefers installed package metadata but falls back to `__version__` for development:

```python
def get_version():
    try:
        from importlib.metadata import version
        return version("vector-inspector")
    except Exception:
        return __version__  # Dev fallback
```

## Common Mistakes

❌ Only updating `pyproject.toml` → `__version__` out of sync for dev mode
❌ Only updating `__init__.py` → Release workflow won't trigger
❌ Forgetting `docs/RELEASE_REASON.md` → Release has no description
❌ Updating pyproject.toml version without checking __init__.py
❌ Changing version in code but not updating release notes
❌ Editing CHANGELOG.md but forgetting to sync __version__

✅ Update all three files together — pyproject.toml, __init__.py, and RELEASE_REASON.md
✅ Always check __init__.py when pyproject.toml version changes
✅ Version numbers must match across all three files

## Related

- [[branch-protection-workflow]] - Use PR workflow for version bumps
- `.github/workflows/release-and-publish.yml` - Automated release process
