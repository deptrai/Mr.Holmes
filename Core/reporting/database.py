"""
Core/reporting/database.py

Database singleton — Story 6.1 (AC6).
Manages SQLite connection lifecycle and schema migration.

Usage:
    db = Database.get_instance()
    db.ensure_schema()
    conn = db.connection
"""
from __future__ import annotations

# F2: removed unused 'import os' — Path handles everything
import sqlite3
import threading
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Resolve schema.sql relative to THIS file — immune to CWD changes
_SCHEMA_PATH = Path(__file__).parent / "schema.sql"
_DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "GUI" / "Reports" / "mrholmes.db"


class Database:
    """
    Thread-safe SQLite singleton for the Mr.Holmes reporting layer.

    AC6: Singleton pattern — one shared connection per process.
    AC5: ensure_schema() runs CREATE TABLE IF NOT EXISTS migrations.
    """

    _instance: Database | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------
    @classmethod
    def get_instance(cls, db_path: str | Path | None = None) -> "Database":
        """Return the process-wide Database singleton, creating it if needed."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(db_path)
                cls._instance.ensure_schema()
            elif db_path is not None:
                # F3: Warn if caller expects a different db_path
                requested = Path(db_path)
                if requested != cls._instance._db_path:
                    logger.warning(
                        "Database singleton already exists at '%s'; "
                        "ignoring requested path '%s'",
                        cls._instance._db_path, requested,
                    )
            return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Tear down the singleton (test isolation helper)."""
        with cls._lock:
            if cls._instance is not None and cls._instance._conn is not None:
                cls._instance._conn.close()
            cls._instance = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------
    @property
    def connection(self) -> sqlite3.Connection:
        """Lazily open and return the SQLite connection."""
        if self._conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")
            logger.debug("SQLite connection opened: %s", self._db_path)
        return self._conn

    def close(self) -> None:
        """Explicitly close the connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
            logger.debug("SQLite connection closed.")

    # ------------------------------------------------------------------
    # AC5: Schema migration
    # ------------------------------------------------------------------
    def ensure_schema(self) -> None:
        """
        Run the schema.sql migration script.
        All statements use CREATE TABLE IF NOT EXISTS — safe to run repeatedly.

        Note: executescript() issues an implicit COMMIT before executing.
        Do NOT call this inside an in-progress transaction.
        """
        # F13: Guard against missing schema file
        if not _SCHEMA_PATH.exists():
            raise FileNotFoundError(
                "Schema file not found: %s. "
                "Ensure Core/reporting/schema.sql is present." % _SCHEMA_PATH
            )
        sql = _SCHEMA_PATH.read_text(encoding="utf-8")
        conn = self.connection
        try:
            conn.executescript(sql)
            conn.commit()
            logger.info("Schema migration completed: %s", _SCHEMA_PATH)
        except sqlite3.Error as exc:
            logger.error("Schema migration failed: %s", exc)
            raise

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute a single DML statement."""
        return self.connection.execute(sql, params)

    def executemany(self, sql: str, params_seq) -> sqlite3.Cursor:
        """Batch execute a prepared statement."""
        return self.connection.executemany(sql, params_seq)

    def commit(self) -> None:
        self.connection.commit()

    def rollback(self) -> None:
        self.connection.rollback()

    # context-manager support
    def __enter__(self) -> "Database":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            self.rollback()
        else:
            self.commit()
