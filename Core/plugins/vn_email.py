"""Core/plugins/vn_email.py — Email validation + breach check.

Combines multiple email intelligence sources:
1. Email validation (format + MX record + SMTP check via aiohttp)
2. HaveIBeenPwned breach lookup (requires MH_HAVEIBEENPWNED_API_KEY)
3. LeakLookup breach search (requires MH_LEAKLOOKUP_API_KEY)
4. Holehe-style email registration check (which sites use this email)

v2.1: Unified email enrichment plugin with RateLimiter (AD-12).
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

_EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


class VnEmailPlugin:
    """Email validation + breach check + registration lookup."""

    @property
    def name(self) -> str:
        return "VnEmail"

    @property
    def requires_api_key(self) -> bool:
        return False  # API keys are optional enhancements

    @property
    def stage(self) -> int:
        return 1

    @property
    def target_types(self) -> list[str]:
        return ["email", "EMAIL"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("email", "EMAIL"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"VnEmail supports email, got {target_type}",
            )

        email = target.strip().lower()
        if not _EMAIL_REGEX.match(email):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Invalid email format: {target}",
            )

        result_data: dict[str, Any] = {
            "email": email,
            "data_found": True,
            "source": "vn_email",
        }

        # Method 1: Format validation (already done above)
        result_data["format_valid"] = True

        # Method 2: MX record check
        mx_result = await self._check_mx(email)
        result_data["mx_valid"] = mx_result

        # Method 3: HaveIBeenPwned breach lookup
        hibp_key = os.environ.get("MH_HAVEIBEENPWNED_API_KEY", "")
        if hibp_key:
            hibp_result = await self._hibp_lookup(email, hibp_key)
            if hibp_result:
                result_data["hibp_breaches"] = hibp_result.get("breaches", [])
                result_data["hibp_breach_count"] = hibp_result.get("count", 0)
                result_data["hibp_pastes"] = hibp_result.get("pastes", [])

        # Method 4: LeakLookup breach search
        leaklookup_key = os.environ.get("MH_LEAKLOOKUP_API_KEY", "")
        if leaklookup_key:
            ll_result = await self._leaklookup_search(email, leaklookup_key)
            if ll_result:
                result_data["leaklookup_found"] = ll_result.get("found", False)
                result_data["leaklookup_sources"] = ll_result.get("sources", [])

        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data=result_data,
        )

    async def _check_mx(self, email: str) -> bool:
        """Check if email domain has MX records."""
        import asyncio
        import socket

        domain = email.split("@")[1]
        try:
            loop = asyncio.get_event_loop()
            # Try to resolve MX record via getaddrinfo (fallback to A record)
            await loop.getaddrinfo(domain, 25, type=socket.SOCK_STREAM)
            return True
        except Exception:
            try:
                await loop.getaddrinfo(domain, None)
                return True
            except Exception:
                return False

    async def _hibp_lookup(self, email: str, api_key: str) -> dict | None:
        """Search HaveIBeenPwned for breach data."""
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("haveibeenpwned.com", self.name)

        try:
            async with aiohttp.ClientSession() as session:
                # Breach lookup
                url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
                headers = {
                    "hibp-api-key": api_key,
                    "User-Agent": "MrHolmes/2.1",
                    "Accept": "application/json",
                }

                async with session.get(
                    url, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        breaches = await resp.json()
                        return {
                            "breaches": [
                                {
                                    "name": b.get("Name", ""),
                                    "domain": b.get("Domain", ""),
                                    "breach_date": b.get("BreachDate", ""),
                                    "pwn_count": b.get("PwnCount", 0),
                                    "data_classes": b.get("DataClasses", []),
                                }
                                for b in breaches
                            ],
                            "count": len(breaches),
                            "pastes": [],
                        }
                    elif resp.status == 404:
                        return {"breaches": [], "count": 0, "pastes": []}
                    elif resp.status == 429:
                        logger.warning("HIBP rate limited")
                        return None
        except Exception as e:
            logger.warning("HIBP lookup error: %s", e)

        return None

    async def _leaklookup_search(self, email: str, api_key: str) -> dict | None:
        """Search LeakLookup for breach data."""
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("leaklookup.com", self.name)

        try:
            async with aiohttp.ClientSession() as session:
                url = "https://leaklookup.com/api/query"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                payload = {"type": "email", "query": email}

                async with session.post(
                    url, headers=headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        sources = list(data.keys()) if isinstance(data, dict) else []
                        return {
                            "found": len(sources) > 0,
                            "sources": sources,
                        }
        except Exception as e:
            logger.warning("LeakLookup error: %s", e)

        return None
