# Story 9.5: Cache Layer

Status: review

## Story

As the plugin system,
I want a transparent cache layer so that repeated queries for the same target don't re-hit external APIs,
so that ban risk is reduced and pipeline speed improves on subsequent runs.

## Acceptance Criteria

1. `PluginCache` class tại `Core/cache/plugin_cache.py`:
   - SQLite backend, file tại `GUI/Reports/Autonomous/plugin_cache.db` (cùng thư mục với reports)
   - TTL configurable qua env var `MH_CACHE_TTL` (default `86400` — 24 giờ)
   - Cache key format: `f"{plugin_name}:{target_type}:{target_value}"`

2. `get(key: str) -> dict | None`:
   - Trả về cached `result.data` dict nếu entry tồn tại và chưa expired
   - Trả về `None` nếu miss hoặc expired (expired entries không bị xóa ngay, lazy cleanup)

3. `set(key: str, value: dict, ttl: int | None = None) -> None`:
   - Lưu `value` với expiry timestamp = `now + ttl`
   - `ttl=None` → dùng class default TTL từ `MH_CACHE_TTL`
   - Upsert (INSERT OR REPLACE)

4. `invalidate(target: str) -> int`:
   - Xóa tất cả cache entries có `key` chứa `target` string
   - Return số entries đã xóa

5. `cleanup_expired() -> int`:
   - Xóa tất cả entries đã expired
   - Return số entries đã xóa
   - Được gọi automatically tại `__init__` (một lần per session)

6. Thread-safe với `asyncio.Lock` — một lock duy nhất per cache instance cho tất cả writes

7. Cache wrapping trong `PluginManager` (tại `Core/plugins/manager.py`):
   - `PluginManager.__init__` nhận optional `cache: PluginCache | None = None`
   - Trong `_safe_execute()`: kiểm tra cache trước khi gọi plugin
   - Cache hit → reconstruct `PluginResult` từ cached data, log "Cache hit for {plugin}: {target}"
   - Cache miss → chạy plugin, store result nếu `is_success=True`
   - Plugins không cần biết cache tồn tại

8. Unit tests tại `tests/cache/test_plugin_cache.py` ≥ 80% coverage:
   - Test cache hit → correct data returned
   - Test cache miss → None returned
   - Test TTL expiry → expired entry returns None
   - Test invalidate → matching entries deleted, count correct
   - Test cleanup_expired → only expired removed
   - Test PluginManager cache integration (mock plugin + mock cache)

## Tasks / Subtasks

- [x] Task 1: Tạo `Core/cache/` package (AC: 1)
  - [x] `Core/cache/__init__.py` (empty)
  - [x] `Core/cache/plugin_cache.py`
  - [x] SQLite schema: `CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, data TEXT, expires_at REAL)`

- [x] Task 2: Implement `PluginCache` (AC: 1-6)
  - [x] `__init__(db_path: str | None = None, ttl: int | None = None)` — db_path default từ `GUI/Reports/Autonomous/plugin_cache.db`
  - [x] `get()` với TTL check
  - [x] `set()` với upsert và expiry
  - [x] `invalidate()` với LIKE query
  - [x] `cleanup_expired()` — chạy tại `__init__`
  - [x] `asyncio.Lock` cho write operations

- [x] Task 3: Update `PluginManager` (AC: 7)
  - [x] Thêm `cache: PluginCache | None = None` parameter
  - [x] Wrap `_safe_execute()` với cache check/store logic

- [x] Task 4: Viết unit tests (AC: 8)
  - [x] `tests/cache/test_plugin_cache.py`
  - [x] Dùng `tmp_path` pytest fixture cho SQLite file

## Dev Notes

### SQLite Schema & Operations

```python
import sqlite3
import json
import time
import asyncio
import os
from pathlib import Path

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cache (
    key       TEXT PRIMARY KEY,
    data      TEXT NOT NULL,
    expires_at REAL NOT NULL
)
"""

class PluginCache:
    def __init__(self, db_path: str | None = None, ttl: int | None = None) -> None:
        if db_path is None:
            db_path = "GUI/Reports/Autonomous/plugin_cache.db"
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._ttl = ttl or int(os.getenv("MH_CACHE_TTL", "86400"))
        self._lock = asyncio.Lock()
        # Init DB schema + cleanup expired
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(CREATE_TABLE_SQL)
            conn.commit()
        self.cleanup_expired()

    def get(self, key: str) -> dict | None:
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT data, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        data_str, expires_at = row
        if time.time() > expires_at:
            return None  # Expired — lazy, not deleted here
        return json.loads(data_str)

    async def set(self, key: str, value: dict, ttl: int | None = None) -> None:
        expires_at = time.time() + (ttl if ttl is not None else self._ttl)
        async with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, data, expires_at) VALUES (?, ?, ?)",
                    (key, json.dumps(value), expires_at),
                )
                conn.commit()
```

### Cache Key Construction (trong PluginManager)

```python
def _cache_key(self, plugin: IntelligencePlugin, target: str, target_type: str) -> str:
    try:
        name = plugin.name
    except Exception:
        name = "unknown"
    return f"{name}:{target_type.upper()}:{target.lower()}"
```

### PluginManager Integration Pattern

```python
async def _safe_execute(self, plugin, target, target_type):
    if self._cache is not None:
        key = self._cache_key(plugin, target, target_type)
        cached = self._cache.get(key)
        if cached is not None:
            logger.debug("Cache hit for %s: %s", plugin.name, target)
            return PluginResult(plugin_name=plugin.name, is_success=True, data=cached)

    result = await self._run_plugin(plugin, target, target_type)

    if self._cache is not None and result.is_success and result.data:
        await self._cache.set(key, result.data)

    return result
```

### File Locations

| File | Action |
|------|--------|
| `Core/cache/__init__.py` | CREATE (empty) |
| `Core/cache/plugin_cache.py` | CREATE |
| `Core/plugins/manager.py` | MODIFY — add cache integration |
| `tests/cache/test_plugin_cache.py` | CREATE |
| `tests/cache/__init__.py` | CREATE (empty) |

### Project Structure Notes

- `GUI/Reports/Autonomous/plugin_cache.db` — cùng thư mục với reports để user dễ clear
- `PluginCache` không coupled với `PluginResult` — store và retrieve `dict` (`.data` field)
- `get()` là sync (SQLite read nhanh), `set()` là async (để acquire lock)
- Không implement distributed cache — SQLite đủ cho single-user CLI tool
- `cleanup_expired()` là sync — chạy tại init, không gây async overhead

### References

- `Core/plugins/manager.py` — file sẽ được modify
- PRD FR26-FR28 (cache layer, TTL, invalidation): `_bmad-output/planning-artifacts/prd-epic9.md`
- NFR5 (cache hit rate ≥ 60%): `_bmad-output/planning-artifacts/prd-epic9.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No issues. All 20 tests passed on first implementation run.

### Completion Notes List

- `PluginCache` implemented with SQLite backend, async lock for writes, sync reads
- `get()` là sync (SQLite read nhanh), `set()`/`invalidate()` acquire `asyncio.Lock`
- `cleanup_expired()` chạy once tại `__init__` — lazy, không block
- `PluginManager.__init__` nhận `cache: PluginCache | None = None` — backward compatible (no-arg still works)
- `_safe_execute()` refactored: cache check → plugin run → cache store (success-only)
- `_cache_key()` helper: `"{name}:{TARGET_TYPE}:{target_lower}"` — deterministic, case-insensitive
- Cache wrapping is transparent — plugins không biết cache tồn tại
- 20 unit tests covering: DB creation, TTL env config, get/set/invalidate/cleanup, concurrent writes, PluginManager hit/miss/fail-not-cached/no-cache

### File List

- `Core/cache/__init__.py` (created)
- `Core/cache/plugin_cache.py` (created)
- `Core/plugins/manager.py` (modified — cache integration)
- `tests/cache/__init__.py` (created)
- `tests/cache/test_plugin_cache.py` (created)
