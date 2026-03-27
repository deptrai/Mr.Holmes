"""
Core/engine/async_search.py

Async HTTP search engine cho Mr.Holmes OSINT scanner.
Story 2.1 — Migrate Requests_Search → aiohttp Async Method, Epic 2.

Provides:
    search_site() — async function nhận session + site config → ScanResult
    SiteConfig    — typed config cho một site (thay thế JSON dict access)

Anti-patterns (theo Dev Notes):
    - KHÔNG implement gather/semaphore — đó là Story 2.2
    - KHÔNG xóa Requests_Search.py — backward compat được giữ ở Task 4
    - KHÔNG hardcode timeout — phải configurable
"""
from __future__ import annotations

import asyncio
import aiohttp
from dataclasses import dataclass, field
from typing import Optional

import logging

from Core.models import ScanResult, ScanStatus, ErrorStrategy
from Core.models.exceptions import (
    TargetSiteTimeout,
    ProxyDeadError,
    RateLimitExceeded,
    SiteCheckError,
)
from Core.Support import Headers

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Site config dataclass — thay thế JSON dict access trực tiếp
# ---------------------------------------------------------------------------

@dataclass
class SiteConfig:
    """
    Typed representation của 1 site entry trong site_list.json.

    Thay thế pattern: sites[data1]["error"], sites[data1]["text"], v.v.
    """
    name: str
    url_template: str          # URL với {} placeholder cho username
    display_url: str           # URL hiển thị trong report (site1 trong legacy)
    error_strategy: ErrorStrategy

    # Strategy-specific fields
    error_text: str = ""       # dùng cho ErrorStrategy.MESSAGE
    response_url: str = ""     # dùng cho ErrorStrategy.RESPONSE_URL

    # Metadata
    tags: list[str] = field(default_factory=list)
    is_scrapable: bool = False


# ---------------------------------------------------------------------------
# Default timeout (match requests.get(timeout=10))
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT_SECONDS = 10


# ---------------------------------------------------------------------------
# CAPTCHA/Block Detection (Story 3.3)
# ---------------------------------------------------------------------------

CAPTCHA_INDICATORS: tuple[str, ...] = (
    "captcha",
    "recaptcha",
    "hcaptcha",
    "cf-challenge",
    "challenge-platform",
    "challenge-form",
    "turnstile",
)


def _detect_captcha(body: str) -> bool:
    """
    AC3: Kiểm tra HTML body có chứa CAPTCHA/challenge indicators.

    Args:
        body: HTML response body (string).

    Returns:
        True nếu tìm thấy bất kỳ CAPTCHA keyword nào.
    """
    body_lower = body.lower()
    return any(indicator in body_lower for indicator in CAPTCHA_INDICATORS)



# ---------------------------------------------------------------------------
# Core async search function (Task 1 + Task 2 + Task 3)
# ---------------------------------------------------------------------------

async def search_site(
    session: aiohttp.ClientSession,
    site_config: SiteConfig,
    username: str,
    proxy: Optional[str] = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> ScanResult:
    """
    Kiểm tra username trên 1 site bất đồng bộ.

    Thay thế Requests_Search.Search.search() cho 1 site.
    Returns ScanResult thay vì mutate shared lists (AC5).

    Args:
        session:         aiohttp.ClientSession đã cấu hình.
        site_config:     Typed site metadata (AC2 — 3 strategies).
        username:        Username cần tìm kiếm.
        proxy:           Proxy URL dạng "http://host:port" (AC4 aiohttp format).
        timeout_seconds: HTTP timeout, default 10s (AC4).

    Returns:
        ScanResult với status FOUND/NOT_FOUND/ERROR/TIMEOUT.

    Raises:
        Không raise — mọi exception được catch và trả về ScanResult(ERROR/TIMEOUT).
    """
    timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    # Twitter dùng header đặc biệt
    headers = (
        Headers.Get.Twitter()
        if site_config.name == "Twitter"
        else Headers.Get.classic()
    )

    target_url = site_config.url_template.format(username)

    try:
        async with session.get(
            url=target_url,
            headers=headers,
            proxy=proxy,
            timeout=timeout,
            allow_redirects=True,
        ) as response:
            return await _evaluate_response(response, site_config, username)

    except asyncio.TimeoutError:
        exc = TargetSiteTimeout(
            site_name=site_config.name,
            url=site_config.display_url,
            timeout_seconds=timeout_seconds,
        )
        return _error_result(site_config, ScanStatus.TIMEOUT, exc)

    except aiohttp.ClientProxyConnectionError:
        exc = ProxyDeadError(
            proxy_url=str(proxy or "unknown"),
            site_name=site_config.name,
            url=site_config.display_url,
        )
        return _error_result(site_config, ScanStatus.BLOCKED, exc)

    except Exception as raw_exc:  # noqa: BLE001
        exc = SiteCheckError(
            site_name=site_config.name,
            url=site_config.display_url,
            error_type=type(raw_exc).__name__,
            original_error=raw_exc,
        )
        return _error_result(site_config, ScanStatus.ERROR, exc)


async def _evaluate_response(
    response: aiohttp.ClientResponse,
    site_config: SiteConfig,
    username: str,
) -> ScanResult:
    """
    Áp dụng error strategy để xác định found/not_found.

    Check order (Story 3.3):
        1. 403 → BLOCKED (mọi strategy)
        2. 429 → RATE_LIMITED (mọi strategy)
        3. Body CAPTCHA detection (mọi strategy khi đọc body)
        4. Strategy-specific logic

    3 strategies (AC2):
        Status-Code  — response.status == 200
        Message      — error_text NOT in response body
        Response-Url — str(response.url) != expected_url
    """
    strategy = site_config.error_strategy

    # ---- AC1: 403 → BLOCKED (mọi strategy) ----
    if response.status == 403:
        exc = RateLimitExceeded(
            site_name=site_config.name,
            url=site_config.display_url,
            status_code=403,
        )
        return _error_result(site_config, ScanStatus.BLOCKED, exc)

    # ---- AC2: 429 → RATE_LIMITED (mọi strategy) ----
    if response.status == 429:
        exc = RateLimitExceeded(
            site_name=site_config.name,
            url=site_config.display_url,
            status_code=429,
            retry_after=_parse_retry_after(response),
        )
        return _error_result(site_config, ScanStatus.RATE_LIMITED, exc)

    # ---- Status-Code strategy ----
    if strategy == ErrorStrategy.STATUS_CODE:
        if response.status == 200:
            # AC3: check CAPTCHA in body before declaring FOUND
            body = await response.text(errors="replace")
            if _detect_captcha(body):
                return _captcha_result(site_config)
            return _found_result(site_config)
        elif response.status in (404, 204):
            return _not_found_result(site_config)
        else:
            return ScanResult(
                site_name=site_config.name,
                url=site_config.display_url,
                status=ScanStatus.ERROR,
                tags=site_config.tags,
                error_message=f"HTTP {response.status}",
            )

    # ---- Message strategy ----
    elif strategy == ErrorStrategy.MESSAGE:
        if not site_config.error_text:
            return ScanResult(
                site_name=site_config.name,
                url=site_config.display_url,
                status=ScanStatus.ERROR,
                tags=site_config.tags,
                error_message="MESSAGE strategy requires non-empty error_text",
            )
        body = await response.text(errors="replace")
        if _detect_captcha(body):
            return _captcha_result(site_config)
        if site_config.error_text in body:
            return _not_found_result(site_config)
        return _found_result(site_config)

    # ---- Response-Url strategy ----
    elif strategy == ErrorStrategy.RESPONSE_URL:
        actual_url = str(response.url)
        if actual_url == site_config.response_url:
            return _not_found_result(site_config)
        return _found_result(site_config)

    # Fallback — strategy không xác định
    return ScanResult(
        site_name=site_config.name,
        url=site_config.display_url,
        status=ScanStatus.ERROR,
        error_message=f"Unknown strategy: {strategy}",
    )


def _captcha_result(site_config: SiteConfig) -> ScanResult:
    """Helper: tạo ScanResult CAPTCHA khi phát hiện challenge trong body (AC3)."""
    return ScanResult(
        site_name=site_config.name,
        url=site_config.display_url,
        status=ScanStatus.CAPTCHA,
        tags=site_config.tags,
        error_message="CAPTCHA/challenge detected in response body",
    )


def _found_result(site_config: SiteConfig) -> ScanResult:
    """Helper: tạo ScanResult FOUND với đầy đủ metadata."""
    return ScanResult(
        site_name=site_config.name,
        url=site_config.display_url,
        status=ScanStatus.FOUND,
        is_scrapable=site_config.is_scrapable,
        tags=site_config.tags,
    )


def _not_found_result(site_config: SiteConfig) -> ScanResult:
    """Helper: tạo ScanResult NOT_FOUND."""
    return ScanResult(
        site_name=site_config.name,
        url=site_config.display_url,
        status=ScanStatus.NOT_FOUND,
        tags=site_config.tags,
    )


def _error_result(site_config: SiteConfig, status: ScanStatus, exc: Exception) -> ScanResult:
    """
    Helper: log exception và trả về ScanResult với error context.
    M1 fix — loại bỏ boilerplate lặp trong mỗi except block.
    """
    logger.warning("%s", exc)
    return ScanResult(
        site_name=site_config.name,
        url=site_config.display_url,
        status=status,
        is_scrapable=False,
        tags=site_config.tags,
        error_message=str(exc),
    )


def _parse_retry_after(response: aiohttp.ClientResponse) -> Optional[int]:
    """
    Parse Retry-After header từ response (Story 2.4 — AC5 structured context).

    Returns:
        int seconds nếu header present và valid, None otherwise.
    """
    header = response.headers.get("Retry-After")
    if header is None:
        return None
    try:
        return int(header)
    except (ValueError, TypeError):
        return None
