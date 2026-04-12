"""
tests/plugins/test_shodan.py

Story 7.3 — Unit tests for ShodanPlugin (Shodan API integration).
"""
from __future__ import annotations

import json
import pytest
from aioresponses import aioresponses

from Core.plugins.shodan import ShodanPlugin
from Core.plugins.base import PluginResult


SHODAN_URL = "https://api.shodan.io/shodan/host/8.8.8.8?key=test_key_123"

SAMPLE_SHODAN_RESPONSE = {
    "region_code": "CA",
    "ip": 134744072,
    "postal_code": "94043",
    "country_code": "US",
    "city": "Mountain View",
    "dma_code": 807,
    "last_update": "2023-10-04T08:49:35.190817",
    "latitude": 37.4056,
    "tags": ["cloud"],
    "area_code": None,
    "country_name": "United States",
    "hostnames": ["dns.google"],
    "org": "Google LLC",
    "data": [
        {
            "port": 53,
            "banner": "DNS Server",
            "vulns": ["CVE-1999-0001", "CVE-2015-0235"]
        },
        {
            "port": 443,
            "banner": "HTTPS Server",
            "vulns": {"CVE-2015-0235": {"cvss": 7.5}, "CVE-2020-1234": {"cvss": 9.8}}
        }
    ],
    "isp": "Google LLC",
    "longitude": -122.0775,
    "ports": [53, 443],
    "os": "Linux"
}


# ---------------------------------------------------------------------------
# AC1: ShodanPlugin implements IntelligencePlugin
# ---------------------------------------------------------------------------

def test_shodan_plugin_name():
    """ShodanPlugin.name returns the expected identifier."""
    plugin = ShodanPlugin(api_key="dummy_key")
    assert plugin.name == "Shodan"


def test_shodan_plugin_requires_api_key():
    """ShodanPlugin.requires_api_key is True."""
    plugin = ShodanPlugin(api_key="dummy_key")
    assert plugin.requires_api_key is True


# ---------------------------------------------------------------------------
# AC2+AC3+AC5: API integration + Open ports + Vulnerabilities
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shodan_check_valid_ip():
    """Returns PluginResult with open ports, hostnames, org, isp and CVEs."""
    plugin = ShodanPlugin(api_key="test_key_123")

    with aioresponses() as mock:
        mock.get(
            SHODAN_URL,
            status=200,
            body=json.dumps(SAMPLE_SHODAN_RESPONSE),
            headers={"Content-Type": "application/json"},
        )
        result = await plugin.check("8.8.8.8", "IP")

    assert isinstance(result, PluginResult)
    assert result.plugin_name == "Shodan"
    assert result.is_success is True
    assert result.data["data_found"] is True

    # Check extracted data
    assert result.data["ports"] == [53, 443]
    assert result.data["hostnames"] == ["dns.google"]
    assert result.data["org"] == "Google LLC"
    assert result.data["isp"] == "Google LLC"
    
    # Check deduplicated CVEs
    vulns = result.data["vulnerabilities"]
    assert len(vulns) == 3
    assert "CVE-1999-0001" in vulns
    assert "CVE-2015-0235" in vulns
    assert "CVE-2020-1234" in vulns
    
    # Check location data
    assert result.data["location"]["city"] == "Mountain View"
    assert result.data["location"]["country"] == "United States"
    assert result.data["location"]["os"] == "Linux"


@pytest.mark.asyncio
async def test_shodan_check_not_found():
    """Returns data_found=False when IP is not in Shodan (404)."""
    plugin = ShodanPlugin(api_key="test_key_123")

    with aioresponses() as mock:
        mock.get(SHODAN_URL, status=404)
        result = await plugin.check("8.8.8.8", "IP")

    assert result.is_success is True
    assert result.data["data_found"] is False
    assert result.data["ports"] == []


# ---------------------------------------------------------------------------
# Edge Cases & Rate Limit
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_shodan_wrong_target_type():
    """Non-IP target type returns is_success=False without API call."""
    plugin = ShodanPlugin(api_key="valid")
    result = await plugin.check("test@example.com", "EMAIL")

    assert result.is_success is False
    assert "ip" in result.error_message.lower()


@pytest.mark.asyncio
async def test_shodan_no_api_key():
    """Without API key, returns is_success=False."""
    plugin = ShodanPlugin(api_key="")
    result = await plugin.check("8.8.8.8", "IP")

    assert result.is_success is False
    assert "api key" in result.error_message.lower()


@pytest.mark.asyncio
async def test_shodan_rate_limited_429():
    """API rate limit hit (429) returns is_success=False."""
    plugin = ShodanPlugin(api_key="test_key_123")

    with aioresponses() as mock:
        mock.get(SHODAN_URL, status=429)
        result = await plugin.check("8.8.8.8", "IP")

    assert result.is_success is False
    assert "429" in result.error_message or "rate limit" in result.error_message.lower()


@pytest.mark.asyncio
async def test_shodan_unauthorized_401():
    """Invalid API key (401) returns is_success=False."""
    plugin = ShodanPlugin(api_key="test_key_123")

    with aioresponses() as mock:
        mock.get(SHODAN_URL, status=401)
        result = await plugin.check("8.8.8.8", "IP")

    assert result.is_success is False
    assert "401" in result.error_message or "unauthorized" in result.error_message.lower()


@pytest.mark.asyncio
async def test_shodan_rate_limit_applied():
    """Rate limiter waits at least 1.0s between consecutive calls."""
    import time
    plugin = ShodanPlugin(api_key="test_key")

    url1 = "https://api.shodan.io/shodan/host/1.1.1.1?key=test_key"
    url2 = "https://api.shodan.io/shodan/host/8.8.4.4?key=test_key"

    with aioresponses() as mock:
        mock.get(url1, status=404)
        mock.get(url2, status=404)

        t0 = time.monotonic()
        await plugin.check("1.1.1.1", "IP")
        await plugin.check("8.8.4.4", "IP")
        elapsed = time.monotonic() - t0

    # Should take at least 1.0s due to rate limiting
    assert elapsed >= 1.0
