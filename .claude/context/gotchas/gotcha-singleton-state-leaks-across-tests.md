---
name: singleton-state-leaks-across-tests
description: >-
  Class-level singletons (TelemetryService, CacheManager, SettingsService) leak
  state across tests unless reset in an autouse fixture, causing tests that pass
  alone to fail in the full suite
metadata:
  type: gotcha
  tags:
    - testing
    - singleton
    - isolation
    - pytest
---

**Symptom**: a test passes when run alone (`pytest tests/test_foo.py::test_bar`) but fails when run as part of the full suite — the classic sign of cross-test state leakage, not a real logic bug.

**Root cause**: several core services are implemented as class-level singletons holding mutable state (`_instance`, in-memory caches, queued events). Pytest runs tests in collection order by default (`pytest-randomly` is NOT installed — see `pytest.ini`), so a singleton mutated by an earlier test silently affects a later one unless something resets it between tests.

**Confirmed instances in this codebase**:
- `TelemetryService` — `tests/conftest.py` autouse `_reset_telemetry_singleton` fixture resets the singleton and purges its queue file *before and after every test*, specifically "regardless of test order" (its own docstring).
- `CacheManager` — `tests/services/test_cache_manager.py` autouse fixture nulls `CacheManager._instance` before/after each test.
- `SettingsService` — `tests/services/test_settings_service.py` monkeypatches `Path.home()` per test so settings reads/writes never touch the real home dir or leak across tests.
- Multiple `metadata/test_*_helpers.py` files each define their own `reset_cache_singleton` fixture for a shared metadata cache.

**How to apply when you hit this**:
1. If a test only fails in the full suite, suspect singleton/shared state before suspecting the test's own logic.
2. Find the singleton (`_instance` class attribute, module-level cache dict, or similar) the code under test touches.
3. Add (or extend) an `autouse=True` pytest fixture that resets it to a clean state both before AND after the test (not just before — a leftover from the current test can poison the NEXT one too).
4. If the singleton persists to disk/settings (not just in-memory), isolate the filesystem path too (e.g. monkeypatch `Path.home()` or point at `tmp_path`), not just the in-memory instance.
5. Prefer a local fixture scoped to the test module touching that singleton over a new global conftest fixture, unless the singleton is touched broadly (telemetry/cache already are global for this reason).
