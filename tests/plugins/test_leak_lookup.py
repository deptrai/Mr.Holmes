"""
tests/plugins/test_leak_lookup.py

Story 7.5 — Unit tests for LeakLookupPlugin.
"""
from __future__ import annotations

import json
import pytest
from aioresponses import aioresponses

from Core.plugins.leak_lookup import LeakLookupPlugin
from Core.plugins.base import PluginResult


LEAK_LOOKUP_URL = "https://leak-lookup.com/api/search"

SUCCESS_RESPONSE = {
    "error": "false",
    "message": {
        "linkedin.com": [{"hash": "md5...", "salt": "..."}],
        "canva.com": [{"plaintext": "password123"}]
    }
}

NOT_FOUND_RESPONSE = {
    "error": "false",
    "message": "" # This is how leak-lookup typically returns "no results"
}

INVALID_KEY_RESPONSE = {
    "error": "true",
    "message": "Invalid API Key"
}

# ---------------------------------------------------------------------------
# AC1, AC2, AC3: Initialization & Types
# ---------------------------------------------------------------------------

def test_leak_lookup_init():
    """LeakLookup requires API key and sets right name."""
    plugin = LeakLookupPlugin(api_key="dummy_key")
    assert plugin.name == "LeakLookup"
    assert plugin.requires_api_key is True


@pytest.mark.asyncio
async def test_leak_lookup_no_api_key():
    """Without API key, returns is_success=False explicitly mentioning missing key."""
    plugin = LeakLookupPlugin(api_key="")
    result = await plugin.check("test@example.com", "EMAIL")

    assert result.is_success is False
    assert "MH_LEAKLOOKUP_API_KEY" in result.error_message


@pytest.mark.asyncio
async def test_leak_lookup_wrong_target_type():
    """Target type out of supported mapping returns is_success=False."""
    plugin = LeakLookupPlugin(api_key="valid")
    result = await plugin.check("+1234567890", "PHONE")

    assert result.is_success is False
    assert "only supports" in result.error_message.lower()


# ---------------------------------------------------------------------------
# AC4: API Interaction & Parsing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_leak_lookup_found_breaches():
    """Returns successful result mapping databases to vulnerabilities array."""
    plugin = LeakLookupPlugin(api_key="test_key")

    with aioresponses() as mock:
        mock.post(
            LEAK_LOOKUP_URL,
            status=200,
            payload=SUCCESS_RESPONSE,
        )
        result = await plugin.check("test@example.com", "EMAIL")

    assert isinstance(result, PluginResult)
    assert result.plugin_name == "LeakLookup"
    assert result.is_success is True
    assert result.data["data_found"] is True
    
    vulns = result.data["vulnerabilities"]
    assert len(vulns) == 2
    assert "linkedin.com" in vulns
    assert "canva.com" in vulns
    assert result.data["metadata"]["total_breaches"] == 2


@pytest.mark.asyncio
async def test_leak_lookup_not_found():
    """Returns success but data_found=False when no entries exist."""
    plugin = LeakLookupPlugin(api_key="test_key")

    with aioresponses() as mock:
        mock.post(
            LEAK_LOOKUP_URL,
            status=200,
            payload=NOT_FOUND_RESPONSE,
        )
        result = await plugin.check("test@example.com", "EMAIL")

    assert result.is_success is True
    assert result.data["data_found"] is False
    assert result.data["vulnerabilities"] == []


@pytest.mark.asyncio
async def test_leak_lookup_invalid_key():
    """Server returns 200 but JSON holds error='true' -> traps to 401 message."""
    plugin = LeakLookupPlugin(api_key="test_key")

    with aioresponses() as mock:
        mock.post(
            LEAK_LOOKUP_URL,
            status=200,
            payload=INVALID_KEY_RESPONSE,
        )
        result = await plugin.check("test@example.com", "EMAIL")

    assert result.is_success is False
    assert "401" in result.error_message
    assert "Invalid API Key" in result.error_message


@pytest.mark.asyncio
async def test_leak_lookup_rate_limit_http_429():
    """Catch conventional HTTP 429 server codes."""
    plugin = LeakLookupPlugin(api_key="test_key")

    with aioresponses() as mock:
        mock.post(LEAK_LOOKUP_URL, status=429)
        result = await plugin.check("test@example.com", "EMAIL")

    assert result.is_success is False
    assert "429" in result.error_message


# ---------------------------------------------------------------------------
# Rate Limiting Engine Check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_leak_lookup_rate_limit_throttle():
    """Ensure Lock and sleep enforcement spans 1.0 seconds."""
    import time
    plugin = LeakLookupPlugin(api_key="test_key")

    with aioresponses() as mock:
        mock.post(LEAK_LOOKUP_URL, status=200, payload=NOT_FOUND_RESPONSE)
        mock.post(LEAK_LOOKUP_URL, status=200, payload=NOT_FOUND_RESPONSE)

        t0 = time.monotonic()
        await plugin.check("test@example.com", "EMAIL")
        await plugin.check("test2@example.com", "EMAIL")
        elapsed = time.monotonic() - t0

    assert elapsed >= 1.0
