"""
Core/reporting/pdf_export.py

Story 6.4 — PDF Export via Jinja2
AC2: Template-based pipeline: Jinja2 → HTML → PDF (weasyprint / pdfkit fallback)
AC3: Report includes: header, summary, findings table, tags cloud
AC4: Branding: Mr.Holmes logo, date, investigation metadata

Usage:
    exporter = PdfExporter()
    out_path = exporter.export(investigation_id=1)
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Template directory is sibling to this file
_TEMPLATE_DIR = Path(__file__).parent / "templates"
_TEMPLATE_NAME = "report.html.j2"

# Default output directory
_DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "GUI" / "Reports" / "PDF"


def _get_jinja_env():
    """
    Lazily build a Jinja2 Environment — import deferred so the module loads
    without Jinja2 installed (graceful ImportError at export time).
    """
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    return Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )


def _render_pdf_weasyprint(html: str, out_path: Path) -> None:
    """Render HTML → PDF via weasyprint."""
    from weasyprint import HTML  # type: ignore

    HTML(string=html).write_pdf(str(out_path))


def _render_pdf_pdfkit(html: str, out_path: Path) -> None:
    """Fallback: render HTML → PDF via pdfkit (requires wkhtmltopdf binary)."""
    import pdfkit  # type: ignore

    pdfkit.from_string(html, str(out_path))


class PdfExporter:
    """
    Exports an investigation from SQLite to a PDF report.

    AC2: Uses Jinja2 template → HTML → PDF (weasyprint preferred, pdfkit fallback)
    AC3: Includes header, summary, findings table, tags cloud
    AC4: Branding with date and investigation metadata
    """

    def __init__(
        self,
        db: Any | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        """
        Args:
            db:         Database instance (defaults to Database.get_instance()).
                        Accepts any object with a `.connection` attribute that
                        returns a sqlite3.Connection.
            output_dir: Directory where PDFs are saved. Defaults to
                        GUI/Reports/PDF/.
        """
        self._db = db
        self._output_dir = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export(self, investigation_id: int) -> Path:
        """
        Generate a PDF report for the given investigation.

        Returns:
            Path to the generated PDF file.

        Raises:
            ValueError:        If investigation_id not found in DB.
            ImportError:       If neither weasyprint nor pdfkit is installed.
            RuntimeError:      If PDF rendering fails.
            OSError:           If the output directory cannot be created.
        """
        db = self._resolve_db()
        inv = self._fetch_investigation(db.connection, investigation_id)
        all_findings = self._fetch_findings(db.connection, investigation_id)
        found_findings, all_tags = self._partition_findings(db.connection, all_findings)

        html = self._render_html(inv, all_findings, found_findings, all_tags)
        out_path = self._pdf_path(inv)

        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._write_pdf(html, out_path)

        logger.info("PDF exported: %s", out_path)
        return out_path

    def render_html(self, investigation_id: int) -> str:
        """
        Return the rendered HTML string (useful for testing / preview).
        Does NOT write to disk.
        """
        db = self._resolve_db()
        inv = self._fetch_investigation(db.connection, investigation_id)
        all_findings = self._fetch_findings(db.connection, investigation_id)
        found_findings, all_tags = self._partition_findings(db.connection, all_findings)
        return self._render_html(inv, all_findings, found_findings, all_tags)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_db(self) -> Any:
        if self._db is not None:
            return self._db
        from Core.reporting.database import Database  # deferred import

        return Database.get_instance()

    def _fetch_investigation(
        self, conn: sqlite3.Connection, investigation_id: int
    ) -> dict:
        """
        Fetch one investigation row. Raises ValueError if not found.
        AC2 / AC4 data source.
        """
        # Cast created_at to TEXT to avoid sqlite3 PARSE_DECLTYPES ValueError
        # on ISO 8601 T-separator timestamps (e.g. "2025-01-15T10:30:00")
        row = conn.execute(
            "SELECT id, subject, subject_type, "
            "CAST(created_at AS TEXT) AS created_at, proxy_used, "
            "total_sites, total_found "
            "FROM investigations WHERE id = ?",
            (investigation_id,),
        ).fetchone()

        if row is None:
            raise ValueError(f"Investigation id={investigation_id} not found in database.")

        return dict(row)

    def _fetch_findings(
        self, conn: sqlite3.Connection, investigation_id: int
    ) -> list[dict]:
        """Fetch all findings for the investigation, ordered by site_name."""
        rows = conn.execute(
            "SELECT id, site_name, url, status, error_type, "
            "CAST(created_at AS TEXT) AS created_at "
            "FROM findings "
            "WHERE investigation_id = ? "
            "ORDER BY site_name",
            (investigation_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def _partition_findings(
        self, conn: sqlite3.Connection, all_findings: list[dict]
    ) -> tuple[list[dict], list[str]]:
        """
        Split findings into found-only list and collect unique tags.
        AC3: findings table + tags cloud.
        """
        found = []
        tags_seen: set[str] = set()

        for f in all_findings:
            if f.get("status") == "found":
                # Fetch tags for this finding
                tag_rows = conn.execute(
                    "SELECT t.name FROM tags t "
                    "JOIN finding_tags ft ON ft.tag_id = t.id "
                    "WHERE ft.finding_id = ? ORDER BY t.name",
                    (f["id"],),
                ).fetchall()
                f["tags"] = [r["name"] for r in tag_rows]
                tags_seen.update(f["tags"])
                found.append(f)

        return found, sorted(tags_seen)

    def _render_html(
        self,
        investigation: dict,
        all_findings: list[dict],
        found_findings: list[dict],
        all_tags: list[str],
    ) -> str:
        """Render the Jinja2 template to an HTML string."""
        env = _get_jinja_env()
        template = env.get_template(_TEMPLATE_NAME)
        return template.render(
            investigation=investigation,
            all_findings=all_findings,
            found_findings=found_findings,
            all_tags=all_tags,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

    def _pdf_path(self, investigation: dict) -> Path:
        """Build the output PDF file path."""
        import re
        # Strip filesystem-unsafe characters (Windows + Unix)
        subject = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', investigation.get("subject", "unknown"))
        inv_id = investigation.get("id", 0)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self._output_dir / f"report_{subject}_{inv_id}_{ts}.pdf"

    def _write_pdf(self, html: str, out_path: Path) -> None:
        """
        Render HTML → PDF. Tries weasyprint first, falls back to pdfkit.
        AC2: template → HTML → PDF
        """
        # Try weasyprint (preferred — no system binary required)
        try:
            _render_pdf_weasyprint(html, out_path)
            return
        except ImportError:
            logger.debug("weasyprint not available, trying pdfkit…")
        except Exception as exc:
            logger.warning("weasyprint failed (%s), trying pdfkit…", exc)

        # Fallback: pdfkit (already listed in requirements.txt)
        try:
            _render_pdf_pdfkit(html, out_path)
            return
        except ImportError:
            raise ImportError(
                "PDF export requires either weasyprint or pdfkit.\n"
                "Install with: pip install weasyprint\n"
                "  or:         pip install pdfkit  (also needs wkhtmltopdf)"
            )
        except Exception as exc:
            raise RuntimeError(f"PDF rendering failed: {exc}") from exc
