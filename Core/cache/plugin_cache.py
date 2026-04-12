"""
Core/cache/plugin_cache.py

Story 9.5 — PluginCache: SQLite-backed transparent cache layer for plugin results.
Reduces redundant API calls and ban risk by caching successful PluginResult.data.
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
from pathlib import Path

_DEFAULT_DB_PATH = str(Path(__file__).resolve().parents[2] / "GUI" / "Reports" / "Autonomous" / "plugin_cache.db")
_DEFAULT_TTL = 86400  # 24 hours
_DEFAULT_MAX_ENTRIES = 10000

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cache (
    key        TEXT PRIMARY KEY,
    data       TEXT NOT NULL,
    expires_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cache_expires_at ON cache(expires_at);
"""


class PluginCache:
    """
    Transparent SQLite cache for plugin results.

    - TTL configurable via `MH_CACHE_TTL` env var (default 86400 seconds).
    - get() is synchronous (fast SQLite read).
    - set()/invalidate() acquire asyncio.Lock for write safety.
    - cleanup_expired() runs once at __init__ (lazy, per-session).
    """

    def __init__(self, db_path: str | None = None, ttl: int | None = None) -> None:
        if db_path is None:
            db_path = _DEFAULT_DB_PATH
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        try:
            self._ttl: int = ttl if ttl is not None else int(os.getenv("MH_CACHE_TTL", str(_DEFAULT_TTL)))
        except ValueError:
            self._ttl = _DEFAULT_TTL
        try:
            self._max_entries: int = int(os.getenv("MH_CACHE_MAX_ENTRIES", str(_DEFAULT_MAX_ENTRIES)))
        except ValueError:
            self._max_entries = _DEFAULT_MAX_ENTRIES
        self._lock = asyncio.Lock()

        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_CREATE_TABLE_SQL)
            # Sync cleanup at init — no lock needed, no other tasks running yet
            conn.execute("DELETE FROM cache WHERE expires_at <= ?", (time.time(),))
            conn.commit()

    # ------------------------------------------------------------------
    # AC2: get()
    # ------------------------------------------------------------------

    def get(self, key: str) -> dict | None:
        """
        Return cached data dict if the entry exists and has not expired.
        Returns None on miss or expiry. Expired entries are NOT deleted here (lazy).
        """
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT data, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        data_str, expires_at = row
        if time.time() > expires_at:
            return None
        try:
            return json.loads(data_str)
        except (json.JSONDecodeError, TypeError):
            return None

    # ------------------------------------------------------------------
    # AC3: set()
    # ------------------------------------------------------------------

    async def set(self, key: str, value: dict, ttl: int | None = None) -> None:
        """
        Store value with expiry. Upserts existing keys.
        ttl=None uses instance default (from MH_CACHE_TTL or 86400).
        """
        effective_ttl = ttl if ttl is not None else self._ttl
        expires_at = time.time() + effective_ttl
        async with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO cache (key, data, expires_at) VALUES (?, ?, ?)",
                    (key, json.dumps(value), expires_at),
                )
                # Evict oldest entries if cache exceeds max size
                count = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
                if count > self._max_entries:
                    conn.execute(
                        "DELETE FROM cache WHERE key IN ("
                        "  SELECT key FROM cache ORDER BY expires_at ASC LIMIT ?"
                        ")",
                        (count - self._max_entries,),
                    )
                conn.commit()

    # ------------------------------------------------------------------
    # AC4: invalidate()
    # ------------------------------------------------------------------

    async def invalidate(self, target: str) -> int:
        """
        Delete all cache entries whose key contains target string.
        Returns number of deleted entries.
        """
        if not target:
            return 0
        # Escape LIKE wildcards so % and _ in target are treated literally
        escaped = target.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        async with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM cache WHERE key LIKE ? ESCAPE '\\'", (f"%{escaped}%",)
                )
                conn.commit()
                return cursor.rowcount

    # ------------------------------------------------------------------
    # AC5: cleanup_expired()
    # ------------------------------------------------------------------

    async def cleanup_expired(self) -> int:
        """
        Delete all expired entries. Returns count deleted.
        Called automatically once at __init__ per session.
        """
        async with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM cache WHERE expires_at <= ?", (time.time(),)
                )
                conn.commit()
                return cursor.rowcount
