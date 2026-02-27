"""Tests for CacheManager covering uncovered methods: set, clear, enable, disable,
is_enabled, get_cache_info, and invalidate_cache_on_refresh."""

import pytest

from vector_inspector.core.cache_manager import (
    CacheEntry,
    CacheManager,
    invalidate_cache_on_refresh,
)


@pytest.fixture(autouse=True)
def reset_cache_manager():
    """Reset the CacheManager singleton before every test for isolation."""
    CacheManager._instance = None
    yield
    # Tear-down: reset again so state doesn't bleed into subsequent tests
    CacheManager._instance = None


# ---------------------------------------------------------------------------
# set()
# ---------------------------------------------------------------------------


def test_set_stores_entry():
    cm = CacheManager()
    entry = CacheEntry(data=["a", "b"])
    cm.set("db1", "col1", entry)
    result = cm.get("db1", "col1")
    assert result is entry
    assert result.data == ["a", "b"]


def test_set_updates_timestamp():
    """set() should refresh the entry's timestamp."""
    from datetime import datetime

    cm = CacheManager()
    entry = CacheEntry(data=None)
    old_ts = datetime(2000, 1, 1)
    entry.timestamp = old_ts
    cm.set("db1", "col1", entry)
    assert cm.get("db1", "col1").timestamp > old_ts


def test_set_when_disabled_does_not_store():
    cm = CacheManager()
    cm.disable()
    entry = CacheEntry(data="x")
    cm.set("db1", "col1", entry)
    # disable() clears the cache, and set() with disabled cache is a no-op
    assert cm.get("db1", "col1") is None


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------


def test_clear_removes_all_entries():
    cm = CacheManager()
    cm.set("db1", "col1", CacheEntry(data=1))
    cm.set("db2", "col2", CacheEntry(data=2))
    assert cm.get("db1", "col1") is not None

    cm.clear()

    assert cm.get("db1", "col1") is None
    assert cm.get("db2", "col2") is None


def test_clear_on_empty_cache_does_not_raise():
    cm = CacheManager()
    cm.clear()  # Should not raise
    assert cm.get_cache_info()["entry_count"] == 0


# ---------------------------------------------------------------------------
# enable() / disable()
# ---------------------------------------------------------------------------


def test_enable_allows_set_and_get():
    cm = CacheManager()
    cm.disable()
    cm.enable()
    cm.set("db", "col", CacheEntry(data="hello"))
    assert cm.get("db", "col") is not None


def test_disable_clears_existing_entries():
    cm = CacheManager()
    cm.set("db", "col", CacheEntry(data="hi"))
    cm.disable()
    # After disable, cache should be cleared
    cm.enable()  # re-enable so get() doesn't return None from disabled check
    assert cm.get("db", "col") is None


def test_enable_is_idempotent():
    cm = CacheManager()
    cm.enable()
    cm.enable()
    assert cm.is_enabled() is True


def test_disable_is_idempotent():
    cm = CacheManager()
    cm.disable()
    cm.disable()
    assert cm.is_enabled() is False


# ---------------------------------------------------------------------------
# is_enabled()
# ---------------------------------------------------------------------------


def test_is_enabled_default_true():
    cm = CacheManager()
    assert cm.is_enabled() is True


def test_is_enabled_after_disable():
    cm = CacheManager()
    cm.disable()
    assert cm.is_enabled() is False


def test_is_enabled_after_reenable():
    cm = CacheManager()
    cm.disable()
    cm.enable()
    assert cm.is_enabled() is True


# ---------------------------------------------------------------------------
# get_cache_info()
# ---------------------------------------------------------------------------


def test_get_cache_info_empty():
    cm = CacheManager()
    info = cm.get_cache_info()
    assert info["enabled"] is True
    assert info["entry_count"] == 0
    assert info["entries"] == []


def test_get_cache_info_with_entries():
    cm = CacheManager()
    cm.set("dbA", "colA", CacheEntry(data=[1, 2, 3]))
    cm.set("dbA", "colB", CacheEntry(data=None))

    info = cm.get_cache_info()
    assert info["entry_count"] == 2
    assert info["enabled"] is True

    names = {(e["database"], e["collection"]) for e in info["entries"]}
    assert ("dbA", "colA") in names
    assert ("dbA", "colB") in names

    entry_a = next(e for e in info["entries"] if e["collection"] == "colA")
    assert entry_a["has_data"] is True

    entry_b = next(e for e in info["entries"] if e["collection"] == "colB")
    assert entry_b["has_data"] is False


def test_get_cache_info_has_search_results_flag():
    cm = CacheManager()
    e = CacheEntry(data=None, search_results={"ids": [[1]]})
    cm.set("db", "col", e)
    info = cm.get_cache_info()
    assert info["entries"][0]["has_search_results"] is True


def test_get_cache_info_reflects_disabled_state():
    cm = CacheManager()
    cm.disable()
    info = cm.get_cache_info()
    assert info["enabled"] is False


# ---------------------------------------------------------------------------
# invalidate_cache_on_refresh()
# ---------------------------------------------------------------------------


def test_invalidate_cache_on_refresh_clears_all():
    cm = CacheManager()
    cm.set("db1", "col1", CacheEntry(data=1))
    cm.set("db2", "col2", CacheEntry(data=2))

    invalidate_cache_on_refresh()

    assert cm.get("db1", "col1") is None
    assert cm.get("db2", "col2") is None


def test_invalidate_cache_on_refresh_specific_db():
    cm = CacheManager()
    cm.set("db1", "col1", CacheEntry(data=1))
    cm.set("db2", "col2", CacheEntry(data=2))

    invalidate_cache_on_refresh(database="db1")

    assert cm.get("db1", "col1") is None
    assert cm.get("db2", "col2") is not None


def test_invalidate_cache_on_refresh_specific_db_and_col():
    cm = CacheManager()
    cm.set("db1", "col1", CacheEntry(data=1))
    cm.set("db1", "col2", CacheEntry(data=2))

    invalidate_cache_on_refresh(database="db1", collection="col1")

    assert cm.get("db1", "col1") is None
    assert cm.get("db1", "col2") is not None
