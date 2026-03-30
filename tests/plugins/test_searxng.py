"""
tests/plugins/test_searxng.py

Story 7.6 — Unit tests for SearxngPlugin.
"""
from __future__ import annotations

import os
import pytest
from aioresponses import aioresponses

from Core.plugins.searxng import SearxngPlugin
from Core.plugins.base import PluginResult


DEFAULT_SEARX_URL = "https://searx.be/search"
CUSTOM_SEARX_URL = "https://my-searx.example.com/search"

SUCCESS_RESPONSE = {
    "query": "test query",
    "number_of_results": 2,
    "results": [
        {"url": "https://example.com/leak1", "title": "Leak 1"},
        {"url": "https://example.com/leak2", "title": "Leak 2"}
    ]
}

EMPTY_RESPONSE = {
    "query": "test query",
    "number_of_results": 0,
    "results": []
}

# ---------------------------------------------------------------------------
# AC1, AC2, AC3: Initialization & Fallbacks
# ---------------------------------------------------------------------------

def test_searxng_init_default():
    """Missing env var gracefully falls back to https://searx.be/search"""
    # ensure clean env
    if "MH_SEARXNG_URL" in os.environ:
        del os.environ["MH_SEARXNG_URL"]
        
    plugin = SearxngPlugin()
    assert plugin.base_url == DEFAULT_SEARX_URL
    assert plugin.requires_api_key is False
    assert plugin.name == "SearxngOSINT"

def test_searxng_init_custom_env(monkeypatch):
    """Custom env var overrides the default URL"""
    monkeypatch.setenv("MH_SEARXNG_URL", CUSTOM_SEARX_URL)
    plugin = SearxngPlugin()
    assert plugin.base_url == CUSTOM_SEARX_URL


@pytest.mark.asyncio
async def test_searxng_wrong_target_type():
    """Target type out of supported mapping returns is_success=False."""
    plugin = SearxngPlugin()
    result = await plugin.check("+1234567890", "PHONE")

    assert result.is_success is False
    assert "only supports" in result.error_message.lower()


# ---------------------------------------------------------------------------
# AC5: Multi-target Formatting
# ---------------------------------------------------------------------------

def test_searxng_query_builder():
    """Target types map out to OSINT Dorking strings"""
    plugin = SearxngPlugin()
    
    # EMAIL / USERNAME -> password OR leak OR dump
    q1 = plugin._build_query("admin@test.com", "EMAIL")
    assert '"admin@test.com"' in q1
    assert "password OR leak" in q1
    
    q2 = plugin._build_query("johndoe", "USERNAME")
    assert '"johndoe"' in q2
    assert "password OR leak" in q2
    
    # IP / DOMAIN -> vulnerability OR exploit
    q3 = plugin._build_query("1.1.1.1", "IP")
    assert '"1.1.1.1"' in q3
    assert "vulnerability OR exploit" in q3
    
    q4 = plugin._build_query("example.com", "DOMAIN")
    assert '"example.com"' in q4
    assert "vulnerability OR exploit" in q4


# ---------------------------------------------------------------------------
# AC4: Payload Orchestration & Error Handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_searxng_found_results():
    """Returns successful result mapping URLs and titles."""
    plugin = SearxngPlugin()

    with aioresponses() as mock:
        # Note: aioresponses by default matches exactly, but since params are variable,
        # we can match just the base URL by ignoring querystrings if we don't compile regex.
        # But we'll use a regex target or match the exact pattern.
        import re
        pattern = re.compile(rf"^{DEFAULT_SEARX_URL}\?.*")
        mock.get(
            pattern,
            status=200,
            payload=SUCCESS_RESPONSE,
        )
        result = await plugin.check("admin@test.com", "EMAIL")

    assert isinstance(result, PluginResult)
    assert result.plugin_name == "SearxngOSINT"
    assert result.is_success is True
    assert result.data["data_found"] is True
    
    urls = result.data["osint_urls"]
    assert len(urls) == 2
    assert urls[0]["url"] == "https://example.com/leak1"
    assert urls[0]["title"] == "Leak 1"
    
    meta = result.data["metadata"]
    assert meta["total_clues"] == 2
    assert meta["searxng_node"] == DEFAULT_SEARX_URL
    assert '"admin@test.com" password' in meta["query_used"]


@pytest.mark.asyncio
async def test_searxng_empty_results():
    """Returns success but data_found=False when no entries exist."""
    plugin = SearxngPlugin()

    with aioresponses() as mock:
        import re
        pattern = re.compile(rf"^{DEFAULT_SEARX_URL}\?.*")
        mock.get(
            pattern,
            status=200,
            payload=EMPTY_RESPONSE,
        )
        result = await plugin.check("admin@test.com", "EMAIL")

    assert result.is_success is True
    assert result.data["data_found"] is False
    assert result.data["osint_urls"] == []


@pytest.mark.asyncio
async def test_searxng_rate_limit_http_429():
    """Catch conventional HTTP 429 server codes."""
    plugin = SearxngPlugin()

    with aioresponses() as mock:
        import re
        pattern = re.compile(rf"^{DEFAULT_SEARX_URL}\?.*")
        mock.get(pattern, status=429)
        result = await plugin.check("admin@test.com", "EMAIL")

    assert result.is_success is False
    assert "429" in result.error_message
    assert "MH_SEARXNG_URL" in result.error_message


@pytest.mark.asyncio
async def test_searxng_server_error():
    """Catch 500/404 server errors."""
    plugin = SearxngPlugin()

    with aioresponses() as mock:
        import re
        pattern = re.compile(rf"^{DEFAULT_SEARX_URL}\?.*")
        mock.get(pattern, status=503)
        result = await plugin.check("admin@test.com", "EMAIL")

    assert result.is_success is False
    assert "HTTP 503" in result.error_message


@pytest.mark.asyncio
async def test_searxng_timeout():
    """Catch asyncio.TimeoutError."""
    plugin = SearxngPlugin()

    with aioresponses() as mock:
        import asyncio
        import re
        pattern = re.compile(rf"^{DEFAULT_SEARX_URL}\?.*")
        mock.get(pattern, exception=asyncio.TimeoutError("Timeout"))
        result = await plugin.check("admin@test.com", "EMAIL")

    assert result.is_success is False
    assert "timed out" in result.error_message
