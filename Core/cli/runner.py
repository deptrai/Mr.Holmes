"""
Core/cli/runner.py

Batch execution logic for Mr.Holmes non-interactive mode.

Story 5.1 — Argparse CLI Interface
AC1: scan without interactive prompts
AC3: backward compatible (no args → interactive)
AC5: --output json|txt|csv
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from io import StringIO
from typing import Any, Dict, Optional

from Core.config.logging_config import get_logger

_logger = get_logger(__name__)


class ScanResult:
    """Lightweight container for batch scan result data."""

    def __init__(
        self,
        scan_type: str,
        target: str,
        found: int = 0,
        output_file: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.scan_type = scan_type
        self.target = target
        self.found = found
        self.output_file = output_file
        self.data = data or {}

    def as_dict(self) -> Dict[str, Any]:
        return {
            "scan_type": self.scan_type,
            "target": self.target,
            "found": self.found,
            "output_file": self.output_file,
            "data": self.data,
        }


class BatchRunner:
    """
    Runs a non-interactive OSINT scan based on parsed CLI arguments.

    Usage:
        runner = BatchRunner(args)
        runner.run()
    """

    # Default mode for headless / batch runs
    DEFAULT_MODE = "Desktop"

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self._result: Optional[ScanResult] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> int:
        """
        Execute the scan and return exit code.

        Returns:
            0 on success, 1 on failure.
        """
        try:
            self._result = self._dispatch()
            self._emit_output(self._result)
            return 0
        except Exception as e:
            _logger.error("Batch scan failed: %s", e, exc_info=True)
            print(f"[!] Scan failed: {e}", file=sys.stderr)
            return 1

    @property
    def result(self) -> Optional[ScanResult]:
        """The scan result (available after run() completes)."""
        return self._result

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def _dispatch(self) -> ScanResult:
        """Route args to the appropriate scan handler."""
        args = self.args

        if args.username:
            return self._run_username_scan(args.username)
        elif args.phone:
            return self._run_phone_scan(args.phone)
        elif args.email:
            return self._run_email_scan(args.email)
        elif args.website:
            return self._run_website_scan(args.website)
        else:
            # No target — should not reach here in normal flow
            raise ValueError("No scan target provided. Use --username, --phone, --email, or --website.")

    # ------------------------------------------------------------------
    # Scan handlers
    # ------------------------------------------------------------------

    def _run_username_scan(self, username: str) -> ScanResult:
        """Run username OSINT via ScanPipeline."""
        from Core.engine.scan_pipeline import ScanPipeline
        from Core.cli.rich_output import make_output_handler

        _logger.info("Starting username batch scan: %s", username)
        proxy_choice = 1 if self.args.proxy else 2
        
        # Mute UI output if user explicitly requested JSON or CSV scripts.
        # Otherwise, show the beautiful Rich UI during scan!
        output_handler = make_output_handler(force_silent=(self.args.output != "txt"))

        pipeline = ScanPipeline(
            username,
            self.DEFAULT_MODE,
            batch_mode=True,
            proxy_choice=proxy_choice,
            nsfw_enabled=self.args.nsfw,
            output_handler=output_handler,
        )

        try:
            pipeline.run()
        except Exception as e:
            _logger.error("Username scan pipeline error: %s", e, exc_info=True)
            raise

        report_path = f"GUI/Reports/Usernames/{pipeline.username}/{pipeline.username}.txt"
        return ScanResult(
            scan_type="username",
            target=pipeline.username,
            found=getattr(pipeline, "found", 0),
            output_file=report_path,
            data={"nsfw": self.args.nsfw, "proxy": self.args.proxy},
        )

    def _run_phone_scan(self, phone: str) -> ScanResult:
        """Run phone OSINT via legacy Searcher_phone."""
        from Core.Searcher_phone import Phone_search

        _logger.info("Starting phone batch scan: %s", phone)
        Phone_search.searcher(phone, self.DEFAULT_MODE)

        return ScanResult(
            scan_type="phone",
            target=phone,
            output_file=f"GUI/Reports/Phones/{phone}.txt",
        )

    def _run_email_scan(self, email: str) -> ScanResult:
        """Run email OSINT via legacy E_Mail."""
        from Core.E_Mail import Mail_search

        _logger.info("Starting email batch scan: %s", email)
        Mail_search.Search(email, self.DEFAULT_MODE)

        return ScanResult(
            scan_type="email",
            target=email,
        )

    def _run_website_scan(self, website: str) -> ScanResult:
        """Run website OSINT via legacy Searcher_website."""
        from Core.Searcher_website import Web

        _logger.info("Starting website batch scan: %s", website)
        Web.search(website, self.DEFAULT_MODE)

        return ScanResult(
            scan_type="website",
            target=website,
        )

    # ------------------------------------------------------------------
    # Output formatting (AC5)
    # ------------------------------------------------------------------

    def _emit_output(self, result: ScanResult) -> None:
        """Print result summary in the requested output format."""
        fmt = self.args.output

        if fmt == "json":
            print(json.dumps(result.as_dict(), indent=2))
        elif fmt == "csv":
            buf = StringIO()
            writer = csv.writer(buf)
            d = result.as_dict()
            writer.writerow(d.keys())
            writer.writerow(d.values())
            print(buf.getvalue(), end="")
        else:
            # txt (default)
            print(f"\n[+] Scan complete: {result.scan_type.upper()} → {result.target}")
            if result.found:
                print(f"[+] Found: {result.found} results")
            if result.output_file:
                print(f"[+] Report: {result.output_file}")
