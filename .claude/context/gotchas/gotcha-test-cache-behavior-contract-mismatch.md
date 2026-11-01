---
name: test-cache-behavior-contract-mismatch
description: >-
  test_cache_behavior fails standalone because it expects the cache to survive a
  schema change the fingerprint logic explicitly invalidates
metadata:
  type: gotcha
  tags:
    - tests
    - content-column
    - caching
    - contract
---

`tests/test_content_column_detection.py::test_cache_behavior` asserts that a second `_detect_content_column("test_col", <different schema>)` call returns the first call's result (`"content"`). It fails even fully isolated (clean settings file, single test selected): the implementation evicts the cache entry when the schema fingerprint changes (`base_connection.py`, schema-changed branch deletes cache and fingerprint, then re-detects — `"other"` wins on the new schema).

So the test and the code assert opposite contracts and no ordering or settings state is involved. This is a product decision, not test pollution: either the test's expectation is wrong (cache is *meant* to invalidate on schema change — the fingerprint machinery exists precisely for that) or the invalidation logic is wrong (detection should be sticky per collection once cached). Do not lump this failure in with the override-pollution failures when fixing; it needs its contract decided first. Verified 2026-11-01: fails standalone, returns `'other'`, while neighbors like `test_get_content_column` pass standalone.
