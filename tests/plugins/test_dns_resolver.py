"""Tests for Core/plugins/dns_resolver.py"""
import asyncio
import socket
from unittest.mock import AsyncMock, patch

import pytest

from Core.plugins.dns_resolver import DNSResolverPlugin
from Core.plugins.base import PluginResult


@pytest.mark.asyncio
async def test_dns_resolver_wrong_type():
    """Non-DOMAIN target returns failure immediately."""
    plugin = DNSResolverPlugin()
    result = await plugin.check("1.2.3.4", "IP")
    assert result.is_success is False
    assert "DOMAIN" in result.error_message


@pytest.mark.asyncio
async def test_dns_resolver_invalid_domain():
    """Domain with no dot is rejected."""
    plugin = DNSResolverPlugin()
    result = await plugin.check("notadomain", "DOMAIN")
    assert result.is_success is False


@pytest.mark.asyncio
async def test_dns_resolver_success():
    """Successful DNS lookup returns IP clues."""
    plugin = DNSResolverPlugin()
    fake_infos = [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.2.3.4", 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("5.6.7.8", 0)),
    ]
    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo = AsyncMock(return_value=fake_infos)
        result = await plugin.check("example.com", "DOMAIN")

    assert result.is_success is True
    assert set(result.data["ips"]) == {"1.2.3.4", "5.6.7.8"}
    assert result.data["domain"] == "example.com"


@pytest.mark.asyncio
async def test_dns_resolver_gaierror():
    """DNS gaierror returns failure with error_message."""
    plugin = DNSResolverPlugin()
    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo = AsyncMock(
            side_effect=socket.gaierror("Name or service not known")
        )
        result = await plugin.check("nonexistent.invalid", "DOMAIN")

    assert result.is_success is False
    assert "DNS resolution failed" in result.error_message


@pytest.mark.asyncio
async def test_extract_clues_returns_ip_tuples():
    """extract_clues converts resolved IPs to (ip, 'IP') tuples."""
    plugin = DNSResolverPlugin()
    result = PluginResult(
        plugin_name="DNSResolver",
        is_success=True,
        data={"domain": "example.com", "ips": ["1.2.3.4", "5.6.7.8"], "data_found": True},
    )
    clues = plugin.extract_clues(result)
    assert ("1.2.3.4", "IP") in clues
    assert ("5.6.7.8", "IP") in clues


@pytest.mark.asyncio
async def test_extract_clues_empty_on_failure():
    """extract_clues returns [] on failed result."""
    plugin = DNSResolverPlugin()
    result = PluginResult(
        plugin_name="DNSResolver",
        is_success=False,
        data={},
        error_message="failed",
    )
    assert plugin.extract_clues(result) == []


@pytest.mark.asyncio
async def test_dns_resolver_filters_cdn_ips():
    """Cloudflare/CDN IPs are filtered out, non-CDN IPs are kept."""
    plugin = DNSResolverPlugin()
    # Mix: one Cloudflare IP (104.16.x) + one real IP
    fake_infos = [
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("104.16.1.1", 0)),  # Cloudflare
        (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("203.162.1.1", 0)),  # Real
    ]
    with patch("asyncio.get_running_loop") as mock_loop:
        mock_loop.return_value.getaddrinfo = AsyncMock(return_value=fake_infos)
        result = await plugin.check("somesite.com", "DOMAIN")

    assert result.is_success is True
    assert "203.162.1.1" in result.data["ips"]
    assert "104.16.1.1" not in result.data["ips"]
    assert result.data["cdn_note"] is False
