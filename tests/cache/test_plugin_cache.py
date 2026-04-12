"""
tests/cache/test_plugin_cache.py

Story 9.5 — Unit tests for PluginCache and PluginManager cache integration.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from Core.cache.plugin_cache import PluginCache
from Core.plugins.base import PluginResult
from Core.plugins.manager import PluginManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_cache(tmp_path, ttl: int = 3600) -> PluginCache:
    db = str(tmp_path / "test_cache.db")
    return PluginCache(db_path=db, ttl=ttl)


# ---------------------------------------------------------------------------
# AC1: PluginCache initialization
# ---------------------------------------------------------------------------

def test_plugin_cache_creates_db_file(tmp_path):
    """PluginCache creates the SQLite file on init."""
    db = str(tmp_path / "sub" / "cache.db")
    cache = PluginCache(db_path=db, ttl=3600)
    assert Path(db).exists()


def test_plugin_cache_default_ttl_from_env(tmp_path, monkeypatch):
    """Default TTL comes from MH_CACHE_TTL env var."""
    monkeypatch.setenv("MH_CACHE_TTL", "7200")
    db = str(tmp_path / "cache.db")
    cache = PluginCache(db_path=db)
    assert cache._ttl == 7200


def test_plugin_cache_default_ttl_fallback(tmp_path, monkeypatch):
    """Default TTL falls back to 86400 when MH_CACHE_TTL not set."""
    monkeypatch.delenv("MH_CACHE_TTL", raising=False)
    db = str(tmp_path / "cache.db")
    cache = PluginCache(db_path=db)
    assert cache._ttl == 86400


# ---------------------------------------------------------------------------
# AC2: get() — cache hit and miss
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_returns_none_on_miss(tmp_path):
    """get() returns None when key not in cache."""
    cache = make_cache(tmp_path)
    result = cache.get("HolehPlugin:EMAIL:test@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_get_returns_data_on_hit(tmp_path):
    """get() returns stored dict after set()."""
    cache = make_cache(tmp_path)
    data = {"registered": ["instagram"], "total_checked": 50}
    await cache.set("holehe:EMAIL:test@example.com", data)
    result = cache.get("holehe:EMAIL:test@example.com")
    assert result == data


@pytest.mark.asyncio
async def test_get_returns_none_for_expired_entry(tmp_path):
    """get() returns None for an expired entry (TTL=0 = immediate expiry)."""
    cache = make_cache(tmp_path, ttl=0)
    data = {"registered": ["discord"]}
    await cache.set("holehe:EMAIL:expired@example.com", data, ttl=0)
    # Advance time to ensure expiry instead of flaky sleep
    with patch("Core.cache.plugin_cache.time") as mock_time:
        mock_time.time.return_value = time.time() + 1
        result = cache.get("holehe:EMAIL:expired@example.com")
    assert result is None


@pytest.mark.asyncio
async def test_get_does_not_delete_expired_entry(tmp_path):
    """get() returns None for expired but does NOT delete the entry (lazy cleanup)."""
    import sqlite3
    cache = make_cache(tmp_path, ttl=0)
    data = {"test": "data"}
    await cache.set("plugin:EMAIL:lazy@test.com", data, ttl=0)
    # Mock time to ensure expiry
    with patch("Core.cache.plugin_cache.time") as mock_time:
        mock_time.time.return_value = time.time() + 1
        cache.get("plugin:EMAIL:lazy@test.com")  # should return None, not delete
    # Verify the row still exists in DB
    with sqlite3.connect(cache._db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM cache WHERE key = ?", ("plugin:EMAIL:lazy@test.com",)).fetchone()[0]
    assert count == 1, "Lazy cleanup: expired entry should remain in DB after get()"


# ---------------------------------------------------------------------------
# AC3: set() — upsert and custom TTL
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_upserts_existing_key(tmp_path):
    """set() updates existing entry (INSERT OR REPLACE)."""
    cache = make_cache(tmp_path)
    await cache.set("plugin:EMAIL:user@test.com", {"v": 1})
    await cache.set("plugin:EMAIL:user@test.com", {"v": 2})
    result = cache.get("plugin:EMAIL:user@test.com")
    assert result == {"v": 2}


@pytest.mark.asyncio
async def test_set_with_custom_ttl(tmp_path):
    """set() with custom TTL overrides default."""
    cache = make_cache(tmp_path, ttl=3600)
    data = {"key": "value"}
    await cache.set("plugin:EMAIL:custom@test.com", data, ttl=7200)
    # Should still be readable
    result = cache.get("plugin:EMAIL:custom@test.com")
    assert result == data


@pytest.mark.asyncio
async def test_set_with_none_ttl_uses_default(tmp_path):
    """set(ttl=None) uses the instance default TTL."""
    cache = make_cache(tmp_path, ttl=3600)
    await cache.set("plugin:EMAIL:default@test.com", {"x": 1}, ttl=None)
    result = cache.get("plugin:EMAIL:default@test.com")
    assert result == {"x": 1}


# ---------------------------------------------------------------------------
# AC4: invalidate()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalidate_deletes_matching_entries(tmp_path):
    """invalidate(target) removes all entries whose key contains target."""
    cache = make_cache(tmp_path)
    await cache.set("holehe:EMAIL:alice@test.com", {"data": 1})
    await cache.set("maigret:EMAIL:alice@test.com", {"data": 2})
    await cache.set("holehe:EMAIL:bob@test.com", {"data": 3})

    deleted = await cache.invalidate("alice@test.com")
    assert deleted == 2  # alice entries deleted

    # Alice entries gone
    assert cache.get("holehe:EMAIL:alice@test.com") is None
    assert cache.get("maigret:EMAIL:alice@test.com") is None
    # Bob's entry intact
    assert cache.get("holehe:EMAIL:bob@test.com") == {"data": 3}


@pytest.mark.asyncio
async def test_invalidate_returns_zero_when_no_match(tmp_path):
    """invalidate() returns 0 when no entries match."""
    cache = make_cache(tmp_path)
    deleted = await cache.invalidate("nonexistent@example.com")
    assert deleted == 0


@pytest.mark.asyncio
async def test_invalidate_empty_target_returns_zero(tmp_path):
    """invalidate('') must not delete anything — guard against LIKE '%%'."""
    cache = make_cache(tmp_path)
    await cache.set("plugin:EMAIL:keep@test.com", {"data": 1})
    deleted = await cache.invalidate("")
    assert deleted == 0
    assert cache.get("plugin:EMAIL:keep@test.com") == {"data": 1}


# ---------------------------------------------------------------------------
# AC5: cleanup_expired()
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cleanup_expired_removes_expired_entries(tmp_path):
    """cleanup_expired() deletes expired entries and returns count."""
    import sqlite3
    db = str(tmp_path / "cache.db")

    # Manually insert expired and live entries
    import sqlite3 as _sqlite3
    _conn = _sqlite3.connect(db)
    _conn.execute("CREATE TABLE cache (key TEXT PRIMARY KEY, data TEXT, expires_at REAL)")
    _conn.execute("INSERT INTO cache VALUES ('old:key:1', '{}', ?)", (time.time() - 100,))  # expired
    _conn.execute("INSERT INTO cache VALUES ('old:key:2', '{}', ?)", (time.time() - 1,))    # expired
    _conn.execute("INSERT INTO cache VALUES ('live:key:1', '{}', ?)", (time.time() + 3600,))  # live
    _conn.commit()
    _conn.close()

    cache = PluginCache(db_path=db, ttl=3600)  # __init__ calls cleanup_expired()
    # After init, 2 expired entries should be gone
    with sqlite3.connect(db) as conn:
        count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
    assert count == 1, "Only live entry should remain"


@pytest.mark.asyncio
async def test_cleanup_expired_returns_count(tmp_path):
    """cleanup_expired() returns the number of deleted entries."""
    cache = make_cache(tmp_path)
    # Manually insert expired entry by calling set with immediate expiry then directly
    await cache.set("plugin:X:expired1", {"d": 1}, ttl=0)
    await cache.set("plugin:X:expired2", {"d": 2}, ttl=0)
    await cache.set("plugin:X:live", {"d": 3}, ttl=3600)
    # Mock time to ensure expiry
    with patch("Core.cache.plugin_cache.time") as mock_time:
        mock_time.time.return_value = time.time() + 1
        deleted = await cache.cleanup_expired()
    assert deleted >= 2


# ---------------------------------------------------------------------------
# AC6: Thread safety (asyncio.Lock)
# ---------------------------------------------------------------------------

def test_cache_has_asyncio_lock(tmp_path):
    """PluginCache has an asyncio.Lock instance."""
    cache = make_cache(tmp_path)
    assert isinstance(cache._lock, asyncio.Lock)


@pytest.mark.asyncio
async def test_concurrent_set_operations(tmp_path):
    """Multiple concurrent set() calls complete without error."""
    cache = make_cache(tmp_path)

    async def write(i):
        await cache.set(f"plugin:EMAIL:user{i}@test.com", {"index": i})

    await asyncio.gather(*[write(i) for i in range(10)])

    # All 10 entries should be written
    for i in range(10):
        result = cache.get(f"plugin:EMAIL:user{i}@test.com")
        assert result == {"index": i}


# ---------------------------------------------------------------------------
# AC7: PluginManager cache integration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_plugin_manager_cache_hit(tmp_path):
    """PluginManager returns cached result without calling plugin.check()."""
    cache = make_cache(tmp_path)
    cached_data = {"registered": ["instagram"], "total": 1}

    # Pre-populate cache
    key = "MockPlugin:EMAIL:target@test.com"
    await cache.set(key, cached_data)

    # Mock plugin — use spec to prevent MagicMock auto-creating normalize_target
    mock_plugin = MagicMock(spec=["name", "requires_api_key", "check"])
    mock_plugin.name = "MockPlugin"
    mock_plugin.requires_api_key = False
    mock_plugin.check = AsyncMock()

    manager = PluginManager(cache=cache)
    manager.register(mock_plugin)
    results = await manager.run_all("target@test.com", "EMAIL")

    assert len(results) == 1
    assert results[0].is_success is True
    assert results[0].data == cached_data
    mock_plugin.check.assert_not_called()  # Cache hit — plugin not called


@pytest.mark.asyncio
async def test_plugin_manager_cache_miss_calls_plugin(tmp_path):
    """On cache miss, PluginManager calls the plugin and stores result."""
    cache = make_cache(tmp_path)

    mock_plugin = MagicMock(spec=["name", "requires_api_key", "check"])
    mock_plugin.name = "MockPlugin"
    mock_plugin.requires_api_key = False
    mock_plugin.check = AsyncMock(return_value=PluginResult(
        plugin_name="MockPlugin", is_success=True, data={"result": "fresh"}
    ))

    manager = PluginManager(cache=cache)
    manager.register(mock_plugin)
    results = await manager.run_all("target@test.com", "EMAIL")

    assert len(results) == 1
    assert results[0].data == {"result": "fresh"}
    mock_plugin.check.assert_called_once()

    # Subsequent call should hit cache
    results2 = await manager.run_all("target@test.com", "EMAIL")
    assert results2[0].data == {"result": "fresh"}
    mock_plugin.check.assert_called_once()  # Still called only once


@pytest.mark.asyncio
async def test_plugin_manager_failed_result_not_cached(tmp_path):
    """PluginManager does NOT cache failed plugin results."""
    cache = make_cache(tmp_path)

    mock_plugin = MagicMock(spec=["name", "requires_api_key", "check"])
    mock_plugin.name = "MockPlugin"
    mock_plugin.requires_api_key = False
    mock_plugin.check = AsyncMock(return_value=PluginResult(
        plugin_name="MockPlugin", is_success=False, data={}, error_message="API error"
    ))

    manager = PluginManager(cache=cache)
    manager.register(mock_plugin)
    await manager.run_all("target@test.com", "EMAIL")

    # Second call should call plugin again (failure not cached)
    await manager.run_all("target@test.com", "EMAIL")
    assert mock_plugin.check.call_count == 2


@pytest.mark.asyncio
async def test_plugin_manager_without_cache_works_normally():
    """PluginManager without cache (cache=None) behaves as before."""
    mock_plugin = MagicMock(spec=["name", "requires_api_key", "check"])
    mock_plugin.name = "MockPlugin"
    mock_plugin.requires_api_key = False
    mock_plugin.check = AsyncMock(return_value=PluginResult(
        plugin_name="MockPlugin", is_success=True, data={"x": 1}
    ))

    manager = PluginManager()  # no cache
    manager.register(mock_plugin)
    results = await manager.run_all("target@test.com", "EMAIL")

    assert len(results) == 1
    assert results[0].is_success is True
    mock_plugin.check.assert_called_once()
