"""
Core/Support/Proxy_Audit.py

SQLite audit trail cho proxy-assisted HTTP requests.
Ghi nhận timestamp, target host, proxy hash, status code, duration, source module.
Retention policy tự động purge entries cũ hơn max_age_days.

Security: proxy address được hash SHA-256 (truncated 16 hex chars),
không bao giờ lưu raw IP. Target URL chỉ lưu host, không lưu path.
"""
import hashlib
import os
import sqlite3
import time
from urllib.parse import urlparse


class Proxy_Audit:
    """Audit trail cho proxy requests. Local SQLite, không transmit off-machine."""

    _DB_NAME = "proxy_audit.db"
    _PURGE_INTERVAL_SECONDS = 3600  # lazy purge at most once per hour
    _last_purge_at = 0.0

    @staticmethod
    def _db_path():
        """Resolve proxy_audit.db path relative to repo root."""
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return os.path.join(root, Proxy_Audit._DB_NAME)

    @staticmethod
    def _connect():
        """Open SQLite connection and ensure schema exists."""
        path = Proxy_Audit._db_path()
        conn = sqlite3.connect(path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS proxy_audit_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                target_host TEXT NOT NULL,
                proxy_hash TEXT NOT NULL,
                status_code INTEGER NOT NULL,
                duration_ms INTEGER NOT NULL,
                source_module TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_proxy_audit_timestamp "
            "ON proxy_audit_entries(timestamp)"
        )
        conn.commit()
        return conn

    @staticmethod
    def _hash_proxy(proxy_addr):
        """SHA-256 hash proxy address, truncate to 16 hex chars."""
        return hashlib.sha256(proxy_addr.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _extract_host(url):
        """Extract host from URL, truncate to 255 chars."""
        parsed = urlparse(url)
        host = parsed.hostname or ""
        return host[:255]

    @staticmethod
    def log(target_url, proxy_addr, status_code, duration_ms, source_module):
        """
        Insert audit entry. Returns entry id.

        Raises ValueError on invalid input, sqlite3.Error on DB failure.
        """
        if not target_url:
            raise ValueError("target_url must not be empty")
        if duration_ms < 0:
            raise ValueError("duration_ms must be non-negative")
        if not proxy_addr:
            raise ValueError("proxy_addr must not be empty")
        if not source_module:
            raise ValueError("source_module must not be empty")

        host = Proxy_Audit._extract_host(target_url)
        if not host:
            raise ValueError("target_url must have a valid host")

        proxy_hash = Proxy_Audit._hash_proxy(proxy_addr)

        conn = Proxy_Audit._connect()
        try:
            cursor = conn.execute(
                """
                INSERT INTO proxy_audit_entries
                    (target_host, proxy_hash, status_code, duration_ms, source_module)
                VALUES (?, ?, ?, ?, ?)
                """,
                (host, proxy_hash, status_code, duration_ms, source_module[:100]),
            )
            conn.commit()
            entry_id = cursor.lastrowid
        finally:
            conn.close()

        Proxy_Audit._maybe_purge()
        return entry_id

    @staticmethod
    def _maybe_purge(max_age_days=30):
        """Lazy purge: run at most once per _PURGE_INTERVAL_SECONDS."""
        now = time.time()
        if now - Proxy_Audit._last_purge_at < Proxy_Audit._PURGE_INTERVAL_SECONDS:
            return 0
        Proxy_Audit._last_purge_at = now
        return Proxy_Audit.purge(max_age_days)

    @staticmethod
    def purge(max_age_days=30):
        """
        Delete entries older than max_age_days. Returns count deleted.
        """
        conn = Proxy_Audit._connect()
        try:
            cursor = conn.execute(
                "DELETE FROM proxy_audit_entries "
                "WHERE timestamp < datetime('now', ?)",
                ("-%d days" % max_age_days,),
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    @staticmethod
    def query(limit=100, source_module=None):
        """
        Query recent audit entries. Returns list of dicts, newest first.
        """
        conn = Proxy_Audit._connect()
        try:
            if source_module:
                cursor = conn.execute(
                    "SELECT id, timestamp, target_host, proxy_hash, "
                    "status_code, duration_ms, source_module "
                    "FROM proxy_audit_entries "
                    "WHERE source_module = ? "
                    "ORDER BY id DESC LIMIT ?",
                    (source_module, limit),
                )
            else:
                cursor = conn.execute(
                    "SELECT id, timestamp, target_host, proxy_hash, "
                    "status_code, duration_ms, source_module "
                    "FROM proxy_audit_entries "
                    "ORDER BY id DESC LIMIT ?",
                    (limit,),
                )
            rows = cursor.fetchall()
            return [
                {
                    "id": r[0],
                    "timestamp": r[1],
                    "target_host": r[2],
                    "proxy_hash": r[3],
                    "status_code": r[4],
                    "duration_ms": r[5],
                    "source_module": r[6],
                }
                for r in rows
            ]
        finally:
            conn.close()

    @staticmethod
    def count():
        """Return total entry count."""
        conn = Proxy_Audit._connect()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM proxy_audit_entries")
            return cursor.fetchone()[0]
        finally:
            conn.close()
