"""
tests/proxy/test_proxy_rotate_integration.py

Integration tests cho Story 3-1 Task 3+4:
  - AC3: ProxyDeadError → auto-rotate + retry
  - AC4: pool exhausted → fallback direct connection + warning
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from Core.proxy.manager import ProxyManager
from Core.models.exceptions import ProxyDeadError


PROXY_LIST = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080",
]


# ---------------------------------------------------------------------------
# Unit tests: ProxyDeadError → rotate logic (synchronous, no aiohttp needed)
# ---------------------------------------------------------------------------

class TestProxyRotateOnDead:
    """
    Test rotate pattern khi gặp ProxyDeadError.

    Pattern (AC3):
        try:
            result = await search(proxy=pm.rotate())
        except ProxyDeadError as e:
            pm.mark_dead(e.proxy_url)
            result = await search(proxy=pm.rotate())
    """

    def test_rotate_after_mark_dead_skips_dead_proxy(self) -> None:
        """AC3: sau mark_dead, proxy tiếp theo khác proxy chết."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        first = pm.rotate()               # proxy1
        pm.mark_dead(first)               # proxy1 → dead
        second = pm.rotate()              # phải là proxy2 hoặc proxy3
        assert second != first
        assert second is not None

    def test_successive_failures_exhaust_pool(self) -> None:
        """AC4: liên tiếp mark_dead cho đến khi pool cạn."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        for _ in range(len(PROXY_LIST)):
            current = pm.rotate()
            if current is None:
                break
            pm.mark_dead(current)

        # Pool phải exhausted
        assert pm.is_exhausted()
        assert pm.rotate() is None

    def test_fallback_after_pool_exhausted(self) -> None:
        """AC4: rotate() = None → signal cho caller dùng direct connection."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        for p in PROXY_LIST:
            pm.mark_dead(p)

        # None = signal fallback direct
        fallback_proxy = pm.rotate()
        assert fallback_proxy is None

    def test_dead_proxies_tracked_correctly(self) -> None:
        """AC3: dead_proxies() track đúng."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        pm.mark_dead(PROXY_LIST[0])
        pm.mark_dead(PROXY_LIST[2])

        dead = pm.dead_proxies()
        assert PROXY_LIST[0] in dead
        assert PROXY_LIST[2] in dead
        assert PROXY_LIST[1] not in dead

    def test_live_proxies_subset_of_original(self) -> None:
        """AC3: proxy còn sống chỉ là subset của pool gốc."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)
        pm.mark_dead(PROXY_LIST[0])

        # Lấy tất cả proxy còn trong pool
        remaining = [pm.rotate() for _ in range(pm.pool_size())]
        for r in remaining:
            assert r in PROXY_LIST
            assert r != PROXY_LIST[0]


# ---------------------------------------------------------------------------
# Async integration tests: simulate ProxyDeadError trong scan loop
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retry_with_rotated_proxy_on_dead_error() -> None:
    """
    AC3: Simulate scan_site raise ProxyDeadError → rotate → retry thành công.

    Đây là pattern caller nên implement:
    1. rotate() → proxy1
    2. search_site() với proxy1 → ProxyDeadError
    3. mark_dead(proxy1)
    4. rotate() → proxy2
    5. search_site() với proxy2 → thành công
    """
    from Core.models import ScanStatus
    
    pm = ProxyManager()
    pm.load_proxy_pool(PROXY_LIST)

    call_count = 0

    async def mock_search(proxy: str | None) -> str:
        nonlocal call_count
        call_count += 1
        if proxy == PROXY_LIST[0]:
            raise ProxyDeadError(
                proxy_url=PROXY_LIST[0],
                site_name="TestSite",
                url="http://testsite.com",
            )
        return "SUCCESS"

    # Simulate AC3 pattern
    proxy = pm.rotate()
    try:
        result = await mock_search(proxy=proxy)
    except ProxyDeadError as e:
        pm.mark_dead(e.proxy_url)
        proxy = pm.rotate()
        result = await mock_search(proxy=proxy)

    assert result == "SUCCESS"
    assert call_count == 2
    assert PROXY_LIST[0] in pm.dead_proxies()


@pytest.mark.asyncio
async def test_fallback_direct_when_all_proxies_dead() -> None:
    """
    AC4: tất cả proxy dead → fallback direct connection với proxy=None.
    """
    pm = ProxyManager()
    pm.load_proxy_pool(["http://proxy1.dead:8080"])

    async def mock_search(proxy: str | None) -> str:
        if proxy is not None:
            raise ProxyDeadError(
                proxy_url=proxy,
                site_name="TestSite",
                url="http://test.com",
            )
        return "DIRECT_SUCCESS"

    proxy = pm.rotate()
    try:
        result = await mock_search(proxy=proxy)
    except ProxyDeadError as e:
        pm.mark_dead(e.proxy_url)
        # Pool exhausted → rotate() = None → direct connection
        proxy = pm.rotate()
        assert proxy is None
        result = await mock_search(proxy=proxy)

    assert result == "DIRECT_SUCCESS"
    assert pm.is_exhausted()
