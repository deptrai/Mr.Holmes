"""
tests/plugins/test_searxng.py

Story 7.6 — Unit tests for SearxngPlugin.

Tests use a fixed custom_url via monkeypatch to ensure deterministic
HTTP mocking (the plugin rotates random public nodes otherwise).
"""
from __future__ import annotations

import asyncio
import os
import re

import pytest
from aioresponses import aioresponses

from Core.plugins.searxng import SearxngPlugin
from Core.plugins.base import PluginResult


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
# Helpers
# ---------------------------------------------------------------------------

def _make_plugin_with_custom_url(monkeypatch):
    """Create a SearxngPlugin that uses a deterministic custom URL for mocking."""
    monkeypatch.setenv("MH_SEARXNG_URL", CUSTOM_SEARX_URL)
    return SearxngPlugin()


# ---------------------------------------------------------------------------
# AC1, AC2, AC3: Initialization & Fallbacks
# ---------------------------------------------------------------------------

def test_searxng_init_default():
    """Missing env var → custom_url is empty, plugin uses public fallback nodes."""
    if "MH_SEARXNG_URL" in os.environ:
        del os.environ["MH_SEARXNG_URL"]

    plugin = SearxngPlugin()
    assert plugin.custom_url == ""
    assert plugin.requires_api_key is False
    assert plugin.name == "SearxngOSINT"


def test_searxng_init_custom_env(monkeypatch):
    """Custom env var sets custom_url."""
    monkeypatch.setenv("MH_SEARXNG_URL", CUSTOM_SEARX_URL)
    plugin = SearxngPlugin()
    assert plugin.custom_url == CUSTOM_SEARX_URL


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
    """Target types map out to OSINT Dorking strings."""
    plugin = SearxngPlugin()

    q1 = plugin._build_query("admin@test.com", "EMAIL")
    assert '"admin@test.com"' in q1
    assert "password OR leak" in q1

    q2 = plugin._build_query("johndoe", "USERNAME")
    assert '"johndoe"' in q2
    assert "password OR leak" in q2

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
async def test_searxng_found_results(monkeypatch):
    """Returns successful result mapping URLs and titles."""
    plugin = _make_plugin_with_custom_url(monkeypatch)

    with aioresponses() as mock:
        pattern = re.compile(r"^https://my-searx\.example\.com/search\b.*")
        mock.get(pattern, status=200, payload=SUCCESS_RESPONSE)
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
    assert meta["searxng_node"] == CUSTOM_SEARX_URL
    assert '"admin@test.com" password' in meta["query_used"]


@pytest.mark.asyncio
async def test_searxng_empty_results(monkeypatch):
    """Returns success but data_found=False when no entries exist."""
    plugin = _make_plugin_with_custom_url(monkeypatch)

    with aioresponses() as mock:
        pattern = re.compile(r"^https://my-searx\.example\.com/search\b.*")
        mock.get(pattern, status=200, payload=EMPTY_RESPONSE)
        result = await plugin.check("admin@test.com", "EMAIL")

    assert result.is_success is True
    assert result.data["data_found"] is False
    assert result.data["osint_urls"] == []


@pytest.mark.asyncio
async def test_searxng_rate_limit_http_429(monkeypatch):
    """HTTP 429 on custom URL → falls through to public nodes → all fail → exhausted error."""
    plugin = _make_plugin_with_custom_url(monkeypatch)

    with aioresponses() as mock:
        # Mock custom URL with 429
        pattern = re.compile(r"^https://my-searx\.example\.com/search\b.*")
        mock.get(pattern, status=429)
        # Mock all public fallback nodes with 429 too
        for node in SearxngPlugin.FALLBACK_NODES:
            escaped = re.escape(node)
            mock.get(re.compile(rf"^{escaped}\b.*"), status=429)
        result = await plugin.check("admin@test.com", "EMAIL")

    assert result.is_success is False
    assert "429" in result.error_message


@pytest.mark.asyncio
async def test_searxng_server_error(monkeypatch):
    """HTTP 503 on all nodes + DDG unavailable → exhausted error."""
    plugin = _make_plugin_with_custom_url(monkeypatch)

    # Patch DDG fallback so it raises an exception (simulates DDG unavailable)
    monkeypatch.setattr(
        "Core.plugins.searxng.DDGS",
        lambda: (_ for _ in ()).throw(Exception("DDG unavailable")),
        raising=False,
    )

    with aioresponses() as mock:
        pattern = re.compile(r"^https://my-searx\.example\.com/search\b.*")
        mock.get(pattern, status=503)
        for node in SearxngPlugin.FALLBACK_NODES:
            escaped = re.escape(node)
            mock.get(re.compile(rf"^{escaped}\b.*"), status=503)
        result = await plugin.check("admin@test.com", "EMAIL")

    assert result.is_success is False
    assert "503" in result.error_message


@pytest.mark.asyncio
async def test_searxng_timeout(monkeypatch):
    """Timeout on all nodes → exhausted error with 'Timeout' mention."""
    plugin = _make_plugin_with_custom_url(monkeypatch)

    with aioresponses() as mock:
        pattern = re.compile(r"^https://my-searx\.example\.com/search\b.*")
        mock.get(pattern, exception=asyncio.TimeoutError("Timeout"))
        for node in SearxngPlugin.FALLBACK_NODES:
            escaped = re.escape(node)
            mock.get(re.compile(rf"^{escaped}\b.*"), exception=asyncio.TimeoutError("Timeout"))
        result = await plugin.check("admin@test.com", "EMAIL")

    assert result.is_success is False
    assert "Timeout" in result.error_message


@pytest.mark.asyncio
async def test_searxng_custom_url_fail_falls_back_to_public(monkeypatch):
    """Custom URL fails but a public node succeeds → result is successful."""
    plugin = _make_plugin_with_custom_url(monkeypatch)

    with aioresponses() as mock:
        # Custom URL fails
        pattern = re.compile(r"^https://my-searx\.example\.com/search\b.*")
        mock.get(pattern, status=503)
        # All public nodes succeed
        for node in SearxngPlugin.FALLBACK_NODES:
            escaped = re.escape(node)
            mock.get(re.compile(rf"^{escaped}\b.*"), status=200, payload=SUCCESS_RESPONSE)
        result = await plugin.check("admin@test.com", "EMAIL")

    assert result.is_success is True
    assert result.data["data_found"] is True
