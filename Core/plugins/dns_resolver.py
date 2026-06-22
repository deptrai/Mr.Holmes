"""
Core/plugins/dns_resolver.py

Story 9.17-ext — DNS Resolver Plugin.

Resolves DOMAIN targets to IP addresses using asyncio DNS lookup.
Acts as a bridge between DOMAIN clues (from LeakLookup/Shodan) and
IP-based plugins (Shodan), enabling full DOMAIN → IP → Shodan pipeline.

Stage 3: runs alongside Shodan/Numverify on discovered DOMAIN clues.
"""
from __future__ import annotations

import asyncio
import logging
import socket

from Core.plugins.base import IntelligencePlugin, PluginResult

logger = logging.getLogger(__name__)

# Common CDN/shared-hosting IPs that produce noisy Shodan results — skip them
_CDN_PREFIXES = (
    "104.16.", "104.17.", "104.18.", "104.19.", "104.20.", "104.21.",  # Cloudflare
    "172.64.", "172.65.", "172.66.", "172.67.",                         # Cloudflare
    "151.101.",                                                          # Fastly
    "13.107.", "40.76.",                                                 # Microsoft CDN
)


class DNSResolverPlugin(IntelligencePlugin):
    """
    Resolves DOMAIN → IP(s) for downstream Shodan enrichment.

    stage = 3  — runs on DOMAIN clues discovered by Stage 2 plugins
    tos_risk = "safe"  — passive DNS lookup, no scraping
    """

    name: str = "DNSResolver"
    requires_api_key: bool = False
    stage: int = 1   # Stage 1 so it runs inside RecursiveProfiler BFS on discovered DOMAINs
    tos_risk: str = "safe"

    def __init__(self, api_key: str = "") -> None:
        pass  # no API key needed

    async def check(self, target: str, target_type: str) -> PluginResult:
        """
        Resolve a DOMAIN to its IP address(es).

        Args:
            target: Domain name to resolve (e.g. "example.com").
            target_type: Must be "DOMAIN".

        Returns:
            PluginResult with resolved IPs, or failure on DNS error.
        """
        if target_type.upper() != "DOMAIN":
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"DNSResolver only supports DOMAIN targets, got {target_type}",
            )

        # Strip trailing dot, lowercase
        domain = target.strip().rstrip(".").lower()
        if not domain or "." not in domain:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Invalid domain: {target!r}",
            )

        try:
            loop = asyncio.get_running_loop()
            # Resolve A records via getaddrinfo (works cross-platform)
            infos = await loop.getaddrinfo(
                domain, None,
                family=socket.AF_INET,   # IPv4 only — Shodan works best with IPv4
                type=socket.SOCK_STREAM,
            )
        except socket.gaierror as exc:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"DNS resolution failed for {domain}: {exc}",
            )
        except Exception as exc:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"DNSResolver error for {domain}: {exc}",
            )

        # Extract unique IPs, filter CDN noise
        seen: set[str] = set()
        ips: list[str] = []
        for info in infos:
            ip = info[4][0]
            if ip not in seen:
                seen.add(ip)
                if not any(ip.startswith(pfx) for pfx in _CDN_PREFIXES):
                    ips.append(ip)

        if not ips:
            # All resolved to CDN IPs — return them anyway but flag
            ips = list({info[4][0] for info in infos})
            cdn_note = True
        else:
            cdn_note = False

        logger.debug("DNSResolver: %s → %s", domain, ips)

        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={
                "domain": domain,
                "ips": ips,
                "cdn_note": cdn_note,
                "data_found": len(ips) > 0,
            },
        )

    def extract_clues(self, result: PluginResult) -> list[tuple[str, str]]:
        """Emit each resolved IP as an IP clue for Shodan to pick up."""
        if not result.is_success or not result.data:
            return []
        return [(ip, "IP") for ip in result.data.get("ips", [])]
