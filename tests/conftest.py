"""
tests/conftest.py

Shared pytest fixtures cho Mr.Holmes test suite.

Story 4.1 — Setup pytest + mock-based HTTP Framework, Epic 4.

Provides:
    site_config_factory  — factory fixture để tạo SiteConfig cho bất kỳ strategy nào
    mock_session         — mock aiohttp.ClientSession fixture cho HTTP mocking (AC3)
    status_code_site     — preconfigured site dùng Status-Code strategy
    message_site         — preconfigured site dùng Message strategy
    response_url_site    — preconfigured site dùng Response-Url strategy

Note: Migrated from aioresponses to unittest.mock-based approach because
aioresponses is incompatible with aiohttp 3.11+ (ClientResponse.__init__
requires stream_writer argument that aioresponses doesn't provide).
"""
from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock

import pytest

from Core.engine.async_search import SiteConfig
from Core.models.scan_result import ErrorStrategy


# ---------------------------------------------------------------------------
# AC3 — Mock-based HTTP mocking helpers (replaces aioresponses)
# ---------------------------------------------------------------------------

class MockResponse:
    """Mock aiohttp response that works as an async context manager."""

    def __init__(
        self,
        status: int = 200,
        body: bytes | str = b"",
        payload: dict | list | None = None,
        headers: dict | None = None,
        url: str | None = None,
        exception: Exception | None = None,
    ):
        self.status = status
        self._body = body
        self._payload = payload
        self.headers = headers or {}
        self.url = url or "https://example.com/testuser"
        self._exception = exception

    async def __aenter__(self):
        if self._exception is not None:
            raise self._exception
        return self

    async def __aexit__(self, *args):
        return False

    async def text(self, errors: str = "replace"):
        if isinstance(self._body, bytes):
            return self._body.decode(errors=errors)
        return str(self._body) if self._body else ""

    async def json(self):
        if self._payload is not None:
            return self._payload
        if isinstance(self._body, (bytes, str)):
            import json
            raw = self._body.decode() if isinstance(self._body, bytes) else self._body
            return json.loads(raw) if raw else {}
        return {}

    def raise_for_status(self):
        """Mimic aiohttp's raise_for_status — no-op for successful statuses."""
        pass


def make_mock_response(
    status: int = 200,
    body: bytes | str = b"",
    payload: dict | list | None = None,
    headers: dict | None = None,
    url: str | None = None,
    exception: Exception | None = None,
) -> MockResponse:
    """Build a mock aiohttp response (async context manager)."""
    return MockResponse(
        status=status,
        body=body,
        payload=payload,
        headers=headers,
        url=url,
        exception=exception,
    )


def make_mock_session(responses) -> MagicMock:
    """
    Build a mock aiohttp.ClientSession whose .get()/.post() return mock
    responses in order.  ``responses`` may be a single MockResponse or a list.
    """
    if not isinstance(responses, list):
        responses = [responses]
    call_count = [0]

    def _next(*args, **kwargs):
        idx = min(call_count[0], len(responses) - 1)
        call_count[0] += 1
        return responses[idx]

    mock_session = MagicMock()
    mock_session.get = MagicMock(side_effect=_next)
    mock_session.post = MagicMock(side_effect=_next)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_session.closed = False
    return mock_session


class _MockAiohttpRegistry:
    """
    Aioresponses-compatible registry that maps URLs/patterns to responses.

    Used by the ``mock_session`` fixture: tests call ``mock_session.get(url,
    status=200, ...)`` to register a response, then use the session directly.
    """

    def __init__(self):
        self._responses: list[tuple, MockResponse] = []
        self._call_count = 0

    def get(self, url, **kwargs):
        resp = make_mock_response(
            status=kwargs.get("status", 200),
            body=kwargs.get("body", b""),
            payload=kwargs.get("payload"),
            headers=kwargs.get("headers", {}),
            url=str(url) if not hasattr(url, "match") else None,
            exception=kwargs.get("exception"),
        )
        self._responses.append((url, resp))
        return self

    def post(self, url, **kwargs):
        return self.get(url, **kwargs)

    def _match(self, request_url: str) -> MockResponse | None:
        for registered_url, resp in self._responses:
            if hasattr(registered_url, "match"):
                if registered_url.match(request_url):
                    return resp
            elif registered_url == request_url:
                return resp
        return None

    def build_session(self) -> MagicMock:
        """Build a mock session that dispatches to registered responses."""
        registry = self

        def _get(*args, **kwargs):
            url = kwargs.get("url") or (args[0] if args else "")
            resp = registry._match(str(url))
            if resp is None:
                # Fallback: return first registered response or 404
                if registry._responses:
                    return registry._responses[0][1]
                return make_mock_response(status=404)
            return resp

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=_get)
        mock_session.post = MagicMock(side_effect=_get)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.closed = False
        return mock_session


@pytest.fixture
def mock_aiohttp():
    """
    Fixture cung cấp mock-based HTTP registry (replaces aioresponses).

    Usage:
        async def test_something(mock_aiohttp):
            mock_aiohttp.get("https://example.com/user", status=200)
            session = mock_aiohttp.build_session()
            # pass session to code under test
    """
    return _MockAiohttpRegistry()


@pytest.fixture
def mock_session():
    """
    Fixture cung cấp một mock aiohttp session trống cho HTTP mocking.

    Usage:
        async def test_something(mock_session):
            mock_session.get.return_value = make_mock_response(status=200, body=b"...")
            # pass mock_session to search_site() directly
    """
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.closed = False
    return session


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
