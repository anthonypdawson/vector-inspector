---
name: test-settings-not-isolated
description: >-
  Test settings are not isolated: SettingsService persists to the real home-dir
  file and conftest only resets telemetry, so settings writes leak across tests
  and runs
metadata:
  type: gotcha
  tags:
    - tests
    - settings
    - isolation
    - pytest
    - conftest
---

## The trap

`SettingsService` (`src/vector_inspector/services/settings_service.py`) is a process-wide singleton with write-through persistence: every `set()` immediately rewrites the JSON settings file. Default location is the real user file `~/.vector-inspector/settings.json`; the only isolation hatch is the `VI_CONFIG_PATH` env var, read once at first init, which redirects to an alternate file for that run.

`tests/conftest.py` isolates telemetry between tests (function-scoped singleton reset plus HTTP blocking) but does NOT touch settings. So any test that writes settings — `set_content_column()`, which persists `content_column_overrides.<provider>`, or any direct `settings.set()` — leaks that state into every later test in the same pytest process AND into future runs via the on-disk file. New connection objects are not clean slates: `VectorDBConnection.__init__` calls `_load_persisted_overrides()` and pre-seeds the instance cache from disk.

## Proven symptom

`test_manual_override` persisted `test_col -> custom_text` under `content_column_overrides.pgvector`; every later `test_col` detection in the process returned `custom_text` regardless of schema (8 failures in `test_content_column_detection.py`, all order-dependent, all passing alone on a clean file).

## How to apply

- When a test fails only in suite order, check `~/.vector-inspector/settings.json` (or the `VI_CONFIG_PATH` target) for keys the test reads — especially `content_column_overrides.*`.
- Reproduce hermetically: `VI_CONFIG_PATH=/tmp/visettings-test.json` with a fresh file per run; never debug against the real home-dir settings.
- Any new test that calls `settings.set()` or `set_content_column()` needs an autouse fixture that redirects `VI_CONFIG_PATH` to `tmp_path` and resets the `SettingsService` singleton before and after — mirroring the existing `_reset_telemetry_singleton` pattern in `conftest.py`.
- CI must start from a clean settings file or set `VI_CONFIG_PATH`, or suite results depend on whatever ran before on that machine.
