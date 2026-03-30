"""
tests/plugins/test_hibp.py

Story 7.2 — Unit tests for HIBPPlugin (HaveIBeenPwned integration).
All HTTP calls are mocked via aioresponses.
"""
from __future__ import annotations

import json
import pytest
from aioresponses import aioresponses

from Core.plugins.hibp import HIBPPlugin
from Core.plugins.base import PluginResult


HIBP_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/test@example.com"

SAMPLE_BREACHES = [
    {
        "Name": "Adobe",
        "BreachDate": "2013-10-04",
        "DataClasses": ["Email addresses", "Password hints", "Passwords", "Usernames"],
        "PwnCount": 152445165,
    },
    {
        "Name": "LinkedIn",
        "BreachDate": "2012-05-05",
        "DataClasses": ["Email addresses", "Passwords"],
        "PwnCount": 164611595,
    },
]


# ---------------------------------------------------------------------------
# AC1: HIBPPlugin implements IntelligencePlugin protocol
# ---------------------------------------------------------------------------

def test_hibp_plugin_name():
    """HIBPPlugin.name returns the expected identifier."""
    plugin = HIBPPlugin(api_key="dummy_key")
    assert plugin.name == "HaveIBeenPwned"


def test_hibp_plugin_requires_api_key():
    """HIBPPlugin.requires_api_key is True."""
    plugin = HIBPPlugin(api_key="dummy_key")
    assert plugin.requires_api_key is True


# ---------------------------------------------------------------------------
# AC2+AC3: API v3 integration + parse breach results
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hibp_check_found_breaches():
    """Returns PluginResult with breach count, names, dates, data classes."""
    plugin = HIBPPlugin(api_key="test_key_123")

    with aioresponses() as mock:
        mock.get(
            HIBP_URL,
            status=200,
            body=json.dumps(SAMPLE_BREACHES),
            headers={"Content-Type": "application/json"},
        )
        result = await plugin.check("test@example.com", "EMAIL")

    assert isinstance(result, PluginResult)
    assert result.plugin_name == "HaveIBeenPwned"
    assert result.is_success is True
    assert result.error_message is None

    # AC3: breach_count, breach_names, breach_dates, data_classes
    assert result.data["breach_count"] == 2
    assert "Adobe" in result.data["breach_names"]
    assert "LinkedIn" in result.data["breach_names"]
    assert "2013-10-04" in result.data["breach_dates"]
    assert "Email addresses" in result.data["data_classes"]


@pytest.mark.asyncio
async def test_hibp_check_no_breaches():
    """Returns is_success=True with breach_count=0 when email is clean (404)."""
    plugin = HIBPPlugin(api_key="test_key_123")

    with aioresponses() as mock:
        mock.get(HIBP_URL, status=404)
        result = await plugin.check("test@example.com", "EMAIL")

    assert result.is_success is True
    assert result.data["breach_count"] == 0
    assert result.data["breach_names"] == []


# ---------------------------------------------------------------------------
# AC4: Rate limit — 1 request per 1.5 seconds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hibp_rate_limit_applied():
    """Rate limiter waits at least 1.5s between consecutive calls."""
    import time
    plugin = HIBPPlugin(api_key="test_key")

    url1 = "https://haveibeenpwned.com/api/v3/breachedaccount/a@b.com"
    url2 = "https://haveibeenpwned.com/api/v3/breachedaccount/c@d.com"

    with aioresponses() as mock:
        mock.get(url1, status=404)
        mock.get(url2, status=404)

        t0 = time.monotonic()
        await plugin.check("a@b.com", "EMAIL")
        await plugin.check("c@d.com", "EMAIL")
        elapsed = time.monotonic() - t0

    # Should take at least 1.5s due to rate limiting
    assert elapsed >= 1.5


# ---------------------------------------------------------------------------
# AC5: Graceful handling when no API key configured
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_hibp_no_api_key_returns_failure():
    """Without an API key, returns is_success=False with descriptive error."""
    plugin = HIBPPlugin(api_key="")
    result = await plugin.check("test@example.com", "EMAIL")

    assert result.is_success is False
    assert result.plugin_name == "HaveIBeenPwned"
    assert "api key" in result.error_message.lower()


@pytest.mark.asyncio
async def test_hibp_unauthorized_401():
    """Invalid API key (401) returns is_success=False."""
    plugin = HIBPPlugin(api_key="invalid_key")

    with aioresponses() as mock:
        mock.get(HIBP_URL, status=401)
        result = await plugin.check("test@example.com", "EMAIL")

    assert result.is_success is False
    assert "401" in result.error_message or "unauthorized" in result.error_message.lower()


@pytest.mark.asyncio
async def test_hibp_rate_limited_429():
    """API rate limit hit (429) returns is_success=False."""
    plugin = HIBPPlugin(api_key="some_key")

    with aioresponses() as mock:
        mock.get(HIBP_URL, status=429)
        result = await plugin.check("test@example.com", "EMAIL")

    assert result.is_success is False
    assert "429" in result.error_message or "rate" in result.error_message.lower()


@pytest.mark.asyncio
async def test_hibp_network_error():
    """Network errors are caught and return is_success=False."""
    import aiohttp
    plugin = HIBPPlugin(api_key="some_key")

    with aioresponses() as mock:
        mock.get(HIBP_URL, exception=aiohttp.ClientConnectionError("connection refused"))
        result = await plugin.check("test@example.com", "EMAIL")

    assert result.is_success is False
    assert result.error_message is not None


@pytest.mark.asyncio
async def test_hibp_wrong_target_type():
    """Non-EMAIL target type returns is_success=False without making API call."""
    plugin = HIBPPlugin(api_key="some_key")
    result = await plugin.check("192.168.1.1", "IP")

    assert result.is_success is False
    assert "email" in result.error_message.lower()
