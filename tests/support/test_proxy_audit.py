"""
tests/support/test_proxy_audit.py

Unit + integration tests cho Core.Support.Proxy_Audit.
Story US-002 — Proxy Audit Trail with SQLite + retention.
"""
import os
import time
from unittest import mock

import pytest

from Core.Support.Proxy_Audit import Proxy_Audit


@pytest.fixture
def audit_db(tmp_path, monkeypatch):
    """Redirect Proxy_Audit to a temp database."""
    db_path = str(tmp_path / "test_proxy_audit.db")
    monkeypatch.setattr(Proxy_Audit, "_db_path", staticmethod(lambda: db_path))
    Proxy_Audit._last_purge_at = 0.0
    return db_path


class TestHashProxy:
    """Test proxy address hashing."""

    def test_hash_is_16_hex_chars(self):
        h = Proxy_Audit._hash_proxy("203.0.113.1:8080")
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_is_deterministic(self):
        h1 = Proxy_Audit._hash_proxy("203.0.113.1:8080")
        h2 = Proxy_Audit._hash_proxy("203.0.113.1:8080")
        assert h1 == h2

    def test_different_proxies_different_hash(self):
        h1 = Proxy_Audit._hash_proxy("203.0.113.1:8080")
        h2 = Proxy_Audit._hash_proxy("198.51.100.5:3128")
        assert h1 != h2


class TestExtractHost:
    """Test URL host extraction."""

    def test_https_url(self):
        assert Proxy_Audit._extract_host("https://example.com/path/to/page") == "example.com"

    def test_http_url(self):
        assert Proxy_Audit._extract_host("http://test.invalid") == "test.invalid"

    def test_url_with_port(self):
        assert Proxy_Audit._extract_host("https://example.com:8443/api") == "example.com"

    def test_long_host_truncated(self):
        long_host = "a" * 300 + ".com"
        result = Proxy_Audit._extract_host("https://" + long_host + "/path")
        assert len(result) <= 255


class TestLog:
    """Test log() insertion."""

    def test_log_returns_entry_id(self, audit_db):
        entry_id = Proxy_Audit.log(
            target_url="https://example.com/page",
            proxy_addr="203.0.113.1:8080",
            status_code=200,
            duration_ms=150,
            source_module="Requests_Search",
        )
        assert isinstance(entry_id, int)
        assert entry_id >= 1

    def test_log_stores_correct_host(self, audit_db):
        Proxy_Audit.log(
            "https://example.com/secret/path",
            "203.0.113.1:8080",
            200,
            100,
            "Requests_Search",
        )
        entries = Proxy_Audit.query()
        assert len(entries) == 1
        assert entries[0]["target_host"] == "example.com"
        assert "secret" not in entries[0]["target_host"]

    def test_log_stores_hashed_proxy(self, audit_db):
        Proxy_Audit.log(
            "https://example.com",
            "203.0.113.1:8080",
            200,
            100,
            "Requests_Search",
        )
        entries = Proxy_Audit.query()
        assert len(entries) == 1
        assert entries[0]["proxy_hash"] != "203.0.113.1:8080"
        assert len(entries[0]["proxy_hash"]) == 16

    def test_log_raises_on_empty_target(self, audit_db):
        with pytest.raises(ValueError, match="target_url"):
            Proxy_Audit.log("", "203.0.113.1:8080", 200, 100, "Requests_Search")

    def test_log_raises_on_negative_duration(self, audit_db):
        with pytest.raises(ValueError, match="duration_ms"):
            Proxy_Audit.log(
                "https://example.com",
                "203.0.113.1:8080",
                200,
                -1,
                "Requests_Search",
            )

    def test_log_raises_on_empty_proxy(self, audit_db):
        with pytest.raises(ValueError, match="proxy_addr"):
            Proxy_Audit.log("https://example.com", "", 200, 100, "Requests_Search")

    def test_log_raises_on_empty_source(self, audit_db):
        with pytest.raises(ValueError, match="source_module"):
            Proxy_Audit.log("https://example.com", "203.0.113.1:8080", 200, 100, "")

    def test_log_raises_on_invalid_host(self, audit_db):
        with pytest.raises(ValueError, match="valid host"):
            Proxy_Audit.log("not-a-url", "203.0.113.1:8080", 200, 100, "Requests_Search")


class TestQuery:
    """Test query() retrieval."""

    def test_query_returns_newest_first(self, audit_db):
        for i in range(3):
            Proxy_Audit.log(
                "https://example.com/%d" % i,
                "203.0.113.1:8080",
                200,
                100,
                "Requests_Search",
            )
        entries = Proxy_Audit.query()
        assert len(entries) == 3
        assert entries[0]["id"] > entries[2]["id"]

    def test_query_filters_by_source_module(self, audit_db):
        Proxy_Audit.log("https://a.com", "1.1.1.1:80", 200, 50, "Module_A")
        Proxy_Audit.log("https://b.com", "2.2.2.2:80", 404, 60, "Module_B")
        Proxy_Audit.log("https://c.com", "3.3.3.3:80", 200, 70, "Module_A")
        entries = Proxy_Audit.query(source_module="Module_A")
        assert len(entries) == 2
        assert all(e["source_module"] == "Module_A" for e in entries)

    def test_query_respects_limit(self, audit_db):
        for i in range(5):
            Proxy_Audit.log("https://example.com/%d" % i, "1.1.1.1:80", 200, 50, "M")
        entries = Proxy_Audit.query(limit=2)
        assert len(entries) == 2


class TestCount:
    """Test count()."""

    def test_count_empty(self, audit_db):
        assert Proxy_Audit.count() == 0

    def test_count_after_inserts(self, audit_db):
        for i in range(3):
            Proxy_Audit.log("https://example.com/%d" % i, "1.1.1.1:80", 200, 50, "M")
        assert Proxy_Audit.count() == 3


class TestPurge:
    """Test purge() retention."""

    def test_purge_deletes_old_entries(self, audit_db):
        import sqlite3

        # Insert an entry, then backdate its timestamp
        Proxy_Audit.log("https://old.com", "1.1.1.1:80", 200, 50, "M")
        conn = sqlite3.connect(audit_db)
        conn.execute(
            "UPDATE proxy_audit_entries SET timestamp = datetime('now', '-60 days')"
        )
        conn.commit()
        conn.close()

        # Insert a recent entry
        Proxy_Audit.log("https://new.com", "2.2.2.2:80", 200, 50, "M")

        deleted = Proxy_Audit.purge(max_age_days=30)
        assert deleted == 1
        assert Proxy_Audit.count() == 1

    def test_purge_leaves_recent_entries(self, audit_db):
        Proxy_Audit.log("https://recent.com", "1.1.1.1:80", 200, 50, "M")
        deleted = Proxy_Audit.purge(max_age_days=30)
        assert deleted == 0
        assert Proxy_Audit.count() == 1

    def test_purge_returns_count_deleted(self, audit_db):
        import sqlite3

        for i in range(3):
            Proxy_Audit.log("https://old%d.com" % i, "1.1.1.1:80", 200, 50, "M")
        conn = sqlite3.connect(audit_db)
        conn.execute(
            "UPDATE proxy_audit_entries SET timestamp = datetime('now', '-60 days')"
        )
        conn.commit()
        conn.close()

        deleted = Proxy_Audit.purge(max_age_days=30)
        assert deleted == 3


class TestSchemaCreation:
    """Integration: schema is created on first call."""

    def test_db_file_created_on_first_log(self, audit_db):
        assert not os.path.exists(audit_db)
        Proxy_Audit.log("https://example.com", "1.1.1.1:80", 200, 50, "M")
        assert os.path.exists(audit_db)

    def test_schema_idempotent(self, audit_db):
        """Multiple calls don't fail even if schema already exists."""
        Proxy_Audit.log("https://a.com", "1.1.1.1:80", 200, 50, "M")
        Proxy_Audit.log("https://b.com", "2.2.2.2:80", 200, 50, "M")
        assert Proxy_Audit.count() == 2
