"""
tests/conftest.py

Shared pytest fixtures cho Mr.Holmes test suite.

Story 4.1 — Setup pytest + aioresponses Framework, Epic 4.

Provides:
    site_config_factory  — factory fixture để tạo SiteConfig cho bất kỳ strategy nào
    mock_aiohttp       — aioresponses context manager fixture cho HTTP mocking (AC3)
    status_code_site     — preconfigured site dùng Status-Code strategy
    message_site         — preconfigured site dùng Message strategy
    response_url_site    — preconfigured site dùng Response-Url strategy
"""
from __future__ import annotations

import pytest
from aioresponses import aioresponses as _aioresponses

from Core.engine.async_search import SiteConfig
from Core.models.scan_result import ErrorStrategy


# ---------------------------------------------------------------------------
# AC3 — aioresponses HTTP mocking fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_aiohttp():
    """
    Fixture cung cấp aioresponses context để mock HTTP calls.

    Usage:
        async def test_something(mock_aiohttp):
            mock_aiohttp.get("https://example.com/user", status=200)
            ...
    """
    with _aioresponses() as m:
        yield m


# ---------------------------------------------------------------------------
# AC3 — SiteConfig factory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def site_config_factory():
    """
    Factory fixture để tạo SiteConfig với custom params.

    Usage:
        def test_foo(site_config_factory):
            site = site_config_factory(name="GitHub", strategy=ErrorStrategy.STATUS_CODE)
    """
    def _factory(
        name: str = "TestSite",
        url_template: str = "https://example.com/{}",
        display_url: str = "https://example.com/testuser",
        strategy: ErrorStrategy = ErrorStrategy.STATUS_CODE,
        error_text: str = "",
        response_url: str = "",
        tags: list[str] | None = None,
        is_scrapable: bool = False,
    ) -> SiteConfig:
        return SiteConfig(
            name=name,
            url_template=url_template,
            display_url=display_url,
            error_strategy=strategy,
            error_text=error_text,
            response_url=response_url,
            tags=tags or ["Test"],
            is_scrapable=is_scrapable,
        )
    return _factory


@pytest.fixture
def status_code_site(site_config_factory):
    """Pre-configured SiteConfig với Status-Code strategy."""
    return site_config_factory(
        name="StatusCodeSite",
        strategy=ErrorStrategy.STATUS_CODE,
    )


@pytest.fixture
def message_site(site_config_factory):
    """Pre-configured SiteConfig với Message strategy."""
    return site_config_factory(
        name="MessageSite",
        strategy=ErrorStrategy.MESSAGE,
        error_text="User not found",
    )


@pytest.fixture
def response_url_site(site_config_factory):
    """Pre-configured SiteConfig với Response-Url strategy."""
    return site_config_factory(
        name="ResponseUrlSite",
        strategy=ErrorStrategy.RESPONSE_URL,
        response_url="https://example.com/404",
    )
