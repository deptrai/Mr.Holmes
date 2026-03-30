"""
tests/reporting/test_csv_export.py

Story 6.5 — Unit tests for CsvExporter and CLI integration.
"""
from __future__ import annotations

import csv
import io
import sqlite3
from unittest.mock import MagicMock

import pytest

from Core.reporting.csv_export import CsvExporter, _FIELDNAMES
from Core.cli.parser import parse_args, parse_investigation_ids, has_export_target


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _row(d: dict):
    """Build a sqlite3.Row-like mapping from a dict."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cols = ", ".join(f"? AS {k}" for k in d)
    row = conn.execute(f"SELECT {cols}", list(d.values())).fetchone()
    conn.close()
    return row


@pytest.fixture
def mock_db():
    """
    Minimal mock DB:
     - investigations id=1 subject="alice", id=2 subject="bob"
     - 2 findings per investigation (one found, one not_found)
     - no tags
    """
    conn = MagicMock()

    inv_rows = {
        1: _row({"id": 1, "subject": "alice", "subject_type": "USERNAME"}),
        2: _row({"id": 2, "subject": "bob",   "subject_type": "USERNAME"}),
    }
    all_inv = [_row({"id": 1}), _row({"id": 2})]

    finding_rows = {
        1: [
            _row({"id": 10, "site_name": "GitHub", "url": "https://github.com/alice",
                  "status": "found", "created_at": "2025-01-15T10:00:00"}),
            _row({"id": 11, "site_name": "LinkedIn", "url": None,
                  "status": "not_found", "created_at": "2025-01-15T10:00:01"}),
        ],
        2: [
            _row({"id": 20, "site_name": "Twitter", "url": "https://twitter.com/bob",
                  "status": "found", "created_at": "2025-01-16T10:00:00"}),
        ],
    }

    def execute_side(sql, params=()):
        cursor = MagicMock()
        sql_upper = sql.upper()

        if "FROM INVESTIGATIONS" in sql_upper and "WHERE ID" in sql_upper:
            inv_id = params[0]
            cursor.fetchone.return_value = inv_rows.get(inv_id)
        elif "FROM INVESTIGATIONS ORDER" in sql_upper:
            cursor.fetchall.return_value = all_inv
        elif "FROM FINDINGS" in sql_upper:
            inv_id = params[0]
            cursor.fetchall.return_value = finding_rows.get(inv_id, [])
        elif "FROM TAGS" in sql_upper:
            cursor.fetchall.return_value = []
        else:
            cursor.fetchone.return_value = None
            cursor.fetchall.return_value = []
        return cursor

    conn.execute.side_effect = execute_side
    db = MagicMock()
    db.connection = conn
    return db


# ---------------------------------------------------------------------------
# Tests — Task 1: CsvExporter output format
# ---------------------------------------------------------------------------

class TestCsvExporter:
    def test_export_to_string_returns_csv(self, mock_db):
        """AC2: export produces valid CSV text."""
        exporter = CsvExporter(db=mock_db)
        text = exporter.export_to_string([1])
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) == 2  # 2 findings for investigation 1

    def test_fieldnames_match_ac2(self, mock_db):
        """AC2: CSV columns match spec."""
        exporter = CsvExporter(db=mock_db)
        text = exporter.export_to_string([1])
        header = text.split("\r\n")[0]
        for col in ["site_name", "url", "status", "tags", "found_at"]:
            assert col in header

    def test_subject_in_output(self, mock_db):
        """AC2: subject columns populated correctly."""
        exporter = CsvExporter(db=mock_db)
        text = exporter.export_to_string([1])
        assert "alice" in text

    def test_multi_investigation_export(self, mock_db):
        """AC4: export([1, 2]) combines findings from both investigations."""
        exporter = CsvExporter(db=mock_db)
        text = exporter.export_to_string([1, 2])
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        subjects = {r["subject"] for r in rows}
        assert "alice" in subjects
        assert "bob" in subjects
        assert len(rows) == 3  # 2 + 1

    def test_all_investigations_export(self, mock_db):
        """AC4: export(None) fetches all investigations."""
        exporter = CsvExporter(db=mock_db)
        text = exporter.export_to_string(None)
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) == 3

    def test_missing_url_replaced_with_empty_string(self, mock_db):
        """AC2: None URL becomes empty string, not 'None'."""
        exporter = CsvExporter(db=mock_db)
        text = exporter.export_to_string([1])
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        linkedin_row = next(r for r in rows if r["site_name"] == "LinkedIn")
        assert linkedin_row["url"] == ""

    def test_raises_on_missing_investigation(self, mock_db):
        """AC1: ValueError if investigation ID not found."""
        exporter = CsvExporter(db=mock_db)
        with pytest.raises(ValueError, match="not found"):
            exporter.export_to_string([9999])

    def test_export_writes_file_to_disk(self, mock_db, tmp_path):
        """AC1: export() creates a file on disk."""
        exporter = CsvExporter(db=mock_db, output_dir=tmp_path)
        out = exporter.export([1])
        assert out.exists()
        assert out.suffix == ".csv"

    def test_export_file_has_bom(self, mock_db, tmp_path):
        """AC3: File starts with UTF-8 BOM (0xEF, 0xBB, 0xBF)."""
        exporter = CsvExporter(db=mock_db, output_dir=tmp_path)
        out = exporter.export([1])
        raw = out.read_bytes()
        assert raw[:3] == b"\xef\xbb\xbf", "File must start with UTF-8 BOM for Excel"

    def test_export_all_filename_label(self, mock_db, tmp_path):
        """AC4: 'all' investigations uses 'all' in filename."""
        exporter = CsvExporter(db=mock_db, output_dir=tmp_path)
        out = exporter.export(None)
        assert "all" in out.name

    def test_export_creates_output_dir(self, mock_db, tmp_path):
        """Output directory is created if missing."""
        out_dir = tmp_path / "nested" / "csv"
        exporter = CsvExporter(db=mock_db, output_dir=out_dir)
        exporter.export([1])
        assert out_dir.is_dir()


# ---------------------------------------------------------------------------
# Tests — Task 2: parse_investigation_ids helper
# ---------------------------------------------------------------------------

class TestParseInvestigationIds:
    def test_single_id(self):
        assert parse_investigation_ids("1") == [1]

    def test_multiple_ids(self):
        assert parse_investigation_ids("1,2,3") == [1, 2, 3]

    def test_all_keyword_lowercase(self):
        assert parse_investigation_ids("all") is None

    def test_all_keyword_uppercase(self):
        assert parse_investigation_ids("ALL") is None

    def test_invalid_raises(self):
        import argparse
        with pytest.raises(argparse.ArgumentTypeError):
            parse_investigation_ids("foo")

    def test_empty_raises(self):
        import argparse
        with pytest.raises(argparse.ArgumentTypeError):
            parse_investigation_ids("")


# ---------------------------------------------------------------------------
# Tests — Task 2: CLI parser
# ---------------------------------------------------------------------------

class TestCliParserCsv:
    def test_csv_export_flag_accepted(self):
        """AC1: --export csv is a valid choice."""
        args = parse_args(["--export", "csv", "--investigation", "1"])
        assert args.export == "csv"
        assert args.investigation == "1"
        assert has_export_target(args) is True

    def test_investigation_accepts_comma_list(self):
        """AC4: comma-separated IDs accepted as string."""
        args = parse_args(["--export", "csv", "--investigation", "1,2,3"])
        assert args.investigation == "1,2,3"

    def test_investigation_accepts_all(self):
        """AC4: 'all' accepted as string."""
        args = parse_args(["--export", "csv", "--investigation", "all"])
        assert args.investigation == "all"

    def test_pdf_still_works_with_single_id(self):
        """Backward compat: pdf + single id still valid."""
        args = parse_args(["--export", "pdf", "--investigation", "5"])
        assert args.export == "pdf"
        assert has_export_target(args) is True
