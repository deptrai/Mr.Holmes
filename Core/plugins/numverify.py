"""
Core/plugins/numverify.py

Story 9.8 — NumverifyPlugin: verify and enrich PHONE number targets via Numverify API.
Free tier: 100 lookups/month via HTTP (HTTPS requires paid plan).
"""
from __future__ import annotations

import logging
import os
import re
import unicodedata

import aiohttp

from Core.plugins.base import IntelligencePlugin, PluginResult, get_http_session

logger = logging.getLogger(__name__)

# Shortest valid phone number (E.164 shortest is ~7 digits including country code).
# Note: detect_seed_type() in autonomous_cli.py requires 9+ digits for auto-detection
# as PHONE — _MIN_PHONE_LEN=7 is only reachable via explicit target_type="PHONE".
_MIN_PHONE_LEN = 7
_HTTP_WARNING_ISSUED = False


class NumverifyPlugin(IntelligencePlugin):
    """
    Numverify phone validation plugin.
    stage=3 — runs after email/username discovery yields phone numbers.
    """

    stage: int = 3
    tos_risk: str = "safe"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key or os.getenv("MH_NUMVERIFY_API_KEY", "")

    @property
    def name(self) -> str:
        return "Numverify"

    @property
    def requires_api_key(self) -> bool:
        return True

    @staticmethod
    def _normalize_phone(phone: str) -> str:
        """Strip non-digit chars except a leading '+'. Return '' if result is too short."""
        # W7: Convert fullwidth/regional digits (e.g. ０-９) to ASCII
        phone = unicodedata.normalize("NFKC", phone.strip())
        # Strip all chars that aren't digits or '+' — this handles formats like (+84)...
        stripped = re.sub(r"[^\d+]", "", phone)
        # Only honour a leading '+'; any '+' in the middle is noise
        if stripped.startswith("+"):
            normalized = "+" + re.sub(r"[^\d]", "", stripped[1:])
        else:
            normalized = re.sub(r"[^\d]", "", stripped)
        return normalized if len(normalized) >= _MIN_PHONE_LEN else ""

    def normalize_target(self, target: str) -> str:
        """Normalize phone for cache key dedup — same number, different formats → same key."""
        return self._normalize_phone(target) or target

    def extract_clues(self, result: PluginResult) -> list[tuple[str, str]]:
        """Phone enrichment data (carrier, location) does not seed further BFS."""
        return []

    async def check(self, target: str, target_type: str) -> PluginResult:
        if target_type.upper() != "PHONE":
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Numverify only supports PHONE targets, got {target_type}",
            )

        if not self.api_key:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=(
                    "Numverify API Key missing. "
                    "Please configure MH_NUMVERIFY_API_KEY."
                ),
            )

        phone = self._normalize_phone(target)
        if not phone:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Phone number too short or invalid after normalization: {target!r}",
            )

        url = (
            f"http://apilayer.net/api/validate"
            f"?access_key={self.api_key}&number={phone}&format=1"
        )

        # W1: Warn once about plaintext HTTP (free tier limitation)
        global _HTTP_WARNING_ISSUED
        if not _HTTP_WARNING_ISSUED:
            logger.warning(
                "Numverify free tier uses HTTP (not HTTPS). "
                "API key and phone number are transmitted in cleartext."
            )
            _HTTP_WARNING_ISSUED = True

        try:
            async with get_http_session(self) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 429:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="429 Rate Limit Exceeded. Numverify free tier: 100 lookups/month.",
                        )

                    if response.status != 200:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=f"Numverify API Error: HTTP {response.status}",
                        )

                    data = await response.json()
                    if not isinstance(data, dict):
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=f"Numverify unexpected response type: {type(data).__name__}",
                        )
                    if data.get("success") is False:
                        err = data.get("error", {})
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=f"Numverify API error {err.get('code', '?')}: {err.get('info', 'unknown')}",
                        )
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "valid": data.get("valid", False),
                            "number": data.get("number", ""),
                            "local_format": data.get("local_format", ""),
                            "international_format": data.get("international_format", ""),
                            "country_prefix": data.get("country_prefix", ""),
                            "country_code": data.get("country_code", ""),
                            "country_name": data.get("country_name", ""),
                            "location": data.get("location", ""),
                            "carrier": data.get("carrier", ""),
                            "line_type": data.get("line_type", ""),
                        },
                    )

        except Exception as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Numverify Network/Parse Error: {str(e)}",
            )
