"""
tests/proxy/test_proxy_health.py

Unit tests cho Story 3-2: Proxy Health-Check trước Session.

Test coverage:
  - AC1: health_check() async method
  - AC2: gửi request tới known endpoint
  - AC3: timeout 5s per proxy
  - AC4: HealthReport: healthy/dead/total counts
  - AC5: auto-remove dead proxies từ pool
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from Core.proxy.manager import ProxyManager, HealthReport


PROXY_LIST = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080",
]

TEST_URL = "http://httpbin.org/ip"


# ---------------------------------------------------------------------------
# AC4: HealthReport dataclass
# ---------------------------------------------------------------------------

class TestHealthReport:
    def test_health_report_is_dataclass(self) -> None:
        """AC4: HealthReport là dataclass với required fields."""
        report = HealthReport(total=3, healthy=2, dead=1, dead_urls=["http://proxy3:8080"])
        assert report.total == 3
        assert report.healthy == 2
        assert report.dead == 1
        assert report.dead_urls == ["http://proxy3:8080"]

    def test_health_report_dead_plus_healthy_equals_total(self) -> None:
        """AC4: healthy + dead == total."""
        report = HealthReport(total=5, healthy=3, dead=2, dead_urls=["a", "b"])
        assert report.healthy + report.dead == report.total

    def test_health_report_empty(self) -> None:
        """AC4: HealthReport cho empty pool."""
        report = HealthReport(total=0, healthy=0, dead=0, dead_urls=[])
        assert report.total == 0


# ---------------------------------------------------------------------------
# AC1 + AC2: health_check() async method
# ---------------------------------------------------------------------------

class TestHealthCheckMethod:
    @pytest.mark.asyncio
    async def test_health_check_returns_health_report(self) -> None:
        """AC1: health_check() trả về HealthReport instance."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        # Mock tất cả proxies healthy
        async def mock_check(proxy: str, url: str, timeout: float, session: object) -> bool:
            return True

        with patch.object(pm, "_check_single_proxy", side_effect=mock_check):
            report = await pm.health_check(test_url=TEST_URL)

        assert isinstance(report, HealthReport)

    @pytest.mark.asyncio
    async def test_health_check_empty_pool_returns_zero_report(self) -> None:
        """AC1+AC4: empty pool → HealthReport(0, 0, 0, [])."""
        pm = ProxyManager()
        pm.load_proxy_pool([])

        report = await pm.health_check(test_url=TEST_URL)

        assert report.total == 0
        assert report.healthy == 0
        assert report.dead == 0
        assert report.dead_urls == []

    @pytest.mark.asyncio
    async def test_all_healthy_report(self) -> None:
        """AC4: tất cả proxies healthy → dead=0."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        async def mock_check(proxy: str, url: str, timeout: float, session: object) -> bool:
            return True  # tất cả healthy

        with patch.object(pm, "_check_single_proxy", side_effect=mock_check):
            report = await pm.health_check(test_url=TEST_URL)

        assert report.total == 3
        assert report.healthy == 3
        assert report.dead == 0
        assert report.dead_urls == []

    @pytest.mark.asyncio
    async def test_all_dead_report(self) -> None:
        """AC4: tất cả proxies dead → healthy=0."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        async def mock_check(proxy: str, url: str, timeout: float, session: object) -> bool:
            return False  # tất cả dead

        with patch.object(pm, "_check_single_proxy", side_effect=mock_check):
            report = await pm.health_check(test_url=TEST_URL)

        assert report.total == 3
        assert report.healthy == 0
        assert report.dead == 3
        assert set(report.dead_urls) == set(PROXY_LIST)

    @pytest.mark.asyncio
    async def test_mixed_healthy_dead_report(self) -> None:
        """AC4: mixed → đếm đúng healthy và dead."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        async def mock_check(proxy: str, url: str, timeout: float, session: object) -> bool:
            return proxy == PROXY_LIST[0]  # chỉ proxy1 healthy

        with patch.object(pm, "_check_single_proxy", side_effect=mock_check):
            report = await pm.health_check(test_url=TEST_URL)

        assert report.total == 3
        assert report.healthy == 1
        assert report.dead == 2
        assert PROXY_LIST[0] not in report.dead_urls


# ---------------------------------------------------------------------------
# AC3: timeout 5s per proxy
# ---------------------------------------------------------------------------

class TestHealthCheckTimeout:
    @pytest.mark.asyncio
    async def test_health_check_uses_5s_timeout_by_default(self) -> None:
        """AC3: timeout mặc định là 5.0s."""
        pm = ProxyManager()
        pm.load_proxy_pool([PROXY_LIST[0]])

        received_timeout = None

        async def capture_timeout(proxy: str, url: str, timeout: float, session: object) -> bool:
            nonlocal received_timeout
            received_timeout = timeout
            return True

        with patch.object(pm, "_check_single_proxy", side_effect=capture_timeout):
            await pm.health_check(test_url=TEST_URL)

        assert received_timeout == 5.0

    @pytest.mark.asyncio
    async def test_health_check_accepts_custom_timeout(self) -> None:
        """AC3: caller có thể override timeout."""
        pm = ProxyManager()
        pm.load_proxy_pool([PROXY_LIST[0]])

        received_timeout = None

        async def capture_timeout(proxy: str, url: str, timeout: float, session: object) -> bool:
            nonlocal received_timeout
            received_timeout = timeout
            return True

        with patch.object(pm, "_check_single_proxy", side_effect=capture_timeout):
            await pm.health_check(test_url=TEST_URL, timeout=10.0)

        assert received_timeout == 10.0


# ---------------------------------------------------------------------------
# AC5: auto-remove dead proxies
# ---------------------------------------------------------------------------

class TestHealthCheckAutoPrune:
    @pytest.mark.asyncio
    async def test_dead_proxy_auto_removed_from_pool(self) -> None:
        """AC5: dead proxy bị xóa khỏi active pool sau health_check."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        async def mock_check(proxy: str, url: str, timeout: float, session: object) -> bool:
            return proxy != PROXY_LIST[1]  # proxy2 là dead

        with patch.object(pm, "_check_single_proxy", side_effect=mock_check):
            await pm.health_check(test_url=TEST_URL)

        assert pm.pool_size() == 2
        assert PROXY_LIST[1] in pm.dead_proxies()

    @pytest.mark.asyncio
    async def test_healthy_proxy_stays_in_pool(self) -> None:
        """AC5: healthy proxy không bị xóa."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        async def mock_check(proxy: str, url: str, timeout: float, session: object) -> bool:
            return True  # tất cả healthy

        with patch.object(pm, "_check_single_proxy", side_effect=mock_check):
            await pm.health_check(test_url=TEST_URL)

        assert pm.pool_size() == 3
        assert pm.dead_proxies() == set()

    @pytest.mark.asyncio
    async def test_all_dead_pool_exhausted(self) -> None:
        """AC5: tất cả dead → pool exhausted sau health_check."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        async def mock_check(proxy: str, url: str, timeout: float, session: object) -> bool:
            return False

        with patch.object(pm, "_check_single_proxy", side_effect=mock_check):
            await pm.health_check(test_url=TEST_URL)

        assert pm.is_exhausted()


# ---------------------------------------------------------------------------
# Task 2: concurrent execution
# ---------------------------------------------------------------------------

class TestHealthCheckConcurrent:
    @pytest.mark.asyncio
    async def test_health_check_runs_concurrently(self) -> None:
        """Task 2: health_check dùng asyncio.gather (concurrent, không sequential)."""
        import time
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        call_times: list[float] = []

        async def slow_check(proxy: str, url: str, timeout: float, session: object) -> bool:
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.05)  # 50ms per check
            return True

        with patch.object(pm, "_check_single_proxy", side_effect=slow_check):
            start = asyncio.get_event_loop().time()
            await pm.health_check(test_url=TEST_URL)
            elapsed = asyncio.get_event_loop().time() - start

        # Concurrent: 3 checks × 50ms = ~50ms total (not 150ms)
        # Allow generous margin: phải < 200ms nếu concurrent
        assert elapsed < 0.2, f"Health check took {elapsed:.3f}s — not concurrent?"
        assert len(call_times) == 3
