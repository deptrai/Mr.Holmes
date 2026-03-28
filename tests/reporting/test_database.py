"""
tests/reporting/test_database.py

Unit tests for Story 6.1 — SQLite Schema Design.
Uses tmp_path fixture for file-backed SQLite isolation.
"""
from __future__ import annotations

import sqlite3
import pytest
from Core.reporting.database import Database


@pytest.fixture(autouse=True)
def reset_singleton():
    """Ensure Database singleton is torn down between tests."""
    Database.reset_instance()
    yield
    Database.reset_instance()


@pytest.fixture
def db(tmp_path):
    """Return a fresh Database backed by a temp file."""
    instance = Database(db_path=tmp_path / "test.db")
    instance.ensure_schema()
    return instance


# ------------------------------------------------------------------
# AC1, AC2, AC3, AC4 — Schema tables exist with correct columns
# ------------------------------------------------------------------
class TestSchemaCreation:
    def test_investigations_table_exists(self, db):
        cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='investigations'")
        assert cur.fetchone() is not None

    def test_findings_table_exists(self, db):
        cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='findings'")
        assert cur.fetchone() is not None

    def test_tags_table_exists(self, db):
        cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tags'")
        assert cur.fetchone() is not None

    def test_finding_tags_table_exists(self, db):
        cur = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='finding_tags'")
        assert cur.fetchone() is not None

    def test_investigations_has_required_columns(self, db):
        cur = db.execute("PRAGMA table_info(investigations)")
        columns = {row[1] for row in cur.fetchall()}
        assert {"id", "subject", "subject_type", "created_at", "proxy_used",
                "total_sites", "total_found"}.issubset(columns)

    def test_findings_has_required_columns(self, db):
        cur = db.execute("PRAGMA table_info(findings)")
        columns = {row[1] for row in cur.fetchall()}
        assert {"id", "investigation_id", "site_name", "url", "status",
                "is_scrapable", "scraped", "raw_response", "error_type"}.issubset(columns)


# ------------------------------------------------------------------
# AC5 — ensure_schema() is idempotent
# ------------------------------------------------------------------
class TestSchemaMigration:
    def test_ensure_schema_idempotent(self, db):
        """Running ensure_schema() twice must not raise."""
        db.ensure_schema()  # second call
        # If no exception, test passes

    def test_schema_persists_across_reopen(self, tmp_path):
        """Data survives connection close and re-open."""
        path = tmp_path / "persist.db"
        db1 = Database(db_path=path)
        db1.ensure_schema()
        db1.execute(
            "INSERT INTO investigations (subject, subject_type) VALUES (?, ?)",
            ("luisphan", "USERNAME"),
        )
        db1.commit()
        db1.close()

        db2 = Database(db_path=path)
        db2.ensure_schema()
        cur = db2.execute("SELECT subject FROM investigations WHERE subject=?", ("luisphan",))
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "luisphan"
        db2.close()


# ------------------------------------------------------------------
# AC6 — Database singleton
# ------------------------------------------------------------------
class TestSingleton:
    def test_get_instance_returns_same_object(self, tmp_path):
        a = Database.get_instance(db_path=tmp_path / "s.db")
        b = Database.get_instance(db_path=tmp_path / "s.db")
        assert a is b

    def test_reset_clears_singleton(self, tmp_path):
        a = Database.get_instance(db_path=tmp_path / "r.db")
        Database.reset_instance()
        b = Database.get_instance(db_path=tmp_path / "r.db")
        assert a is not b


# ------------------------------------------------------------------
# Data integrity — FK, CHECK constraints, indexes
# ------------------------------------------------------------------
class TestDataIntegrity:
    def test_insert_and_query_investigation(self, db):
        db.execute(
            "INSERT INTO investigations (subject, subject_type, proxy_used, total_sites, total_found)"
            " VALUES (?, ?, ?, ?, ?)",
            ("john", "USERNAME", False, 150, 42),
        )
        db.commit()
        cur = db.execute("SELECT total_found FROM investigations WHERE subject='john'")
        assert cur.fetchone()[0] == 42

    def test_insert_finding_linked_to_investigation(self, db):
        db.execute(
            "INSERT INTO investigations (subject, subject_type) VALUES (?, ?)",
            ("alice", "EMAIL"),
        )
        inv_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO findings (investigation_id, site_name, url, status) VALUES (?, ?, ?, ?)",
            (inv_id, "GitHub", "https://github.com/alice", "found"),
        )
        db.commit()
        cur = db.execute(
            "SELECT site_name FROM findings WHERE investigation_id=?", (inv_id,)
        )
        assert cur.fetchone()[0] == "GitHub"

    def test_invalid_subject_type_rejected(self, db):
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO investigations (subject, subject_type) VALUES (?, ?)",
                ("x", "INVALID_TYPE"),
            )

    def test_invalid_status_rejected(self, db):
        db.execute(
            "INSERT INTO investigations (subject, subject_type) VALUES (?, ?)",
            ("bob", "USERNAME"),
        )
        inv_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO findings (investigation_id, site_name, status) VALUES (?, ?, ?)",
                (inv_id, "Twitter", "INVALID_STATUS"),
            )

    def test_tags_and_bridge_table(self, db):
        db.execute("INSERT INTO tags (name) VALUES (?)", ("social",))
        tag_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO investigations (subject, subject_type) VALUES (?, ?)",
            ("charlie", "USERNAME"),
        )
        inv_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO findings (investigation_id, site_name, status) VALUES (?, ?, ?)",
            (inv_id, "Instagram", "found"),
        )
        finding_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO finding_tags (finding_id, tag_id) VALUES (?, ?)",
            (finding_id, tag_id),
        )
        db.commit()
        cur = db.execute(
            "SELECT t.name FROM tags t"
            " JOIN finding_tags ft ON ft.tag_id = t.id"
            " WHERE ft.finding_id = ?",
            (finding_id,),
        )
        assert cur.fetchone()[0] == "social"

    def test_cascading_delete_findings(self, db):
        db.execute(
            "INSERT INTO investigations (subject, subject_type) VALUES (?, ?)",
            ("dave", "USERNAME"),
        )
        inv_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute(
            "INSERT INTO findings (investigation_id, site_name) VALUES (?, ?)",
            (inv_id, "Reddit"),
        )
        db.commit()
        db.execute("DELETE FROM investigations WHERE id = ?", (inv_id,))
        db.commit()
        cur = db.execute("SELECT id FROM findings WHERE investigation_id = ?", (inv_id,))
        assert cur.fetchone() is None

    def test_context_manager_commits_on_success(self, tmp_path):
        db = Database(db_path=tmp_path / "ctx.db")
        db.ensure_schema()
        with db:
            db.execute(
                "INSERT INTO investigations (subject, subject_type) VALUES (?, ?)",
                ("eve", "PHONE"),
            )
        cur = db.execute("SELECT subject FROM investigations WHERE subject='eve'")
        assert cur.fetchone() is not None
        db.close()

    # F6: Test rollback path of __exit__
    def test_context_manager_rollbacks_on_exception(self, tmp_path):
        """Verify __exit__ rolls back when an exception is raised inside the with block."""
        db = Database(db_path=tmp_path / "rollback.db")
        db.ensure_schema()
        # Insert a valid row first
        db.execute(
            "INSERT INTO investigations (subject, subject_type) VALUES (?, ?)",
            ("frank", "USERNAME"),
        )
        db.commit()

        # Now try to insert inside a with block that raises
        try:
            with db:
                db.execute(
                    "INSERT INTO investigations (subject, subject_type) VALUES (?, ?)",
                    ("ghost", "USERNAME"),
                )
                raise ValueError("simulated error")
        except ValueError:
            pass

        # "ghost" must NOT be persisted due to rollback
        cur = db.execute("SELECT subject FROM investigations WHERE subject='ghost'")
        assert cur.fetchone() is None
        # "frank" must still be there
        cur = db.execute("SELECT subject FROM investigations WHERE subject='frank'")
        assert cur.fetchone() is not None
        db.close()

    def test_findings_has_created_at(self, db):
        """F1: Verify findings table has created_at column."""
        cur = db.execute("PRAGMA table_info(findings)")
        columns = {row[1] for row in cur.fetchall()}
        assert "created_at" in columns
