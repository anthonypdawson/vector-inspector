---
name: test-coverage-requirement
description: >-
  Vector Inspector maintains an 80% test coverage policy, enforced via
  pytest-cov
metadata:
  type: decision
  tags:
    - testing
    - coverage
    - policy
---

**Decision**: maintain 80% minimum test coverage across Vector Inspector.

**Why**: quality standard — changes without tests risk regressions. Confirmed still current: `pytest-cov>=7.0.0` is a dependency (pyproject.toml) and `scripts/test.sh` runs `pdm run pytest --cov=vector_inspector --cov-report=html`.

**How to apply**:
- Run `pdm run pytest --cov=vector_inspector --cov-report=term-missing` (or `scripts/test.sh` for the HTML report) before considering work done.
- Always use `pdm run pytest`, never bare `pytest` — dependencies are pdm-managed.
- Write tests alongside implementation, not after — add coverage proactively per feature, not reactively when asked.
- Mock external dependencies (HTTP calls, DB connections, file I/O). Prefer `with patch(...)` context-manager style over `@patch` decorators when patching things like `urllib.request.urlopen`.
- Tests mirror source structure under `tests/`; shared fixtures live in `tests/conftest.py`.
- If coverage drops below 80%, add tests before merging — do not ship the regression and fix later.
