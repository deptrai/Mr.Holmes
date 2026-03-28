"""
tests/reporting/test_writer.py

Unit tests for Story 6.2 — Dual-Write ReportWriter.
Verifies: flat file output, SQLite persistence, graceful degradation.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from Core.models.scan_context import ScanContext, ScanConfig
from Core.models.scan_result import ScanResult, ScanStatus
from Core.reporting.database import Database
from Core.reporting.writer import ReportWriter


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_db_singleton():
    Database.reset_instance()
    yield
    Database.reset_instance()


@pytest.fixture
def db(tmp_path):
    instance = Database(db_path=tmp_path / "test.db")
    instance.ensure_schema()
    return instance


@pytest.fixture
def ctx(tmp_path):
    report_path = tmp_path / "reports" / "testuser" / "testuser.txt"
    report_path.parent.mkdir(parents=True)
    return ScanContext(
        target="testuser",
        subject_type="USERNAME",
        report_path=str(report_path),
        json_output_path=str(tmp_path / "reports" / "testuser" / "testuser.json"),
        json_names_path=str(tmp_path / "reports" / "testuser" / "Name.json"),
    )


@pytest.fixture
def cfg():
    return ScanConfig(proxy_enabled=False)


@pytest.fixture
def results():
    return [
        ScanResult(
            site_name="GitHub",
            url="https://github.com/testuser",
            status=ScanStatus.FOUND,
            is_scrapable=False,
            tags=["Developer", "Code"],
        ),
        ScanResult(
            site_name="Twitter",
            url="https://twitter.com/testuser",
            status=ScanStatus.NOT_FOUND,
            tags=[],
        ),
        ScanResult(
            site_name="Instagram",
            url="https://instagram.com/testuser",
            status=ScanStatus.FOUND,
            is_scrapable=True,
            tags=["Social"],
        ),
    ]


# ------------------------------------------------------------------
# AC1: ReportWriter class exists at correct path
# ------------------------------------------------------------------
class TestReportWriterExists:
    def test_import_succeeds(self):
        from Core.reporting.writer import ReportWriter  # noqa: F401

    def test_instantiation(self):
        writer = ReportWriter()
        assert writer is not None


# ------------------------------------------------------------------
# AC2+AC3: write() produces .txt file with correct format
# ------------------------------------------------------------------
class TestFlatFileWriter:
    def test_txt_written_with_found_urls(self, ctx, cfg, results, db):
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.return_value = db
            writer = ReportWriter()
            writer.write(ctx, cfg, results)

        txt = Path(ctx.report_path).read_text(encoding="utf-8")
        assert "[GitHub] https://github.com/testuser" in txt
        assert "[Instagram] https://instagram.com/testuser" in txt
        # NOT_FOUND should NOT appear in txt
        assert "Twitter" not in txt

    def test_txt_format_matches_expected(self, ctx, cfg, results, db):
        """AC3: Format must be [SiteName] URL\\n"""
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.return_value = db
            writer = ReportWriter()
            writer.write(ctx, cfg, results)

        lines = Path(ctx.report_path).read_text(encoding="utf-8").strip().splitlines()
        for line in lines:
            assert line.startswith("["), f"Line does not start with '[': {line!r}"
            assert "] " in line

    def test_json_output_written(self, ctx, cfg, results, db):
        """AC2: JSON output file exists and is valid JSON"""
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.return_value = db
            writer = ReportWriter()
            writer.write(ctx, cfg, results)

        json_path = Path(ctx.json_output_path)
        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) == 3  # all results (found + not-found)

    def test_json_names_written_found_only(self, ctx, cfg, results, db):
        """AC2: json_names_path contains only found site names"""
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.return_value = db
            writer = ReportWriter()
            writer.write(ctx, cfg, results)

        names_path = Path(ctx.json_names_path)
        assert names_path.exists()
        names = json.loads(names_path.read_text(encoding="utf-8"))
        assert "GitHub" in names
        assert "Instagram" in names
        assert "Twitter" not in names

    def test_no_results_produces_empty_txt(self, ctx, cfg):
        """Edge: no results → txt file not created (nothing to write)"""
        writer = ReportWriter()
        writer._write_txt(ctx, [])
        assert not Path(ctx.report_path).exists()


# ------------------------------------------------------------------
# AC4: SQLite inserts investigation + findings
# ------------------------------------------------------------------
class TestSQLiteWriter:
    def test_investigation_inserted(self, ctx, cfg, results, tmp_path):
        db = Database(db_path=tmp_path / "t.db")
        db.ensure_schema()
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.return_value = db
            writer = ReportWriter()
            inv_id = writer.write(ctx, cfg, results, total_sites=10)

        assert inv_id is not None
        row = db.execute(
            "SELECT subject, subject_type, total_sites, total_found FROM investigations WHERE id=?",
            (inv_id,)
        ).fetchone()
        assert row["subject"] == "testuser"
        assert row["subject_type"] == "USERNAME"
        assert row["total_sites"] == 10
        assert row["total_found"] == 2  # GitHub + Instagram

    def test_findings_inserted_for_all_results(self, ctx, cfg, results, tmp_path):
        db = Database(db_path=tmp_path / "t.db")
        db.ensure_schema()
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.return_value = db
            writer = ReportWriter()
            inv_id = writer.write(ctx, cfg, results, total_sites=10)

        rows = db.execute(
            "SELECT site_name, status FROM findings WHERE investigation_id=?", (inv_id,)
        ).fetchall()
        assert len(rows) == 3
        statuses = {r["site_name"]: r["status"] for r in rows}
        assert statuses["GitHub"] == "found"
        assert statuses["Twitter"] == "not_found"
        assert statuses["Instagram"] == "found"

    def test_tags_persisted_via_bridge(self, ctx, cfg, results, tmp_path):
        db = Database(db_path=tmp_path / "t.db")
        db.ensure_schema()
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.return_value = db
            writer = ReportWriter()
            inv_id = writer.write(ctx, cfg, results, total_sites=10)

        tag_names = db.execute(
            "SELECT DISTINCT t.name FROM tags t "
            "JOIN finding_tags ft ON ft.tag_id = t.id "
            "JOIN findings f ON f.id = ft.finding_id "
            "WHERE f.investigation_id = ?",
            (inv_id,)
        ).fetchall()
        names = {row[0] for row in tag_names}
        assert "Developer" in names
        assert "Code" in names
        assert "Social" in names


# ------------------------------------------------------------------
# AC5: SQLite failure does NOT block flat files
# ------------------------------------------------------------------
class TestGracefulDegradation:
    def test_sqlite_failure_still_writes_txt(self, ctx, cfg, results):
        """AC5: When SQLite explodes, txt/json are still written."""
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.side_effect = sqlite3.OperationalError("disk full")
            writer = ReportWriter()
            inv_id = writer.write(ctx, cfg, results, total_sites=5)

        # SQLite failed → inv_id is None
        assert inv_id is None
        # But txt file must exist with found URLs
        txt = Path(ctx.report_path).read_text(encoding="utf-8")
        assert "[GitHub]" in txt
        assert "[Instagram]" in txt

    def test_sqlite_failure_still_writes_json(self, ctx, cfg, results):
        """AC5: JSON output is written even when SQLite fails."""
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.side_effect = Exception("network error")
            writer = ReportWriter()
            writer.write(ctx, cfg, results, total_sites=5)

        json_path = Path(ctx.json_output_path)
        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert len(data) == 3

    def test_returns_none_on_sqlite_failure(self, ctx, cfg, results):
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.side_effect = sqlite3.Error("boom")
            writer = ReportWriter()
            result = writer.write(ctx, cfg, results)
        assert result is None


# ------------------------------------------------------------------
# write_json_and_sqlite() — pipeline integration method
# ------------------------------------------------------------------
class TestWriteJsonAndSqlite:
    def test_does_not_create_txt(self, ctx, cfg, results, tmp_path):
        """write_json_and_sqlite must NOT write txt (it's done inline)."""
        db = Database(db_path=tmp_path / "t.db")
        db.ensure_schema()
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.return_value = db
            writer = ReportWriter()
            writer.write_json_and_sqlite(ctx, cfg, results, total_sites=10)

        # txt should not exist — only json
        assert not Path(ctx.report_path).exists()
        assert Path(ctx.json_output_path).exists()

    def test_sqlite_inserted(self, ctx, cfg, results, tmp_path):
        db = Database(db_path=tmp_path / "t.db")
        db.ensure_schema()
        with patch("Core.reporting.writer.Database") as mock_db_cls:
            mock_db_cls.get_instance.return_value = db
            writer = ReportWriter()
            inv_id = writer.write_json_and_sqlite(ctx, cfg, results, total_sites=7)

        assert inv_id is not None
        row = db.execute("SELECT total_sites FROM investigations WHERE id=?", (inv_id,)).fetchone()
        assert row[0] == 7
