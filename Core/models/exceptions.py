"""
Core/models/exceptions.py

OSINTError exception hierarchy — typed errors thay thế generic except Exception: pass.
Phần của Story 1.1 — Foundation Refactoring, Epic 1.
Updated Story 2.4 — Custom Exception Classes, Epic 2.
"""
from __future__ import annotations

from typing import Optional


class OSINTError(Exception):
    """
    Base exception cho tất cả Mr.Holmes OSINT operations.

    Mọi exception trong project đều inherit từ class này,
    cho phép caller catch `OSINTError` để xử lý tất cả OSINT-related errors.
    """

    def __init__(self, message: str, site_name: str = "", url: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.site_name = site_name
        self.url = url

    def __str__(self) -> str:
        parts = [self.message]
        if self.site_name:
            parts.append(f"site={self.site_name}")
        if self.url:
            parts.append(f"url={self.url}")
        return " | ".join(parts)


class TargetSiteTimeout(OSINTError):
    """
    Request tới target site bị timeout.

    Raise khi: requests.exceptions.Timeout hoặc asyncio.TimeoutError
    """

    def __init__(
        self,
        site_name: str,
        url: str,
        timeout_seconds: float = 10.0,
    ) -> None:
        super().__init__(
            f"Request timed out after {timeout_seconds}s",
            site_name=site_name,
            url=url,
        )
        self.timeout_seconds = timeout_seconds

    def __str__(self) -> str:
        return (
            f"TargetSiteTimeout | site={self.site_name} | url={self.url} "
            f"| timeout={self.timeout_seconds}s"
        )


class ProxyDeadError(OSINTError):
    """
    Proxy không thể kết nối tới target site.

    Raise khi: proxy connection refused, proxy auth failed, etc.
    """

    def __init__(self, proxy_url: str, site_name: str, url: str = "") -> None:
        super().__init__(
            f"Proxy connection failed: {proxy_url}",
            site_name=site_name,
            url=url,
        )
        self.proxy_url = proxy_url

    def __str__(self) -> str:
        return (
            f"ProxyDeadError | proxy={self.proxy_url} "
            f"| site={self.site_name}"
        )


class RateLimitExceeded(OSINTError):
    """
    Target site trả về HTTP 429 hoặc 403 (rate limited / blocked).

    Raise khi: response.status_code in (429, 403)
    """

    def __init__(
        self,
        site_name: str,
        url: str,
        status_code: int,
        retry_after: Optional[int] = None,
    ) -> None:
        super().__init__(
            f"Rate limited with HTTP {status_code}",
            site_name=site_name,
            url=url,
        )
        self.status_code = status_code
        self.retry_after = retry_after  # giây, từ Retry-After header nếu có

    def __str__(self) -> str:
        base = (
            f"RateLimitExceeded | site={self.site_name} "
            f"| status={self.status_code}"
        )
        if self.retry_after:
            base += f" | retry_after={self.retry_after}s"
        return base


class ScraperError(OSINTError):
    """
    Lỗi xảy ra trong quá trình scrape profile (Instagram, Twitter, etc.).

    Raise khi: Scraper.info.* raises exception
    """

    def __init__(
        self,
        scraper_name: str,
        site_name: str,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            f"Scraper '{scraper_name}' failed",
            site_name=site_name,
        )
        self.scraper_name = scraper_name
        self.original_error = original_error

    def __str__(self) -> str:
        base = f"ScraperError | scraper={self.scraper_name} | site={self.site_name}"
        if self.original_error:
            base += f" | cause={type(self.original_error).__name__}: {self.original_error}"
        return base


class ConfigurationError(OSINTError):
    """
    Lỗi cấu hình — missing .env, invalid config value, path traversal attempt.

    Raise khi:
      - API key missing
      - Path traversal detected trong input
      - Configuration.ini không đọc được
    """

    def __init__(self, message: str, field_name: str = "") -> None:
        super().__init__(message)
        self.field_name = field_name

    def __str__(self) -> str:
        if self.field_name:
            return f"ConfigurationError | field={self.field_name} | {self.message}"
        return f"ConfigurationError | {self.message}"


class SiteCheckError(OSINTError):
    """
    Generic error khi kiểm tra một site không thể phân loại chính xác.

    Dùng khi exception không thuộc TargetSiteTimeout, ProxyDeadError,
    hay RateLimitExceeded — catchall cho các lỗi network/parse khác.

    Raise khi:
      - Unexpected aiohttp exception
      - Response body parse error
      - Unexpected HTTP status (không phải 200/404/429/403)

    Story 2.4 — Custom Exception Classes, Epic 2.
    """

    def __init__(
        self,
        site_name: str,
        url: str,
        error_type: str,
        status_code: Optional[int] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        msg = f"Site check failed [{error_type}]"
        if status_code is not None:
            msg += f" HTTP {status_code}"
        super().__init__(msg, site_name=site_name, url=url)
        self.error_type = error_type
        self.status_code = status_code
        self.original_error = original_error

    def __str__(self) -> str:
        base = (
            f"SiteCheckError | site={self.site_name} | url={self.url} "
            f"| type={self.error_type}"
        )
        if self.status_code is not None:
            base += f" | http={self.status_code}"
        if self.original_error:
            base += f" | cause={type(self.original_error).__name__}: {self.original_error}"
        return base
