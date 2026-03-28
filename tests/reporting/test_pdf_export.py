"""
tests/reporting/test_pdf_export.py

Story 6.4 — Unit tests for PdfExporter and CLI integration.
All tests use mocked DB and PDF renderers to avoid system dependencies.
"""
from __future__ import annotations

import sqlite3
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from Core.reporting.pdf_export import PdfExporter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_row(d: dict):
    """Build a sqlite3.Row-like mapping from a dict."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    # Build a SELECT that yields the dict as a Row
    cols = ", ".join(f"? AS {k}" for k in d)
    row = conn.execute(f"SELECT {cols}", list(d.values())).fetchone()
    conn.close()
    return row


@pytest.fixture
def investigation_row():
    return _make_row({
        "id": 42,
        "subject": "testuser",
        "subject_type": "username",
        "created_at": "2025-01-15 10:30:00",
        "proxy_used": 0,
        "total_sites": 100,
        "total_found": 23,
    })


@pytest.fixture
def finding_rows():
    return [
        _make_row({"id": 1, "site_name": "GitHub", "url": "https://github.com/testuser", "status": "found", "error_type": None, "created_at": "2025-01-15 10:31:00"}),
        _make_row({"id": 2, "site_name": "Twitter", "url": "https://twitter.com/testuser", "status": "found", "error_type": None, "created_at": "2025-01-15 10:31:01"}),
        _make_row({"id": 3, "site_name": "LinkedIn", "url": None, "status": "not_found", "error_type": "timeout", "created_at": "2025-01-15 10:31:02"}),
    ]


@pytest.fixture
def mock_db(investigation_row, finding_rows):
    """Create a mock DB that returns fake investigation + findings."""
    conn = MagicMock()

    def execute_side_effect(sql, params=()):
        cursor = MagicMock()
        sql_upper = sql.upper()
        if "FROM INVESTIGATIONS" in sql_upper and "WHERE ID" in sql_upper:
            cursor.fetchone.return_value = investigation_row
        elif "FROM FINDINGS" in sql_upper:
            cursor.fetchall.return_value = finding_rows
        elif "FROM TAGS" in sql_upper:
            # Return empty tags for simplicity
            cursor.fetchall.return_value = []
        else:
            cursor.fetchone.return_value = None
            cursor.fetchall.return_value = []
        return cursor

    conn.execute.side_effect = execute_side_effect
    db = MagicMock()
    db.connection = conn
    return db


# ---------------------------------------------------------------------------
# Tests — Task 1: Template rendering
# ---------------------------------------------------------------------------

class TestHtmlRendering:
    def test_render_html_contains_subject(self, mock_db):
        """AC3: rendered HTML includes the subject name."""
        exporter = PdfExporter(db=mock_db)
        html = exporter.render_html(42)
        assert "testuser" in html

    def test_render_html_contains_summary_stats(self, mock_db):
        """AC3: summary shows total found / total sites."""
        exporter = PdfExporter(db=mock_db)
        html = exporter.render_html(42)
        assert "23" in html   # total_found
        assert "100" in html  # total_sites

    def test_render_html_contains_branding(self, mock_db):
        """AC4: HTML includes Mr.Holmes branding."""
        exporter = PdfExporter(db=mock_db)
        html = exporter.render_html(42)
        assert "MR.HOLMES" in html.upper()

    def test_render_html_contains_investigation_metadata(self, mock_db):
        """AC4: investigation date and ID present."""
        exporter = PdfExporter(db=mock_db)
        html = exporter.render_html(42)
        assert "42" in html              # ID
        assert "2025-01-15" in html      # date slice

    def test_render_html_findings_table_contains_found_sites(self, mock_db):
        """AC3: findings table lists 'found' sites."""
        exporter = PdfExporter(db=mock_db)
        html = exporter.render_html(42)
        assert "GitHub" in html
        assert "Twitter" in html

    def test_render_html_not_found_sites_in_all_section(self, mock_db):
        """AC3: all-sites section shows not_found entries too."""
        exporter = PdfExporter(db=mock_db)
        html = exporter.render_html(42)
        assert "LinkedIn" in html


# ---------------------------------------------------------------------------
# Tests — Task 2: PdfExporter behaviour
# ---------------------------------------------------------------------------

class TestPdfExporter:
    def test_export_raises_value_error_for_missing_investigation(self, tmp_path):
        """AC2: export raises ValueError when investigation_id not found."""
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        # No rows in DB
        db = MagicMock()
        db.connection.execute.return_value.fetchone.return_value = None

        exporter = PdfExporter(db=db, output_dir=tmp_path)
        with pytest.raises(ValueError, match="not found"):
            exporter.export(9999)

    def test_export_uses_weasyprint_when_available(self, mock_db, tmp_path):
        """AC2: weasyprint is tried first."""
        exporter = PdfExporter(db=mock_db, output_dir=tmp_path)
        mock_write = MagicMock()
        with patch("Core.reporting.pdf_export._render_pdf_weasyprint", mock_write):
            out = exporter.export(42)
        mock_write.assert_called_once()
        assert out.parent == tmp_path
        assert out.suffix == ".pdf"
        assert "testuser" in out.name

    def test_export_falls_back_to_pdfkit_when_weasyprint_missing(self, mock_db, tmp_path):
        """AC2: pdfkit used when weasyprint not installed."""
        exporter = PdfExporter(db=mock_db, output_dir=tmp_path)
        mock_pdfkit = MagicMock()
        with (
            patch("Core.reporting.pdf_export._render_pdf_weasyprint", side_effect=ImportError),
            patch("Core.reporting.pdf_export._render_pdf_pdfkit", mock_pdfkit),
        ):
            out = exporter.export(42)
        mock_pdfkit.assert_called_once()

    def test_export_raises_import_error_when_both_missing(self, mock_db, tmp_path):
        """AC2: ImportError raised if neither renderer available."""
        exporter = PdfExporter(db=mock_db, output_dir=tmp_path)
        # mock _render_html so we bypass jinja2, then test writer raises ImportError
        mock_html = "<html>test</html>"
        with (
            patch.object(exporter, "_render_html", return_value=mock_html),
            patch("Core.reporting.pdf_export._render_pdf_weasyprint", side_effect=ImportError),
            patch("Core.reporting.pdf_export._render_pdf_pdfkit", side_effect=ImportError),
            pytest.raises(ImportError, match="weasyprint"),
        ):
            exporter.export(42)

    def test_export_creates_output_dir(self, mock_db, tmp_path):
        """Output directory is created if it doesn't exist."""
        out_dir = tmp_path / "nested" / "reports"
        exporter = PdfExporter(db=mock_db, output_dir=out_dir)
        with patch("Core.reporting.pdf_export._render_pdf_weasyprint"):
            exporter.export(42)
        assert out_dir.is_dir()

    def test_pdf_filename_contains_subject_and_id(self, mock_db, tmp_path):
        """PDF filename includes subject name and investigation ID."""
        exporter = PdfExporter(db=mock_db, output_dir=tmp_path)
        with patch("Core.reporting.pdf_export._render_pdf_weasyprint"):
            out = exporter.export(42)
        assert "testuser" in out.name
        assert "42" in out.name


# ---------------------------------------------------------------------------
# Tests — Task 3: CLI args
# ---------------------------------------------------------------------------

class TestCliParser:
    def test_export_and_investigation_flags_parsed(self):
        """AC1: --export pdf --investigation 7 produces correct Namespace."""
        from Core.cli.parser import parse_args, has_export_target

        args = parse_args(["--export", "pdf", "--investigation", "7"])
        assert args.export == "pdf"
        assert args.investigation == 7
        assert has_export_target(args) is True

    def test_has_export_target_false_when_no_export(self):
        from Core.cli.parser import parse_args, has_export_target

        args = parse_args(["--username", "foo"])
        assert has_export_target(args) is False

    def test_has_export_target_false_when_investigation_missing(self):
        from Core.cli.parser import parse_args, has_export_target

        args = parse_args(["--export", "pdf"])
        assert has_export_target(args) is False

    def test_investigation_must_be_integer(self):
        """--investigation requires an integer."""
        from Core.cli.parser import build_parser
        import argparse

        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--export", "pdf", "--investigation", "not_an_int"])
