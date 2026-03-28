"""
Core/reporting/writer.py

Story 6.2 — Dual-Write ReportWriter.
Writes OSINT results simultaneously to:
  - Flat files (.txt + .json)  — backward compat for PHP GUI
  - SQLite via Database singleton — for advanced querying

AC5: Atomic degradation — SQLite failure never blocks flat file output.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Sequence

from Core.models.scan_context import ScanContext, ScanConfig
from Core.models.scan_result import ScanResult, ScanStatus
from Core.reporting.database import Database

logger = logging.getLogger(__name__)


class ReportWriter:
    """
    Dual-write strategy for OSINT results.

    AC1: Class at Core/reporting/writer.py
    AC2: write(ctx, cfg, results) → .txt + .json + SQLite
    AC3: Flat file format identical with current output
    AC4: SQLite insert investigation + findings records
    AC5: SQLite failure does NOT block flat files
    """

    def write(
        self,
        ctx: ScanContext,
        cfg: ScanConfig,
        results: Sequence[ScanResult],
        total_sites: int = 0,
    ) -> int | None:
        """
        Persist scan results to both flat files and SQLite.

        Returns the SQLite investigation_id, or None if SQLite failed/skipped.
        Use this when NO flat-file writing has happened yet (batch mode, tests).

        For ScanPipeline where txt is already written inline, use write_json_and_sqlite().
        """
        # F5: Precompute found count once
        total_found = sum(1 for r in results if r.status == ScanStatus.FOUND)

        # AC3: Flat file writes — always first
        self._write_txt(ctx, results)
        self._write_json(ctx, results)

        # AC4+AC5: SQLite write — failure is non-fatal
        return self._write_sqlite(
            ctx, cfg, results, total_sites=total_sites, total_found=total_found
        )

    def write_json_and_sqlite(
        self,
        ctx: ScanContext,
        cfg: ScanConfig,
        results: Sequence[ScanResult],
        total_sites: int = 0,
    ) -> int | None:
        """
        Write JSON + SQLite only (txt already written inline by ScanPipeline._on_progress).
        AC3: txt format integrity is preserved because txt was written at exact point of discovery.
        AC5: SQLite failure is non-fatal.
        """
        self._write_json(ctx, results)

        total_found = sum(1 for r in results if r.status == ScanStatus.FOUND)
        return self._write_sqlite(
            ctx, cfg, results, total_sites=total_sites, total_found=total_found
        )


    # ------------------------------------------------------------------
    # Internal: Flat file writers (AC3)
    # ------------------------------------------------------------------

    def _write_txt(self, ctx: ScanContext, results: Sequence[ScanResult]) -> None:
        """
        Append found results to the .txt report in existing format:
            [SiteName] https://...
        """
        report_path = Path(ctx.report_path)
        try:
            if not report_path.parent.exists():
                report_path.parent.mkdir(parents=True, exist_ok=True)

            found_results = [r for r in results if r.status == ScanStatus.FOUND]
            if not found_results:
                return

            with open(report_path, "a", encoding="utf-8") as f:
                for result in found_results:
                    f.write("[{}] {}\n".format(result.site_name, result.url))
        except OSError as e:
            logger.error("Failed to write to TXT report %s: %s", report_path, e)

    def _write_json(self, ctx: ScanContext, results: Sequence[ScanResult]) -> None:
        """
        Write all results to .json file matching existing format.
        Also write found-only names to json_names_path.
        """
        if ctx.json_output_path:
            json_path = Path(ctx.json_output_path)
            try:
                if not json_path.parent.exists():
                    json_path.parent.mkdir(parents=True, exist_ok=True)

                payload = [r.to_dict() for r in results]
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)
            except OSError as e:
                logger.error("Failed to write JSON output %s: %s", json_path, e)

        if ctx.json_names_path:
            names_path = Path(ctx.json_names_path)
            try:
                if not names_path.parent.exists():
                    names_path.parent.mkdir(parents=True, exist_ok=True)

                found_names = [r.site_name for r in results if r.status == ScanStatus.FOUND]
                with open(names_path, "w", encoding="utf-8") as f:
                    json.dump(found_names, f, ensure_ascii=False, indent=2)
            except OSError as e:
                logger.error("Failed to write names JSON %s: %s", names_path, e)

    # ------------------------------------------------------------------
    # Internal: SQLite writer (AC4, AC5)
    # ------------------------------------------------------------------

    def _write_sqlite(
        self,
        ctx: ScanContext,
        cfg: ScanConfig,
        results: Sequence[ScanResult],
        *,
        total_sites: int,
        total_found: int,
    ) -> int | None:
        """
        Insert investigation + findings into SQLite.
        Returns investigation_id on success, None on any failure (AC5).
        """
        try:
            db = Database.get_instance()

            # F2: Use cursor.lastrowid for thread-safety
            cur = db.execute(
                "INSERT INTO investigations "
                "(subject, subject_type, created_at, proxy_used, total_sites, total_found) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    ctx.target,
                    ctx.subject_type,
                    datetime.now().isoformat(),
                    cfg.proxy_enabled,
                    total_sites,
                    total_found,
                ),
            )
            investigation_id: int = cur.lastrowid

            # Insert findings + tags in bulk
            for result in results:
                fcur = db.execute(
                    "INSERT INTO findings "
                    "(investigation_id, site_name, url, status, is_scrapable, scraped, error_type) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        investigation_id,
                        result.site_name,
                        result.url,
                        result.status.value,
                        result.is_scrapable,
                        False,
                        result.error_message,
                    ),
                )
                finding_id: int = fcur.lastrowid

                for tag_name in result.tags:
                    self._upsert_tag(db, finding_id, tag_name)

            db.commit()
            logger.info(
                "SQLite write OK: investigation_id=%d, %d findings", investigation_id, len(results)
            )
            return investigation_id

        except Exception as exc:
            # F1+F3: rollback partial writes, then log (AC5: non-fatal)
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning("SQLite write failed (flat files still written): %s", exc)
            return None

    def _upsert_tag(self, db, finding_id: int, tag_name: str) -> None:
        """Insert tag if not exists, then create finding_tag link."""
        # Upsert tag (INSERT OR IGNORE)
        db.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name,))
        row = db.execute("SELECT id FROM tags WHERE name = ?", (tag_name,)).fetchone()
        if row:
            tag_id = row[0]
            db.execute(
                "INSERT OR IGNORE INTO finding_tags (finding_id, tag_id) VALUES (?, ?)",
                (finding_id, tag_id),
            )
