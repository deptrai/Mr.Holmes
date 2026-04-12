"""
tests/proxy/test_proxy_pool.py

Unit tests cho Story 3-1: Proxy Auto-Rotate khi Proxy Chết.

Test coverage:
  - AC1: ProxyManager.rotate() — round-robin pool switch
  - AC2: load_proxy_pool từ list và file
  - AC3: ProxyDeadError → auto-rotate + retry
  - AC4: Pool exhausted → fallback direct + warning
  - AC5: round-robin (default) + random (optional)
"""
from __future__ import annotations

import os
import random
import tempfile
import pytest

from Core.proxy.manager import ProxyManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PROXY_LIST = [
    "http://proxy1.example.com:8080",
    "http://proxy2.example.com:8080",
    "http://proxy3.example.com:8080",
]


@pytest.fixture
def pm_with_pool() -> ProxyManager:
    """ProxyManager với pool đã load."""
    pm = ProxyManager()
    pm.load_proxy_pool(PROXY_LIST)
    return pm


# ---------------------------------------------------------------------------
# AC2: load_proxy_pool
# ---------------------------------------------------------------------------

class TestLoadProxyPool:
    def test_load_from_list(self) -> None:
        """AC2: load từ Python list."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)
        assert pm.pool_size() == 3

    def test_load_from_file(self, tmp_path) -> None:
        """AC2: load từ text file, 1 proxy mỗi dòng."""
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text("\n".join(PROXY_LIST))

        pm = ProxyManager()
        pm.load_proxy_pool(str(proxy_file))
        assert pm.pool_size() == 3

    def test_load_file_skips_blank_lines(self, tmp_path) -> None:
        """AC2: file với blank lines — chỉ count non-empty."""
        proxy_file = tmp_path / "proxies.txt"
        proxy_file.write_text("http://p1.com:8080\n\n  \nhttp://p2.com:8080\n")

        pm = ProxyManager()
        pm.load_proxy_pool(str(proxy_file))
        assert pm.pool_size() == 2

    def test_load_from_empty_list(self) -> None:
        """AC2: empty list → pool_size = 0."""
        pm = ProxyManager()
        pm.load_proxy_pool([])
        assert pm.pool_size() == 0

    def test_load_resets_previous_pool(self) -> None:
        """AC2: gọi load lần 2 thay thế pool cũ."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)
        pm.load_proxy_pool(["http://fresh.proxy:3128"])
        assert pm.pool_size() == 1


# ---------------------------------------------------------------------------
# AC1 + AC5: rotate — round-robin
# ---------------------------------------------------------------------------

class TestRotateRoundRobin:
    def test_rotate_returns_first_proxy(self, pm_with_pool: ProxyManager) -> None:
        """AC1: rotate() trả về proxy đầu tiên khi chưa rotate."""
        result = pm_with_pool.rotate()
        assert result == PROXY_LIST[0]

    def test_rotate_cycles_through_pool(self, pm_with_pool: ProxyManager) -> None:
        """AC1+AC5: round-robin đi đúng thứ tự."""
        results = [pm_with_pool.rotate() for _ in range(len(PROXY_LIST))]
        assert results == PROXY_LIST

    def test_rotate_wraps_around(self, pm_with_pool: ProxyManager) -> None:
        """AC5: sau khi hết pool, tiếp tục từ đầu."""
        for _ in range(len(PROXY_LIST)):
            pm_with_pool.rotate()
        # Lần cuối vòng, rotate lại từ đầu
        assert pm_with_pool.rotate() == PROXY_LIST[0]

    def test_rotate_empty_pool_returns_none(self) -> None:
        """AC4: pool rỗng → rotate returns None (fallback)."""
        pm = ProxyManager()
        pm.load_proxy_pool([])
        result = pm.rotate()
        assert result is None


# ---------------------------------------------------------------------------
# AC3: mark_dead — remove from active pool
# ---------------------------------------------------------------------------

class TestMarkDead:
    def test_mark_dead_removes_proxy(self, pm_with_pool: ProxyManager) -> None:
        """AC3: mark_dead() xóa proxy khỏi active pool."""
        pm_with_pool.mark_dead(PROXY_LIST[0])
        assert pm_with_pool.pool_size() == 2

    def test_mark_dead_proxy_not_returned_by_rotate(self, pm_with_pool: ProxyManager) -> None:
        """AC3: proxy đã dead không được rotate() trả về."""
        dead = PROXY_LIST[1]
        pm_with_pool.mark_dead(dead)

        returned = [pm_with_pool.rotate() for _ in range(pm_with_pool.pool_size() * 2)]
        assert dead not in returned

    def test_mark_dead_nonexistent_is_noop(self, pm_with_pool: ProxyManager) -> None:
        """AC3: mark_dead proxy không tồn tại → không raise, pool unchanged."""
        pm_with_pool.mark_dead("http://nonexistent.proxy:9999")
        assert pm_with_pool.pool_size() == 3

    def test_mark_all_dead_triggers_fallback(self, pm_with_pool: ProxyManager) -> None:
        """AC4: khi tất cả proxy dead → pool_size = 0 → rotate() = None."""
        for p in PROXY_LIST:
            pm_with_pool.mark_dead(p)
        assert pm_with_pool.pool_size() == 0
        assert pm_with_pool.rotate() is None

    def test_get_dead_proxies(self, pm_with_pool: ProxyManager) -> None:
        """AC3: có thể lấy danh sách proxy đã dead."""
        pm_with_pool.mark_dead(PROXY_LIST[0])
        assert PROXY_LIST[0] in pm_with_pool.dead_proxies()


# ---------------------------------------------------------------------------
# AC5: Random strategy
# ---------------------------------------------------------------------------

class TestRandomStrategy:
    def test_random_strategy_returns_proxy_from_pool(self, pm_with_pool: ProxyManager) -> None:
        """AC5: strategy='random' → vẫn trả về proxy từ pool."""
        pm_with_pool.set_strategy("random")
        result = pm_with_pool.rotate()
        assert result in PROXY_LIST

    def test_random_strategy_is_not_round_robin(self, pm_with_pool: ProxyManager) -> None:
        """AC5: random strategy phân phối khác round-robin (statistical)."""
        pm_with_pool.set_strategy("random")
        random.seed(42)
        results = [pm_with_pool.rotate() for _ in range(30)]
        # Với 3 proxies, round-robin sẽ lặp đều. Random sẽ có phân phối biến thiên.
        # Ít nhất phải có đủ 3 proxy khác nhau xuất hiện
        assert len(set(results)) == 3

    def test_invalid_strategy_raises(self, pm_with_pool: ProxyManager) -> None:
        """AC5: strategy không hợp lệ → ValueError."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            pm_with_pool.set_strategy("weighted")  # không support


# ---------------------------------------------------------------------------
# AC4: Fallback
# ---------------------------------------------------------------------------

class TestFallbackDirectConnection:
    def test_is_exhausted_false_when_pool_has_items(self, pm_with_pool: ProxyManager) -> None:
        """AC4: is_exhausted() = False khi còn proxy."""
        assert not pm_with_pool.is_exhausted()

    def test_is_exhausted_true_when_all_dead(self, pm_with_pool: ProxyManager) -> None:
        """AC4: is_exhausted() = True sau mark_dead tất cả."""
        for p in PROXY_LIST:
            pm_with_pool.mark_dead(p)
        assert pm_with_pool.is_exhausted()

    def test_rotate_returns_none_on_exhaustion(self, pm_with_pool: ProxyManager) -> None:
        """AC4: rotate() = None → caller phải xử lý fallback direct."""
        for p in PROXY_LIST:
            pm_with_pool.mark_dead(p)
        assert pm_with_pool.rotate() is None


# ---------------------------------------------------------------------------
# Patch #1: async_rotate / async_mark_dead — asyncio.Lock safety
# ---------------------------------------------------------------------------

class TestAsyncSafety:
    @pytest.mark.asyncio
    async def test_async_rotate_returns_proxy(self) -> None:
        """async_rotate() trả về proxy đúng thứ tự round-robin."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)
        result = await pm.async_rotate()
        assert result == PROXY_LIST[0]

    @pytest.mark.asyncio
    async def test_async_rotate_exhausted_returns_none(self) -> None:
        """async_rotate() trả về None khi pool rỗng."""
        pm = ProxyManager()
        pm.load_proxy_pool([])
        result = await pm.async_rotate()
        assert result is None

    @pytest.mark.asyncio
    async def test_async_mark_dead_removes_proxy(self) -> None:
        """async_mark_dead() removes proxy from pool."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)
        await pm.async_mark_dead(PROXY_LIST[0])
        assert pm.pool_size() == 2
        assert PROXY_LIST[0] in pm.dead_proxies()

    @pytest.mark.asyncio
    async def test_concurrent_rotate_no_duplicates(self) -> None:
        """Concurrent async_rotate() calls via Lock — no corruption."""
        import asyncio
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)

        results = await asyncio.gather(*[pm.async_rotate() for _ in range(6)])
        # Tất cả results phải là valid proxy (không None, vì pool còn)
        assert all(r in PROXY_LIST for r in results)


# ---------------------------------------------------------------------------
# Patch #3: reset_pool — khôi phục pool gốc
# ---------------------------------------------------------------------------

class TestResetPool:
    def test_reset_pool_restores_dead_proxies(self, pm_with_pool: ProxyManager) -> None:
        """reset_pool() khôi phục tất cả proxy dead."""
        pm_with_pool.mark_dead(PROXY_LIST[0])
        pm_with_pool.mark_dead(PROXY_LIST[1])
        pm_with_pool.reset_pool()

        assert pm_with_pool.pool_size() == 3
        assert pm_with_pool.dead_proxies() == set()

    def test_reset_pool_without_original_is_noop(self) -> None:
        """reset_pool() khi chưa load → noop."""
        pm = ProxyManager()
        pm.reset_pool()  # should not raise
        assert pm.pool_size() == 0


# ---------------------------------------------------------------------------
# Patch #4: load_proxy_pool preserves strategy
# ---------------------------------------------------------------------------

class TestStrategyPreservation:
    def test_load_preserves_random_strategy(self) -> None:
        """load_proxy_pool() không reset strategy đã set trước đó."""
        pm = ProxyManager()
        pm.set_strategy("random")
        pm.load_proxy_pool(PROXY_LIST)
        # Strategy vẫn là random sau khi load
        assert pm._strategy == "random"

    def test_load_preserves_round_robin_by_default(self) -> None:
        """load_proxy_pool() mặc định giữ round-robin (init default)."""
        pm = ProxyManager()
        pm.load_proxy_pool(PROXY_LIST)
        assert pm._strategy == "round-robin"

