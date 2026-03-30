"""
Core/engine/result_collector.py

ScanResultCollector — centralized collection pattern cho concurrent scan results.

Thay thế 5 shared mutable lists trong legacy Searcher:
    - successfull       → found_urls property
    - successfullName   → found_names property
    - ScraperSites      → scraper_sites property
    - Tags              → all_tags property (accumulated from ScanResult.tags)
    - MostTags          → most_tags property (high-frequency + unique-interest tags)

Story 2.3 — ScanResult Collection Pattern, Epic 2.
Dependencies: Story 1.1 (ScanResult), Story 1.2 (tag processing logic)
"""
from __future__ import annotations

import json
import threading
from typing import Optional

from Core.models.scan_result import ScanResult, ScanStatus
from Core.Support.Requests_Search import UNIQUE_TAGS
from Core.plugins.base import PluginResult


class ScanResultCollector:
    """
    Thread-safe accumulator for ScanResult objects from asyncio.gather().

    AC4 — Thread-safe: uses threading.Lock for all mutations.
    AC3 — Replaces 5 shared mutable lists with derived read-only properties.

    Usage:
        collector = ScanResultCollector(subject="USERNAME")
        collector.add(scan_result)                   # from gather() results
        collector.add_many(list_of_scan_results)     # batch add

        urls   = collector.found_urls      # replaces successfull[]
        names  = collector.found_names     # replaces successfullName[]
        tags   = collector.most_tags       # replaces MostTags[]
    """

    def __init__(self, subject: str = "USERNAME") -> None:
        """
        Args:
            subject: subject type string — e.g. "USERNAME", "PHONE-NUMBER".
                     PHONE-NUMBER skips tag accumulation (matches legacy behavior).
        """
        self.subject = subject
        self._results: list[ScanResult] = []
        self._all_tags: list[str] = []
        self._most_tags: list[str] = []
        self._lock = threading.Lock()  # AC4 — thread-safe per AC4

    # ------------------------------------------------------------------
    # Mutation API
    # ------------------------------------------------------------------

    def add(self, result: ScanResult) -> None:
        """
        AC1 — Add a single ScanResult, updating tag accumulators.
        Thread-safe.
        """
        with self._lock:
            self._results.append(result)
            self._process_tags(result.tags)

    def add_plugin_result(self, result: PluginResult) -> None:
        """
        Story 7.1 — Maps and adds a PluginResult as an internal ScanResult.
        Thread-safe.
        """
        mapped = ScanResult(
            url="",
            site_name=f"Plugin: {result.plugin_name}",
            status=ScanStatus.FOUND if result.is_success else ScanStatus.NOT_FOUND,
            tags=[],
            is_scrapable=False,
            plugin_data=result.data,
        )
        self.add(mapped)

    def add_many(self, results: list[ScanResult]) -> None:
        """
        Batch-add a list of ScanResult objects (e.g. from asyncio.gather() output).
        Thread-safe (single lock acquisition for all items).
        """
        with self._lock:
            for r in results:
                self._results.append(r)
                self._process_tags(r.tags)

    # ------------------------------------------------------------------
    # AC2 — Derived read-only properties
    # ------------------------------------------------------------------

    @property
    def found_urls(self) -> list[str]:
        """Replaces `successfull` — URLs of FOUND sites."""
        with self._lock:
            return [r.url for r in self._results if r.status == ScanStatus.FOUND]

    @property
    def found_names(self) -> list[str]:
        """Replaces `successfullName` — site names of FOUND sites."""
        with self._lock:
            return [r.site_name for r in self._results if r.status == ScanStatus.FOUND]

    @property
    def scraper_sites(self) -> list[str]:
        """Replaces `ScraperSites` — site names of scrapable FOUND sites."""
        with self._lock:
            return [
                r.site_name
                for r in self._results
                if r.status == ScanStatus.FOUND and r.is_scrapable
            ]

    @property
    def all_tags(self) -> list[str]:
        """Replaces `Tags` — all accumulated unique tags."""
        with self._lock:
            return list(self._all_tags)

    @property
    def most_tags(self) -> list[str]:
        """Replaces `MostTags` — high-frequency and unique-interest tags."""
        with self._lock:
            return list(self._most_tags)

    @property
    def found_count(self) -> int:
        """Number of FOUND results."""
        with self._lock:
            return sum(1 for r in self._results if r.status == ScanStatus.FOUND)

    @property
    def total_count(self) -> int:
        """Total number of results accumulated."""
        with self._lock:
            return len(self._results)

    @property
    def blocked_count(self) -> int:
        """AC5: Số BLOCKED results (HTTP 403)."""
        with self._lock:
            return sum(1 for r in self._results if r.status == ScanStatus.BLOCKED)

    @property
    def rate_limited_count(self) -> int:
        """AC5: Số RATE_LIMITED results (HTTP 429)."""
        with self._lock:
            return sum(1 for r in self._results if r.status == ScanStatus.RATE_LIMITED)

    @property
    def captcha_count(self) -> int:
        """AC5: Số CAPTCHA results (challenge detected in body)."""
        with self._lock:
            return sum(1 for r in self._results if r.status == ScanStatus.CAPTCHA)

    def block_summary(self) -> str:
        """
        AC5: Summary report về blocking events sau scan.

        Thread-safe: computes tất cả counts trong 1 lock acquisition để
        đảm bảo consistency (tránh race condition giữa 3 lần acquire riêng).

        Returns:
            Formatted string: "Blocked: X | Rate-Limited: Y | CAPTCHA: Z"
        """
        with self._lock:
            blocked = sum(1 for r in self._results if r.status == ScanStatus.BLOCKED)
            rate_limited = sum(1 for r in self._results if r.status == ScanStatus.RATE_LIMITED)
            captcha = sum(1 for r in self._results if r.status == ScanStatus.CAPTCHA)
        return f"Blocked: {blocked} | Rate-Limited: {rate_limited} | CAPTCHA: {captcha}"

    @property
    def all_results(self) -> list[ScanResult]:
        """Return a copy of all accumulated ScanResult objects."""
        with self._lock:
            return list(self._results)

    # ------------------------------------------------------------------
    # AC3 — Export methods (AC5: compatible with existing report format)
    # ------------------------------------------------------------------

    def to_report_text(self) -> str:
        """
        AC5 — Export found URLs as plain text, matching legacy report line format.

        Legacy format: one URL per line, same as `successfull` iteration.
        """
        lines = []
        with self._lock:
            for r in self._results:
                if r.status == ScanStatus.FOUND:
                    lines.append(r.url)
        return "\n".join(lines)

    def to_mh(self) -> str:
        """
        AC5 — Export in .mh format (same as .txt — distinguished by extension only).

        Legacy .mh files contain the same content as .txt report files.
        """
        return self.to_report_text()

    def to_json(self) -> str:
        """
        AC5 — Export all results as JSON array.

        Each item uses ScanResult.to_dict() for field structure compatible
        with existing GUI/Reports JSON consumers.
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def to_dict(self) -> dict:
        """Export as dict for programmatic access."""
        with self._lock:
            return {
                "subject": self.subject,
                "total": len(self._results),
                "found": sum(1 for r in self._results if r.status == ScanStatus.FOUND),
                "blocked": sum(1 for r in self._results if r.status == ScanStatus.BLOCKED),
                "rate_limited": sum(1 for r in self._results if r.status == ScanStatus.RATE_LIMITED),
                "captcha": sum(1 for r in self._results if r.status == ScanStatus.CAPTCHA),
                "results": [r.to_dict() for r in self._results],
                "most_tags": list(self._most_tags),
                "all_tags": list(self._all_tags),
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_tags(self, tag_list: list[str]) -> None:
        """
        Replicate `Requests_Search.Search._process_tags()` logic (Story 1.2).

        MUST be called under self._lock.

        Business rules:
          - PHONE-NUMBER → skip (no tag processing)
          - tag in UNIQUE_TAGS → always add to most_tags
          - tag already in all_tags but not most_tags → add to most_tags
          - tag not in all_tags → add to all_tags (first occurrence only)
        """
        if self.subject == "PHONE-NUMBER":
            return

        for tag in tag_list:
            if tag in UNIQUE_TAGS:
                self._most_tags.append(tag)
            if tag in self._all_tags:
                if tag not in self._most_tags:
                    self._most_tags.append(tag)
            else:
                self._all_tags.append(tag)
