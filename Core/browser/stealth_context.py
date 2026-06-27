"""Core/browser/stealth_context.py — Stealth browser context for Playwright.

Provides a browser context that bypasses common bot detection:
- Realistic user-agent
- Stealth JavaScript injection
- Viewport randomization
- Cookie persistence
"""
from __future__ import annotations
import random
from typing import Any

# Try import playwright
try:
    from playwright.async_api import async_playwright, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    async_playwright = None
    BrowserContext = None
    Page = None

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
]

STEALTH_JS = """
// Overwrite navigator.webdriver
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

// Overwrite plugins
Object.defineProperty(navigator, 'plugins', {
    get: () => [1, 2, 3, 4, 5],
});

// Overwrite languages
Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en'],
});

// Overwrite permissions
const originalQuery = window.navigator.permissions.query;
window.navigator.permissions.query = (parameters) =>
    parameters.name === 'notifications'
        ? Promise.resolve({ state: Notification.permission })
        : originalQuery(parameters);

// Mock chrome object
window.chrome = { runtime: {} };

// Overwrite WebGL vendor
const getParameter = WebGLRenderingContext.prototype.getParameter;
WebGLRenderingContext.prototype.getParameter = function(parameter) {
    if (parameter === 37445) return 'Intel Inc.';
    if (parameter === 37446) return 'Intel Iris OpenGL Engine';
    return getParameter.apply(this, [parameter]);
};
"""

class StealthBrowser:
    """Stealth browser context manager using Playwright."""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context = None
    
    async def __aenter__(self):
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")
        
        self._playwright = await async_playwright().__aenter__()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        self._context = await self._browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport=random.choice(VIEWPORTS),
            locale="en-US",
            timezone_id="America/New_York",
        )
        
        # Inject stealth scripts
        await self._context.add_init_script(STEALTH_JS)
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.__aexit__(exc_type, exc_val, exc_tb)
    
    async def new_page(self):
        """Create a new stealth page."""
        if not self._context:
            raise RuntimeError("Browser context not initialized")
        return await self._context.new_page()
    
    async def scrape_page(self, url: str, wait_for: str | None = None, 
                          timeout: int = 30000) -> dict:
        """Scrape a page with stealth browser.
        
        Args:
            url: URL to scrape
            wait_for: Optional CSS selector to wait for
            timeout: Timeout in milliseconds
        
        Returns:
            Dict with page content, title, and metadata
        """
        page = await self.new_page()
        try:
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout)
            
            # Extract data
            content = await page.content()
            title = await page.title()
            
            # Try to extract meta tags
            meta_tags = await page.evaluate("""
                () => {
                    const metas = document.querySelectorAll('meta');
                    const result = {};
                    metas.forEach(m => {
                        const name = m.getAttribute('name') || m.getAttribute('property');
                        const content = m.getAttribute('content');
                        if (name && content) result[name] = content;
                    });
                    return result;
                }
            """)
            
            return {
                "url": url,
                "title": title,
                "content_length": len(content),
                "meta_tags": meta_tags,
                "success": True,
            }
        except Exception as e:
            return {"url": url, "error": str(e), "success": False}
        finally:
            await page.close()


async def scrape_with_stealth(url: str, wait_for: str | None = None) -> dict:
    """Convenience function to scrape a single URL with stealth browser.
    
    Args:
        url: URL to scrape
        wait_for: Optional CSS selector to wait for
    
    Returns:
        Dict with scraped data
    """
    if not PLAYWRIGHT_AVAILABLE:
        return {"error": "Playwright not installed", "url": url}
    
    async with StealthBrowser() as browser:
        return await browser.scrape_page(url, wait_for)
