"""
Core/browser/browser_pool.py — AD-11: Browser Pool Management

Manages shared Playwright browser contexts for parallel scraping.
Prevents resource exhaustion when multiple social media scrapers run
in parallel (5 browsers × 250MB = 1.25GB without pooling).

Usage::

    from Core.browser.browser_pool import BrowserPool

    pool = BrowserPool.get_instance()
    ctx = await pool.get_context("facebook")
    page = await ctx.new_page()
    # ... scrape ...
    await pool.release_context("facebook")
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import Playwright
try:
    from playwright.async_api import async_playwright, BrowserContext, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None  # type: ignore
    BrowserContext = None  # type: ignore
    Playwright = None  # type: ignore

# Stealth JS injection (same as stealth_context.py)
_STEALTH_JS = """
// Overwrite navigator.webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Overwrite plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Overwrite languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en', 'vi'],
});

// Overwrite platform
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });

// Chrome runtime mock
window.chrome = { runtime: {} };

// Permissions query override
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);
"""


class BrowserPool:
    """Manages shared Playwright browser contexts for parallel scraping.

    Singleton pattern ensures all plugins share the same pool.
    Limits concurrent browser instances to prevent memory exhaustion.
    """

    _instance: "BrowserPool | None" = None

    def __init__(self, max_browsers: int = 3) -> None:
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed. Run: uv add playwright && playwright install chromium")

        self._max_browsers = max_browsers
        self._semaphore = asyncio.Semaphore(max_browsers)
        self._playwright: Any = None
        self._browser: Any = None
        self._contexts: dict[str, Any] = {}
        self._context_refs: dict[str, int] = {}  # reference count per profile
        self._lock = asyncio.Lock()
        self._initialized = False
        self._loop: asyncio.AbstractEventLoop | None = None  # track owning loop

    @classmethod
    def get_instance(cls) -> "BrowserPool":
        """Get or create the singleton BrowserPool instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _ensure_initialized(self) -> None:
        """Initialize Playwright and browser on first use.

        Detects event-loop changes (e.g., multiple asyncio.run() calls in
        MCP server) and resets the pool to avoid 'future belongs to a
        different loop' errors.
        """
        current_loop = asyncio.get_event_loop()

        # Reset if event loop changed (singleton reused across loops)
        if self._initialized and self._loop is not None and self._loop is not current_loop:
            logger.warning("BrowserPool: event loop changed, resetting pool")
            try:
                await self._force_cleanup()
            except Exception as e:
                logger.warning("BrowserPool: cleanup on loop change failed: %s", e)
            self._initialized = False
            self._loop = None

        if self._initialized:
            return
        async with self._lock:
            if self._initialized:
                return
            logger.info("BrowserPool: initializing Playwright + Chromium")
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled",
                ],
            )
            self._loop = current_loop
            self._initialized = True
            logger.info("BrowserPool: ready (max=%d browsers)", self._max_browsers)

    async def get_context(self, profile: str = "default") -> Any:
        """Get or create a browser context for the given profile.

        Uses semaphore to limit concurrent browser contexts.

        Args:
            profile: Profile name (e.g., "facebook", "instagram", "zalo").
                     Each profile gets its own context with unique fingerprint.

        Returns:
            Playwright BrowserContext
        """
        await self._semaphore.acquire()
        try:
            await self._ensure_initialized()
            async with self._lock:
                if profile not in self._contexts:
                    logger.info("BrowserPool: creating context for profile='%s'", profile)
                    ctx = await self._browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        locale="vi-VN",
                        timezone_id="Asia/Ho_Chi_Minh",
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/131.0.0.0 Safari/537.36"
                        ),
                    )
                    await ctx.add_init_script(_STEALTH_JS)
                    self._contexts[profile] = ctx
                    self._context_refs[profile] = 0

                self._context_refs[profile] += 1
                return self._contexts[profile]
        except Exception:
            self._semaphore.release()
            raise

    async def release_context(self, profile: str = "default") -> None:
        """Release a browser context reference.

        When reference count drops to 0, the context is closed to free memory.
        """
        try:
            async with self._lock:
                if profile not in self._context_refs:
                    return
                self._context_refs[profile] -= 1
                if self._context_refs[profile] <= 0:
                    ctx = self._contexts.pop(profile, None)
                    self._context_refs.pop(profile, None)
                    if ctx:
                        try:
                            await ctx.close()
                        except Exception as exc:
                            logger.warning("BrowserPool: error closing context '%s': %s", profile, exc)
                    logger.info("BrowserPool: closed context for profile='%s'", profile)
        finally:
            self._semaphore.release()

    async def cleanup(self) -> None:
        """Close all contexts and shutdown Playwright. Call on application exit."""
        async with self._lock:
            for profile, ctx in list(self._contexts.items()):
                try:
                    await ctx.close()
                except Exception as exc:
                    logger.warning("BrowserPool: error closing '%s': %s", profile, exc)
            self._contexts.clear()
            self._context_refs.clear()

            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
            self._initialized = False
            self._loop = None
            logger.info("BrowserPool: cleaned up all contexts")

    async def _force_cleanup(self) -> None:
        """Force cleanup without acquiring lock (used on event-loop change)."""
        for profile, ctx in list(self._contexts.items()):
            try:
                await ctx.close()
            except Exception:
                pass
        self._contexts.clear()
        self._context_refs.clear()

        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
        self._initialized = False
        self._loop = None
        logger.info("BrowserPool: force cleanup (event loop changed)")

    def get_stats(self) -> dict:
        """Return pool statistics for monitoring."""
        return {
            "max_browsers": self._max_browsers,
            "active_contexts": len(self._contexts),
            "profiles": list(self._contexts.keys()),
            "reference_counts": dict(self._context_refs),
            "initialized": self._initialized,
        }


# Convenience context manager
class PooledBrowserContext:
    """Async context manager for BrowserPool.

    Usage::

        async with PooledBrowserContext("facebook") as ctx:
            page = await ctx.new_page()
            await page.goto("https://mbasic.facebook.com/...")
            # ... scrape ...
    """

    def __init__(self, profile: str = "default") -> None:
        self.profile = profile
        self._ctx: Any = None

    async def __aenter__(self) -> Any:
        pool = BrowserPool.get_instance()
        self._ctx = await pool.get_context(self.profile)
        return self._ctx

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pool = BrowserPool.get_instance()
        await pool.release_context(self.profile)
