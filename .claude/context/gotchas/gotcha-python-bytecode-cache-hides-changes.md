---
name: python-bytecode-cache-hides-changes
description: >-
  Code changes (especially UI) silently fail to appear in the running app due to
  stale __pycache__ bytecode
metadata:
  type: gotcha
  tags:
    - python
    - bytecode
    - dev-workflow
    - debugging
---

**Symptom**: code changes — especially UI changes — don't appear in the running app after editing, even though the edit is correct and saved.

**Root cause**: Python caches compiled bytecode in `__pycache__` directories. After pulling changes, switching branches, or editing a module that's already been imported elsewhere in the session, the stale `.pyc` can shadow the new source.

**Fix**: use the clean-run script instead of the standard one when this happens:
```bash
scripts/run_clean.sh
```
which runs:
```bash
find . -type d -name __pycache__ -exec rm -rf {} +
python -m vector_inspector
```

**When to reach for it**: after pulling changes, after switching branches, or whenever a UI/module update doesn't show up despite a correct edit. `scripts/run.sh` is the normal entrypoint; `scripts/run_clean.sh` is the cache-busting variant — reach for it as a debugging step before assuming the edit itself is wrong.
