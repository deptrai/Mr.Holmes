# 0011 Playwright Browser Automation

Date: 2026-06-26

## Status

Accepted

## Context

Several high-value OSINT sources (Instagram, Twitter/X, TikTok, LinkedIn)
actively block automated HTTP requests using:

- Cloudflare bot detection (JS challenge, TLS fingerprinting)
- CAPTCHA challenges
- User-agent and header inspection
- Rate limiting by IP reputation

The current plugin architecture (`Core/plugins/base.py`,
`IntelligencePlugin` Protocol) uses `aiohttp` for all HTTP requests via
`get_http_session()`. This works for API-based plugins (HIBP, Shodan,
Numverify) and simple scraping (Maigret, Holehe), but fails on
Cloudflare-protected sites where a real browser is required.

The existing scraper (`Core/Support/Username/Scraper.py`) uses `requests`
+ BeautifulSoup, which also cannot bypass Cloudflare. This leaves a
significant coverage gap for social media profile scraping.

Claude Code, as orchestrator, may request `scrape_profile(url)` for a
profile that requires browser automation. The tool must either succeed or
return a clear error indicating browser automation is needed.

## Decision

Add a **Playwright-based browser automation layer** as a new plugin type
(`BrowserPlugin`), living at `Core/browser/stealth_context.py`.

Key design points:

1. **Playwright Python SDK** (`pip install playwright`) — cross-browser
   (Chromium by default), async-native, well-maintained by Microsoft.

2. **Stealth configuration** — launch Chromium with anti-detection flags:
   - `--disable-blink-features=AutomationControlled`
   - Custom user-agent (rotated from `Useragents/Useragent.txt`)
   - Disable `navigator.webdriver` flag
   - Human-like delays between actions (randomized 1-3s)

3. **New plugin type** — `BrowserPlugin` extends the existing
   `IntelligencePlugin` Protocol. It implements the same `check(target,
   target_type) -> PluginResult` interface but uses Playwright `page.goto()`
   + `page.content()` instead of `aiohttp.get()`. The `PluginManager` and
   `StagedProfiler` treat it identically — no changes to orchestration code.

4. **MCP tool** — `scrape_profile(url, fields?)` is the primary browser
   tool exposed to Claude Code. It returns structured data (bio, posts,
   avatar, name) parsed from the rendered page.

5. **Lifecycle** — browser instance is lazily started on first browser
   tool call, reused across calls in the same session, and closed on
   server shutdown. One browser context per investigation (isolated
   cookies/session).

6. **Proxy integration** — Playwright browser context uses
   `ProxyManager.get_proxy()` if proxy is enabled, same as HTTP plugins.

## Alternatives Considered

1. **Selenium + undetected-chromedriver** — Popular for bot bypass, but
   Selenium is slower, less async-friendly, and `undetected-chromedriver`
   is a community project with frequent breakage. Playwright is
   officially maintained and has better async support.

2. **curl_cffi (TLS fingerprint impersonation)** — Lightweight, can bypass
   some Cloudflare checks by mimicking browser TLS fingerprints without
   a real browser. However, it cannot execute JavaScript challenges, which
   Cloudflare increasingly requires. Good for simple cases but not a
   complete solution.

3. **Headless Chrome via CDP directly** — Maximum control but requires
   significant glue code. Playwright already wraps CDP with a clean API.

4. **Third-party scraping APIs (ScrapingBee, BrightData)** — Offloads
   bot bypass to a service. Adds per-request cost and external dependency.
   Not suitable for a tool that should work offline/free.

5. **Do nothing — accept the coverage gap** — Leaves Instagram, Twitter,
   TikTok, LinkedIn profiles unscrapable. Unacceptable for a comprehensive
   OSINT tool.

## Consequences

Positive:

- Can scrape Cloudflare-protected and JS-rendered sites that HTTP plugins
  cannot reach.
- Same `IntelligencePlugin` interface — no changes to `PluginManager`,
  `StagedProfiler`, or MCP tool wrappers.
- Playwright is well-maintained, async-native, and cross-platform.
- Proxy integration works out of the box (Playwright supports proxy per
  context).

Tradeoffs:

- **Heavier dependency**: Playwright + Chromium ~200-300MB download
  (`playwright install chromium`). This is the largest dependency in the
  project.
- **Slower**: browser page load takes 2-5s vs 0.5s for HTTP. Not suitable
  for high-volume enumeration (use HTTP plugins for that, browser only for
  targeted profile scraping).
- **Resource usage**: Chromium uses ~100-200MB RAM per context. Must
  limit concurrent browser contexts.
- **Fragility**: social media sites change their DOM structure frequently.
  Browser plugins need selector maintenance, same as HTTP scrapers.
- **Detection risk**: Playwright is not invisible. Advanced bot detection
  (DataDome, PerimeterX) may still block it. Stealth config reduces but
  does not eliminate detection.
- **Safe mode**: browser automation is disabled in `safe_mode` (higher
  ban risk). Users must explicitly opt in.

## Follow-Up

- Implement `Core/browser/stealth_context.py` with stealth Chromium launch.
- Convert 2-3 high-value scrapers (Instagram, Twitter) to `BrowserPlugin`.
- Add `scrape_profile` MCP tool.
- Add Playwright to `requirements.txt` with optional install group
  (`pip install mrholmes[browser]`).
- Document selector maintenance process for browser plugins.
- Consider `curl_cffi` as a fallback for simple Cloudflare cases (lighter
  than full browser).
