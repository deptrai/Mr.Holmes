"""
Core/reporting/csv_export.py

Story 6.5 — CSV Export
AC1: `python3 MrHolmes.py --export csv --investigation <id>`
AC2: Columns: site_name, url, status, tags, found_at
AC3: UTF-8 with BOM (utf-8-sig) for Excel compatibility
AC4: Multi-investigation export — accepts list of IDs or None (all)

Usage:
    # Single investigation
    exporter = CsvExporter()
    path = exporter.export([1])

    # Multiple investigations
    path = exporter.export([1, 2, 3])

    # All investigations
    path = exporter.export(None)
"""
from __future__ import annotations

import csv
import io
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

# Default output directory — sibling to PDF/
_DEFAULT_OUTPUT_DIR = (
    Path(__file__).parent.parent.parent / "GUI" / "Reports" / "CSV"
)

# CSV column headers (AC2)
_FIELDNAMES = ["investigation_id", "subject", "subject_type", "site_name", "url",
               "status", "tags", "found_at"]


class CsvExporter:
    """
    Exports investigation findings from SQLite to CSV.

    AC2: Columns: site_name, url, status, tags, found_at
    AC3: UTF-8 with BOM encoding for Excel compatibility
    AC4: Multi-investigation export (list of IDs or None for all)
    """

    def __init__(
        self,
        db: Any | None = None,
        output_dir: str | Path | None = None,
    ) -> None:
        """
        Args:
            db:         Database instance (defaults to Database.get_instance()).
            output_dir: Directory where CSV files are saved (default: GUI/Reports/CSV/).
        """
        self._db = db
        self._output_dir = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def export(self, investigation_ids: Optional[List[int]]) -> Path:
        """
        Export findings to a UTF-8 BOM CSV file.

        Args:
            investigation_ids: List of investigation IDs to export.
                               Pass None to export ALL investigations.

        Returns:
            Path to the generated CSV file.

        Raises:
            ValueError:  If any specified ID does not exist in the DB.
            OSError:     If the output directory cannot be created.
        """
        db = self._resolve_db()
        conn = db.connection

        if investigation_ids is None:
            # AC4: all investigations
            rows = self._fetch_all(conn)
        else:
            rows = self._fetch_many(conn, investigation_ids)

        out_path = self._csv_path(investigation_ids)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._write_csv(rows, out_path)

        logger.info("CSV exported: %s (%d rows)", out_path, len(rows))
        return out_path

    def export_to_string(self, investigation_ids: Optional[List[int]]) -> str:
        """
        Export to an in-memory string (useful for testing without disk I/O).

        Returns:
            CSV text (UTF-8, no BOM — BOM only written to disk files).
        """
        db = self._resolve_db()
        conn = db.connection

        if investigation_ids is None:
            rows = self._fetch_all(conn)
        else:
            rows = self._fetch_many(conn, investigation_ids)

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=_FIELDNAMES, lineterminator="\r\n")
        writer.writeheader()
        writer.writerows(rows)
        return buf.getvalue()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _resolve_db(self) -> Any:
        if self._db is not None:
            return self._db
        from Core.reporting.database import Database  # deferred import
        return Database.get_instance()

    def _fetch_many(
        self, conn: sqlite3.Connection, investigation_ids: List[int]
    ) -> list[dict]:
        """Fetch findings for a specific list of investigation IDs."""
        rows: list[dict] = []
        for inv_id in investigation_ids:
            inv_rows = self._fetch_for_investigation(conn, inv_id)
            rows.extend(inv_rows)
        return rows

    def _fetch_all(self, conn: sqlite3.Connection) -> list[dict]:
        """AC4: Fetch findings across ALL investigations."""
        inv_ids_raw = conn.execute(
            "SELECT id FROM investigations ORDER BY created_at"
        ).fetchall()
        inv_ids = [r[0] for r in inv_ids_raw]
        return self._fetch_many(conn, inv_ids)

    def _fetch_for_investigation(
        self, conn: sqlite3.Connection, investigation_id: int
    ) -> list[dict]:
        """
        Fetch one investigation + its findings, return as flat CSV rows.
        AC2: site_name, url, status, tags, found_at
        """
        # Fetch investigation header (with CAST to avoid PARSE_DECLTYPES ValueError)
        inv = conn.execute(
            "SELECT id, subject, subject_type "
            "FROM investigations WHERE id = ?",
            (investigation_id,),
        ).fetchone()

        if inv is None:
            raise ValueError(
                f"Investigation id={investigation_id} not found in database."
            )

        inv_dict = dict(inv)
        subject = inv_dict["subject"]
        subject_type = inv_dict["subject_type"]

        # Fetch findings (CAST timestamps to TEXT — same fix as Story 6.4)
        # AC2: Optimized to fetch tags in a single query via LEFT JOIN and GROUP_CONCAT
        findings = conn.execute(
            "SELECT f.id, f.site_name, f.url, f.status, "
            "CAST(f.created_at AS TEXT) AS created_at, "
            "GROUP_CONCAT(t.name, ';') AS tags "
            "FROM findings f "
            "LEFT JOIN finding_tags ft ON f.id = ft.finding_id "
            "LEFT JOIN tags t ON ft.tag_id = t.id "
            "WHERE f.investigation_id = ? "
            "GROUP BY f.id "
            "ORDER BY f.site_name",
            (investigation_id,),
        ).fetchall()

        rows: list[dict] = []
        for f in findings:
            f_dict = dict(f)
            rows.append({
                "investigation_id": investigation_id,
                "subject":          subject,
                "subject_type":     subject_type,
                "site_name":        f_dict.get("site_name", ""),
                "url":              f_dict.get("url") or "",
                "status":           f_dict.get("status") or "",
                "tags":             f_dict.get("tags") or "",
                "found_at":         f_dict.get("created_at") or "",
            })

        return rows

    def _csv_path(self, investigation_ids: Optional[List[int]]) -> Path:
        """Build an output CSV filename."""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        if investigation_ids is None:
            label = "all"
        elif len(investigation_ids) == 1:
            label = str(investigation_ids[0])
        else:
            # Sanitize to safe filename fragment
            label = "_".join(str(i) for i in investigation_ids[:5])
            if len(investigation_ids) > 5:
                label += f"_and_{len(investigation_ids) - 5}_more"
        return self._output_dir / f"findings_{label}_{ts}.csv"

    def _write_csv(self, rows: list[dict], out_path: Path) -> None:
        """
        Write rows to CSV with UTF-8 BOM encoding (AC3 — Excel compatibility).
        """
        # utf-8-sig writes the BOM automatically
        with open(out_path, "w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_FIELDNAMES, lineterminator="\r\n")
            writer.writeheader()
            writer.writerows(rows)
