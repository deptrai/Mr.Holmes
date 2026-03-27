"""
Core/proxy/manager.py

ProxyManager — centralizes proxy configuration and ip-api.com identity lookup.

Replaces 8 occurrences of copy-paste proxy init across:
  - Core/Searcher.py
  - Core/Searcher_phone.py
  - Core/Searcher_website.py
  - Core/Searcher_person.py
  - Core/engine/scan_pipeline.py (_resolve_proxy_identity)

Story 1.5 — Extract ProxyManager Class, Epic 1.
Story 3.1 — Proxy Auto-Rotate: load_proxy_pool, rotate, mark_dead (Epic 3).
Foundation for Epic 3 (health-check, captcha-detection).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import random as _random
import urllib.request
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, List, Literal, Optional, Set

import aiohttp

from Core.Support import Language

filename = Language.Translation.Get_Language()

_IP_API_BASE = "http://ip-api.com/json/"
_VALID_STRATEGIES = ("round-robin", "random")

logger = logging.getLogger(__name__)


@dataclass
class HealthReport:
    """AC4: Báo cáo kết quả health check."""
    total: int
    healthy: int
    dead: int
    dead_urls: list[str] = field(default_factory=list)


class ProxyManager:
    """
    Encapsulates proxy configuration, identity resolution, pool rotation, and reset.

    Story 1.5 API (unchanged):
        pm.configure(choice)               # choice=1 → enable, else None
        pm.get_proxy()                     # {http, https} or None
        pm.get_identity()                  # "Region, Country" or None
        pm.reset()                         # disable proxy

    Story 3.1 API (new):
        pm.load_proxy_pool(source)         # str = file path | list = direct list
        pm.rotate() -> str | None          # next proxy URL or None if exhausted
        pm.mark_dead(proxy_url)            # remove from active pool
        pm.pool_size() -> int              # number of live proxies
        pm.is_exhausted() -> bool          # True when no proxies remain
        pm.dead_proxies() -> set[str]      # set of dead proxy URLs
        pm.set_strategy(strategy)          # "round-robin" (default) | "random"
    """

    def __init__(self) -> None:
        # Story 1.5 state
        self._proxy_dict: Optional[dict] = None
        self._proxy_ip: str = "None"
        self._identity: Optional[str] = None
        self._enabled: bool = False

        # Story 3.1 pool state
        self._pool: Deque[str] = deque()           # active proxies (round-robin cursor)
        self._dead: Set[str] = set()               # dead proxy URLs
        self._original_pool: List[str] = []        # original full list (for reset_pool)
        self._strategy: Literal["round-robin", "random"] = "round-robin"
        self._pool_lock: asyncio.Lock = asyncio.Lock()  # thread-safety for pool ops

    # ------------------------------------------------------------------
    # configure() — AC3 (Story 1.5)
    # ------------------------------------------------------------------
    def configure(self, choice: int) -> None:
        """
        Set up proxy based on user choice.

        Args:
            choice: 1 = use proxy from config; anything else = no proxy.
        """
        if choice == 1:
            from Core.Support import Proxies
            self._proxy_dict = Proxies.proxy.final_proxis
            self._proxy_ip = Proxies.proxy.choice3
            self._enabled = True
            self._identity = self._resolve_identity()
        else:
            self._proxy_dict = None
            self._proxy_ip = "None"
            self._enabled = False
            self._identity = None

    # ------------------------------------------------------------------
    # get_proxy() — AC3 (Story 1.5)
    # ------------------------------------------------------------------
    def get_proxy(self) -> Optional[dict]:
        """Return proxy dict {http, https} or None if proxy not enabled."""
        return self._proxy_dict

    # ------------------------------------------------------------------
    # get_identity() — AC3 / AC4 (Story 1.5)
    # ------------------------------------------------------------------
    def get_identity(self) -> Optional[str]:
        """
        Return the geo-identity string for the current proxy, or None.

        Resolved once during configure(); cached thereafter.
        """
        return self._identity

    @property
    def proxy_ip(self) -> str:
        """Return the raw proxy IP string (e.g. '192.168.1.1') or 'None'."""
        return self._proxy_ip

    # ------------------------------------------------------------------
    # reset() — AC3 (Story 1.5)
    # ------------------------------------------------------------------
    def reset(self) -> None:
        """
        Disable proxy (fallback scenario — retry without proxy).

        After reset(), get_proxy() returns None.
        get_identity() still returns the cached identity string.
        """
        self._proxy_dict = None
        self._enabled = False

    # ------------------------------------------------------------------
    # is_enabled() — convenience (Story 1.5)
    # ------------------------------------------------------------------
    def is_enabled(self) -> bool:
        """Return True if proxy is currently active."""
        return self._enabled

    # ------------------------------------------------------------------
    # ip-api.com lookup — AC4 (Story 1.5)
    # ------------------------------------------------------------------
    def _resolve_identity(self) -> Optional[str]:
        """
        Query ip-api.com to get geo-location of the current proxy IP.

        Returns formatted identity string, or None on any failure.
        """
        if self._proxy_ip == "None":
            return None
        try:
            url = _IP_API_BASE + self._proxy_ip
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
            region = data.get("regionName", "Unknown")
            country = data.get("country", "Unknown")
            return Language.Translation.Translate_Language(
                filename, "Default", "ProxyLoc", "None").format(region, country)
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return None

    # ==================================================================
    # Story 3.1 — Proxy Pool Methods
    # ==================================================================

    def load_proxy_pool(self, source: "str | list") -> None:
        """
        Load proxy pool từ Python list hoặc text file.

        AC2: pool configurable từ file (1 proxy/dòng) hoặc list.
        Gọi lần 2 sẽ reset và thay thế pool cũ hoàn toàn.

        Args:
            source: path tới file text (str) hoặc list của proxy URLs.
        """
        if isinstance(source, list):
            proxies = [p.strip() for p in source if p.strip()]
        else:
            # str → đường dẫn file
            if not os.path.isfile(source):
                raise FileNotFoundError(f"Proxy pool file not found: {source}")
            with open(source, "r", encoding="utf-8") as fh:
                proxies = [line.strip() for line in fh if line.strip()]

        # Reset pool state — giữ nguyên strategy hiện tại
        self._original_pool = list(proxies)
        self._pool = deque(proxies)
        self._dead = set()
        # Không reset self._strategy — giữ strategy đã set trước đó

        logger.info("Loaded %d proxies into pool (strategy=%s)", len(proxies), self._strategy)

    def rotate(self) -> Optional[str]:
        """
        Trả về proxy tiếp theo theo rotation strategy, hoặc None nếu pool cạn.

        AC1: switch sang proxy tiếp theo trong pool.
        AC4: pool exhausted → trả về None (caller xử lý fallback).
        AC5: strategy round-robin hoặc random.

        Thread-safe: dùng nội bộ deque operations (atomic ở CPython GIL level).
        Cho async callers, dùng async_rotate() thay thế.

        Returns:
            proxy URL string, hoặc None nếu pool trống/exhausted.
        """
        if not self._pool:
            # AC4: không còn proxy → fallback direct connection
            logger.warning("Proxy pool exhausted — falling back to direct connection")
            return None

        if self._strategy == "random":
            pool_list = list(self._pool)
            return _random.choice(pool_list)
        else:
            # round-robin: lấy từ trái, xoay vòng về phía phải
            proxy = self._pool[0]
            self._pool.rotate(-1)
            return proxy

    async def async_rotate(self) -> Optional[str]:
        """
        Async-safe version of rotate(). Dùng asyncio.Lock để đảm bảo
        chỉ 1 coroutine truy cập pool tại 1 thời điểm.

        Returns:
            proxy URL string, hoặc None nếu pool trống/exhausted.
        """
        async with self._pool_lock:
            return self.rotate()

    async def async_mark_dead(self, proxy_url: str) -> None:
        """
        Async-safe version of mark_dead(). Dùng asyncio.Lock.

        Args:
            proxy_url: URL của proxy đã dead.
        """
        async with self._pool_lock:
            self.mark_dead(proxy_url)

    def mark_dead(self, proxy_url: str) -> None:
        """
        Đánh dấu proxy là dead và xóa khỏi active pool.

        AC3: gọi khi nhận ProxyDeadError để loại bỏ proxy khỏi pool.
        Nếu proxy không tồn tại trong pool → noop (không raise).

        Args:
            proxy_url: URL của proxy đã dead (ví dụ "http://host:port").
        """
        if proxy_url in self._pool:
            self._pool.remove(proxy_url)
            self._dead.add(proxy_url)
            logger.warning("Proxy marked dead and removed: %s", proxy_url)
        # noop nếu proxy không còn trong pool

    def pool_size(self) -> int:
        """
        Số lượng proxy còn sống trong pool.

        Returns:
            Số proxy sẵn sàng. 0 nếu pool đã exhausted.
        """
        return len(self._pool)

    def is_exhausted(self) -> bool:
        """
        Kiểm tra pool đã cạn chưa.

        AC4: caller dùng để phát hiện tình trạng không còn proxy nào.

        Returns:
            True nếu không còn proxy nào sống trong pool.
        """
        return len(self._pool) == 0

    def dead_proxies(self) -> Set[str]:
        """
        Trả về tập hợp các proxy đã bị đánh dấu dead.

        AC3: diagnostic / logging.

        Returns:
            set[str] của các proxy URL đã dead.
        """
        return set(self._dead)

    def set_strategy(self, strategy: str) -> None:
        """
        Thiết lập rotation strategy.

        AC5: "round-robin" (default) hoặc "random".

        Args:
            strategy: "round-robin" hoặc "random".

        Raises:
            ValueError: nếu strategy không hợp lệ.
        """
        if strategy not in _VALID_STRATEGIES:
            raise ValueError(
                f"Unknown strategy: '{strategy}'. "
                f"Valid options: {_VALID_STRATEGIES}"
            )
        self._strategy = strategy  # type: ignore[assignment]

    def reset_pool(self) -> None:
        """
        Khôi phục pool về trạng thái ban đầu (tất cả proxy sống lại).

        Useful khi muốn retry toàn bộ pool sau khi một số proxy
        tạm thời unavailable.
        """
        if not self._original_pool:
            logger.warning("No original pool to reset from")
            return
        self._pool = deque(self._original_pool)
        self._dead.clear()
        logger.info("Pool reset — %d proxies restored", len(self._pool))

    async def _check_single_proxy(
        self,
        proxy: str,
        url: str,
        timeout: float,
        session: aiohttp.ClientSession,
    ) -> bool:
        """
        Kiểm tra trạng thái của một proxy bằng cách gửi request.

        Args:
            session: shared aiohttp.ClientSession (tránh tạo session mới cho mỗi proxy).
        """
        try:
            async with session.get(url, proxy=proxy, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                return resp.status == 200
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as e:
            logger.debug("Health check failed cho proxy %s: %s", proxy, e)
            return False

    async def health_check(
        self,
        test_url: str = "http://httpbin.org/ip",
        timeout: float = 5.0
    ) -> HealthReport:
        """
        Thực hiện proxy health check (AC1).
        - Gửi request tới known endpoint (AC2).
        - Có timeout (AC3).
        - Tự động remove proxies bị chết (AC5).

        Returns: HealthReport báo cáo số lượng healthy/dead (AC4).
        """
        if not self._pool:
            return HealthReport(total=0, healthy=0, dead=0, dead_urls=[])

        # Snapshot pool hiện tại
        proxies_to_check = list(self._pool)

        # Patch #1: share 1 session cho toàn bộ batch — tránh 50+ TCP pools
        async with aiohttp.ClientSession() as session:
            # Task 2: concurrent health check bằng asyncio.gather
            tasks = [
                self._check_single_proxy(proxy, test_url, timeout, session)
                for proxy in proxies_to_check
            ]

            # return_exceptions=True để ngăn fail-fast nếu crash
            results = await asyncio.gather(*tasks, return_exceptions=True)

        healthy_count = 0
        dead_count = 0
        dead_urls: list[str] = []

        for proxy, result in zip(proxies_to_check, results):
            if isinstance(result, bool) and result:
                healthy_count += 1
            else:
                dead_count += 1
                dead_urls.append(proxy)
                # Task 5: Auto-remove proxy nếu dead
                await self.async_mark_dead(proxy)

        logger.info("Proxy health check xong: %d total, %d healthy, %d dead.",
                    len(proxies_to_check), healthy_count, dead_count)

        return HealthReport(
            total=len(proxies_to_check),
            healthy=healthy_count,
            dead=dead_count,
            dead_urls=dead_urls
        )
