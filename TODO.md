# TODO

This file tracks follow-ups and implementation tasks related to provider tests and LanceDB robustness.

- [x] Add pgvector connection unit tests
- [x] Run tests for new file
- [x] Iterate if failures found
- [x] Fix LanceDB `add_items` / `delete_items` issues
- [x] Add mocked LanceDB unit tests
- [x] Run LanceDB tests
- [x] Feature-detect native LanceDB delete API (`tbl.delete(predicate)`) and use when available
- [x] Implement atomic rewrite fallback (drop → create with data, no double-insertion bug)
- [x] Add unit tests: native delete path, fallback-on-error path, no-double-add assertion
- [x] Document supported `lancedb`/`pyarrow` versions in README and CI workflow

Planned (next tasks):

- Add `where`-clause support to `delete_items` (currently ignored)
- Explore LanceDB versioned snapshots / time-travel for safer rewrites
