"""Core/plugins/vn_domain.py — Vietnam domain WHOIS + DNS enrichment.

Combines multiple domain intelligence sources:
1. WHOIS lookup (registration info: owner, registrar, dates)
2. DNS resolution (A, AAAA, MX, NS, TXT records)
3. Subdomain discovery (via crt.sh certificate transparency)
4. .vn TLD specific handling (VNNIC registry)

v2.1: Unified domain enrichment with RateLimiter (AD-12).
"""
from __future__ import annotations

import asyncio
import logging
import re
import socket
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

_DOMAIN_REGEX = re.compile(r'^([a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$')


class VnDomainPlugin:
    """Domain WHOIS + DNS + subdomain enrichment."""

    @property
    def name(self) -> str:
        return "VnDomain"

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def stage(self) -> int:
        return 1

    @property
    def target_types(self) -> list[str]:
        return ["domain", "DOMAIN", "url", "URL"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("domain", "DOMAIN", "url", "URL"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"VnDomain supports domain/url, got {target_type}",
            )

        # Extract domain from URL if needed
        domain = target.strip().lower()
        if target_type in ("url", "URL"):
            domain = re.sub(r'^https?://', '', domain)
            domain = domain.split("/")[0]
            domain = domain.split(":")[0]  # strip port

        if not _DOMAIN_REGEX.match(domain):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Invalid domain: {target}",
            )

        result_data: dict[str, Any] = {
            "domain": domain,
            "is_vn_tld": domain.endswith(".vn"),
            "data_found": True,
            "source": "vn_domain",
        }

        # Method 1: DNS resolution
        dns_result = await self._dns_lookup(domain)
        result_data["dns"] = dns_result

        # Method 2: WHOIS lookup
        whois_result = await self._whois_lookup(domain)
        if whois_result:
            result_data["whois"] = whois_result

        # Method 3: Subdomain discovery via crt.sh
        subdomains = await self._crtsh_lookup(domain)
        if subdomains:
            result_data["subdomains"] = subdomains
            result_data["subdomain_count"] = len(subdomains)

        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data=result_data,
        )

    async def _dns_lookup(self, domain: str) -> dict:
        """Resolve DNS records (A, AAAA, MX, NS, TXT)."""
        loop = asyncio.get_event_loop()
        dns_data: dict[str, Any] = {}

        # A record (IPv4)
        try:
            infos = await loop.getaddrinfo(
                domain, None, family=socket.AF_INET, type=socket.SOCK_STREAM
            )
            dns_data["a_records"] = list({info[4][0] for info in infos})
        except Exception:
            dns_data["a_records"] = []

        # AAAA record (IPv6)
        try:
            infos = await loop.getaddrinfo(
                domain, None, family=socket.AF_INET6, type=socket.SOCK_STREAM
            )
            dns_data["aaaa_records"] = list({info[4][0] for info in infos})
        except Exception:
            dns_data["aaaa_records"] = []

        # MX record via subprocess (getaddrinfo doesn't support MX)
        try:
            proc = await asyncio.create_subprocess_exec(
                "dig", "+short", "MX", domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            mx_output = stdout.decode().strip()
            dns_data["mx_records"] = [
                line.strip() for line in mx_output.split("\n") if line.strip()
            ] if mx_output else []
        except Exception:
            dns_data["mx_records"] = []

        # NS record
        try:
            proc = await asyncio.create_subprocess_exec(
                "dig", "+short", "NS", domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            ns_output = stdout.decode().strip()
            dns_data["ns_records"] = [
                line.strip().rstrip(".") for line in ns_output.split("\n") if line.strip()
            ] if ns_output else []
        except Exception:
            dns_data["ns_records"] = []

        # TXT record
        try:
            proc = await asyncio.create_subprocess_exec(
                "dig", "+short", "TXT", domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            txt_output = stdout.decode().strip()
            dns_data["txt_records"] = [
                line.strip().strip('"') for line in txt_output.split("\n") if line.strip()
            ] if txt_output else []
        except Exception:
            dns_data["txt_records"] = []

        return dns_data

    async def _whois_lookup(self, domain: str) -> dict | None:
        """WHOIS lookup via subprocess."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "whois", domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            whois_text = stdout.decode(errors="replace")

            # Parse common WHOIS fields
            whois_data: dict[str, str] = {}

            # Common field patterns
            patterns = {
                "registrar": r"[Rr]egistrar:\s*(.+)",
                "creation_date": r"[Cc]reation\s*[Dd]ate:\s*(.+)",
                "expiration_date": r"[Rr]egistry\s*[Ee]xpiry\s*[Dd]ate:\s*(.+)",
                "updated_date": r"[Uu]pdated\s*[Dd]ate:\s*(.+)",
                "name_servers": r"[Nn]ame\s*[Ss]erver:\s*(.+)",
                "registrant": r"[Rr]egistrant\s*[Nn]ame:\s*(.+)",
                "registrant_email": r"[Rr]egistrant\s*[Ee]mail:\s*(.+)",
                "status": r"[Dd]omain\s*[Ss]tatus:\s*(.+)",
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, whois_text)
                if match:
                    whois_data[key] = match.group(1).strip()

            # .vn specific fields
            if domain.endswith(".vn"):
                vn_patterns = {
                    "owner": r"[Oo]wner:\s*(.+)",
                    "admin_contact": r"[Aa]dmin\s*[Cc]ontact:\s*(.+)",
                    "tech_contact": r"[Tt]ech\s*[Cc]ontact:\s*(.+)",
                }
                for key, pattern in vn_patterns.items():
                    match = re.search(pattern, whois_text)
                    if match:
                        whois_data[key] = match.group(1).strip()

            whois_data["raw_length"] = len(whois_text)
            return whois_data if whois_data else None

        except Exception as e:
            logger.warning("WHOIS lookup error: %s", e)
            return None

    async def _crtsh_lookup(self, domain: str) -> list[str]:
        """Discover subdomains via crt.sh certificate transparency logs."""
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("crt.sh", self.name)

        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://crt.sh/?q=%.{domain}&output=json"
                headers = {"User-Agent": "Mozilla/5.0 (compatible; MrHolmes/2.1)"}

                async with session.get(
                    url, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        subdomains: set[str] = set()
                        for entry in data:
                            name_value = entry.get("name_value", "")
                            for name in name_value.split("\n"):
                                name = name.strip().lower()
                                if name and domain in name and "*" not in name:
                                    subdomains.add(name)
                        return sorted(subdomains)[:50]  # Limit to 50
        except Exception as e:
            logger.warning("crt.sh lookup error: %s", e)

        return []
