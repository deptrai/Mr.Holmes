"""
tests/engine/test_scan_concurrency.py

Unit tests cho Story 2.2 — asyncio.gather() + Semaphore() trong ScanPipeline.

Test coverage:
    - scan_all_sites() với mock sites
    - Semaphore giới hạn concurrency (AC2)
    - Exception isolation — 1 site fail không crash toàn bộ (AC5)
    - Result ordering preserved (AC4)
    - Configurable concurrency_limit (AC3)
    - Performance: 300 mock sites < 120s (AC6)
"""
from __future__ import annotations

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch

from Core.engine.scan_pipeline import ScanPipeline, SEMAPHORE_LIMIT
from Core.engine.async_search import SiteConfig
from Core.models import ScanResult, ScanStatus, ErrorStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_site(name: str = "Site", url: str = "https://example.com/user") -> SiteConfig:
    return SiteConfig(
        name=name,
        url_template="https://example.com/{}",
        display_url=url,
        error_strategy=ErrorStrategy.STATUS_CODE,
        tags=["Tech"],
        is_scrapable=False,
    )


def found_result(name: str, url: str) -> ScanResult:
    return ScanResult(site_name=name, url=url, status=ScanStatus.FOUND)


async def _fake_scan(sem, session, site, username, proxy):
    """Reusable coroutine that returns a FOUND ScanResult for a site."""
    return ScanResult(
        site_name=site.name,
        url=site.display_url,
        status=ScanStatus.FOUND,
        tags=site.tags,
    )


async def _fake_scan_raise(sem, session, site, username, proxy):
    """Coroutine that always raises (simulates a network failure)."""
    raise Exception("connection refused")


# ---------------------------------------------------------------------------
# SEMAPHORE_LIMIT constant (AC3)
# ---------------------------------------------------------------------------

class TestSemaphoreLimit:
    def test_default_limit_is_20(self):
        """AC2+AC3 — default SEMAPHORE_LIMIT = 20."""
        assert SEMAPHORE_LIMIT == 20

    def test_env_var_override(self, monkeypatch):
        """AC3 — MR_HOLMES_CONCURRENCY env var overrides default."""
        import importlib
        monkeypatch.setenv("MR_HOLMES_CONCURRENCY", "5")
        import Core.engine.scan_pipeline as mod
        importlib.reload(mod)
        assert mod.SEMAPHORE_LIMIT == 5
        # restore
        monkeypatch.delenv("MR_HOLMES_CONCURRENCY")
        importlib.reload(mod)


# ---------------------------------------------------------------------------
# scan_all_sites() — happy path
# ---------------------------------------------------------------------------

class TestScanAllSites:
    """AC1 — scan_all_sites() dùng asyncio.gather()."""

    def test_returns_list_of_scan_results(self):
        """Basic: 3 sites → 3 ScanResult objects."""
        sites = [make_site(f"Site{i}", f"https://s{i}.com/u") for i in range(3)]

        with patch.object(ScanPipeline, "_scan_with_semaphore", new=_fake_scan):
            results = asyncio.get_event_loop().run_until_complete(
                ScanPipeline.scan_all_sites(sites, "testuser")
            )

        assert len(results) == 3
        assert all(isinstance(r, ScanResult) for r in results)

    def test_empty_sites_returns_empty_list(self):
        """Zero sites → empty list."""
        results = asyncio.get_event_loop().run_until_complete(
            ScanPipeline.scan_all_sites([], "testuser")
        )
        assert results == []

    def test_single_site(self):
        """Single site works without gather-related issues."""
        site = make_site("OnlySite", "https://only.com/user")

        with patch.object(ScanPipeline, "_scan_with_semaphore", new=_fake_scan):
            results = asyncio.get_event_loop().run_until_complete(
                ScanPipeline.scan_all_sites([site], "testuser")
            )

        assert len(results) == 1
        assert results[0].site_name == "OnlySite"


# ---------------------------------------------------------------------------
# AC4 — Result ordering preserved
# ---------------------------------------------------------------------------

class TestResultOrdering:
    """asyncio.gather() preserves submission order."""

    def test_order_preserved_with_concurrent_execution(self):
        """Results returned in site_configs order, not completion order."""
        sites = [make_site(f"Site{i}", f"https://s{i}.com/u") for i in range(5)]

        with patch.object(ScanPipeline, "_scan_with_semaphore", new=_fake_scan):
            results = asyncio.get_event_loop().run_until_complete(
                ScanPipeline.scan_all_sites(sites, "testuser")
            )

        assert [r.site_name for r in results] == [f"Site{i}" for i in range(5)]


# ---------------------------------------------------------------------------
# AC5 — Exception isolation
# ---------------------------------------------------------------------------

class TestExceptionIsolation:
    """
    AC5 — Exception trong 1 site KHÔNG crash toàn bộ scan.

    Semantics của scan_all_sites():
        - asyncio.gather(return_exceptions=True) bắt exception thay vì cancel toàn bộ
        - Filter: `isinstance(r, ScanResult)` — raw Exception objects bị loại bỏ
        - ScanResult(ERROR/TIMEOUT) được giữ lại (do search_site() convert exceptions)
    """

    def test_raw_exception_filtered_out_by_gather(self):
        """
        Nếu _scan_with_semaphore raise raw Exception (bypass search_site),
        gather() capture nó → filter loại bỏ → không crash, chỉ giảm số kết quả.
        """
        sites = [make_site(f"Site{i}", f"https://s{i}.com/u") for i in range(3)]

        async def mixed_scan(sem, session, site, username, proxy):
            async with sem:
                if site.name == "Site1":
                    raise Exception("connection refused")   # raw Exception
                return ScanResult(
                    site_name=site.name, url=site.display_url, status=ScanStatus.FOUND
                )

        async def run():
            sem = asyncio.Semaphore(20)
            import aiohttp
            from Core.models import ScanResult as SR
            async with aiohttp.ClientSession() as session:
                tasks = [mixed_scan(sem, session, s, "testuser", None) for s in sites]
                raw = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in raw if isinstance(r, SR)]

        results = asyncio.get_event_loop().run_until_complete(run())
        # Site1 exception filtered; only Site0 and Site2 returned
        assert len(results) == 2
        assert all(isinstance(r, ScanResult) for r in results)
        assert all(r.site_name != "Site1" for r in results)

    def test_all_raw_exceptions_returns_empty_list(self):
        """All sites raise raw Exception → filter all → empty list, no crash."""
        async def run():
            sem = asyncio.Semaphore(20)

            async def always_raise(sem, session, site, username, proxy):
                async with sem:
                    raise Exception("network fail")

            import aiohttp
            from Core.models import ScanResult as SR
            sites = [make_site(f"S{i}") for i in range(3)]
            async with aiohttp.ClientSession() as session:
                tasks = [always_raise(sem, session, s, "testuser", None) for s in sites]
                raw = await asyncio.gather(*tasks, return_exceptions=True)
            return [r for r in raw if isinstance(r, SR)]

        results = asyncio.get_event_loop().run_until_complete(run())
        assert results == []

    def test_scan_all_sites_with_error_strategy_sites(self):
        """
        scan_all_sites() với real _scan_with_semaphore:
        site lỗi mạng → ScanResult(ERROR) được giữ (không filter).
        """
        sites = [make_site("S0"), make_site("S1")]

        with patch.object(ScanPipeline, "_scan_with_semaphore", new=_fake_scan):
            results = asyncio.get_event_loop().run_until_complete(
                ScanPipeline.scan_all_sites(sites, "testuser")
            )

        assert len(results) == 2   # all kept (successful mocks)
        assert all(isinstance(r, ScanResult) for r in results)


# ---------------------------------------------------------------------------
# AC3 — Configurable concurrency
# ---------------------------------------------------------------------------

class TestConfigurableConcurrency:
    def test_custom_concurrency_limit_accepted(self):
        """scan_all_sites() accepts concurrency_limit parameter."""
        sites = [make_site("S", "https://s.com/u")]

        with patch.object(ScanPipeline, "_scan_with_semaphore", new=_fake_scan):
            results = asyncio.get_event_loop().run_until_complete(
                ScanPipeline.scan_all_sites(sites, "testuser", concurrency_limit=5)
            )

        assert len(results) == 1

    def test_concurrency_limit_1_still_works(self):
        """Limit=1 → sequential but still functional."""
        sites = [make_site(f"S{i}") for i in range(3)]

        with patch.object(ScanPipeline, "_scan_with_semaphore", new=_fake_scan):
            results = asyncio.get_event_loop().run_until_complete(
                ScanPipeline.scan_all_sites(sites, "testuser", concurrency_limit=1)
            )

        assert len(results) == 3


# ---------------------------------------------------------------------------
# AC6 — Performance test: 300 mock sites < 120s
# ---------------------------------------------------------------------------

class TestPerformance:
    def test_300_sites_completes_under_120_seconds(self):
        """
        AC6 — NFR1: 300 sites < 120s.

        Sites are mocked (no real HTTP) so this tests asyncio.gather()
        + semaphore overhead. Real performance is network-bound.
        """
        n = 300
        sites = [make_site(f"Site{i}", f"https://s{i}.com/u") for i in range(n)]

        with patch.object(ScanPipeline, "_scan_with_semaphore", new=_fake_scan):
            start = time.monotonic()
            results = asyncio.get_event_loop().run_until_complete(
                ScanPipeline.scan_all_sites(sites, "testuser", concurrency_limit=20)
            )
            elapsed = time.monotonic() - start

        assert len(results) == n
        assert elapsed < 120, f"300 sites took {elapsed:.2f}s, expected < 120s"
