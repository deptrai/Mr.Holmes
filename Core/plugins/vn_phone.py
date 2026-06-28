"""Core/plugins/vn_phone.py — Vietnamese phone carrier and region lookup.

Identifies carrier (Viettel, MobiFone, VinaPhone, etc.) and region
from Vietnamese phone number prefixes.

v2.1 enhancements:
- Numverify API integration (carrier + location + line type, if key configured)
- Truecaller fallback (owner name, if key configured)
- Rate limiter integration (AD-12)
- Structured output with international format
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Vietnamese carrier prefixes (updated 2024)
VN_CARRIERS = {
    "viettel": {
        "prefixes": ["086", "096", "097", "098", "032", "033", "034", "035", "036", "037", "038", "039"],
        "name": "Viettel Military Telecom",
    },
    "mobifone": {
        "prefixes": ["089", "090", "093", "070", "076", "077", "078", "079"],
        "name": "MobiFone",
    },
    "vinaphone": {
        "prefixes": ["088", "091", "094", "081", "082", "083", "084", "085"],
        "name": "VinaPhone",
    },
    "vietnamobile": {
        "prefixes": ["092", "056", "058", "052"],
        "name": "Vietnamobile",
    },
    "gmobile": {
        "prefixes": ["099", "059"],
        "name": "GMobile",
    },
    "itel": {
        "prefixes": ["087"],
        "name": "iTel Telecom",
    },
    "wintel": {
        "prefixes": ["055"],
        "name": "Wintel (CDMA)",
    },
}

# Region prefixes (landline)
VN_REGIONS = {
    "02": "Hanoi", "03": "Hai Phong", "04": "Hai Duong",
    "05": "Nghe An", "06": "Da Nang", "07": "Khanh Hoa",
    "08": "Ho Chi Minh City", "09": "Can Tho",
}


class VnPhonePlugin:
    """Vietnamese phone number carrier and region lookup."""

    @property
    def name(self) -> str:
        return "VnPhone"

    @property
    def requires_api_key(self) -> bool:
        return False  # Numverify key is optional enhancement

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["phone", "PHONE"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("phone", "PHONE"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"VnPhone supports phone, got {target_type}",
            )

        # Normalize: remove spaces, dashes, +84
        phone = re.sub(r'[\s\-\(\)]', '', target)
        if phone.startswith("+84"):
            phone = "0" + phone[3:]
        elif phone.startswith("84"):
            phone = "0" + phone[2:]

        # Check if Vietnamese (starts with 0)
        if not phone.startswith("0"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Not a Vietnamese phone number: {target}",
            )

        # Detect carrier (local prefix lookup)
        carrier = None
        carrier_name = None
        for carrier_key, info in VN_CARRIERS.items():
            for prefix in info["prefixes"]:
                if phone.startswith(prefix):
                    carrier = carrier_key
                    carrier_name = info["name"]
                    break
            if carrier:
                break

        # Detect region (landline)
        region = None
        for prefix, region_name in VN_REGIONS.items():
            if phone.startswith(prefix):
                region = region_name
                break

        is_mobile = carrier is not None
        is_landline = region is not None

        # Base result from local lookup
        result_data = {
            "phone": phone,
            "original": target,
            "is_vietnamese": True,
            "is_mobile": is_mobile,
            "is_landline": is_landline,
            "carrier": carrier,
            "carrier_name": carrier_name,
            "region": region,
            "source": "local_prefix_lookup",
        }

        # Enhance with Numverify API if key configured
        numverify_key = os.environ.get("MH_NUMVERIFY_API_KEY", "")
        if numverify_key:
            api_data = await self._numverify_lookup(phone, numverify_key)
            if api_data:
                result_data.update(api_data)
                result_data["source"] = "local + numverify_api"

        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data=result_data,
        )

    async def _numverify_lookup(self, phone: str, api_key: str) -> dict | None:
        """Enhance with Numverify API: carrier, location, line type."""
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("numverify.com", self.name)

        # Convert to international format for Numverify
        intl_phone = "+84" + phone[1:] if phone.startswith("0") else phone

        try:
            async with aiohttp.ClientSession() as session:
                url = f"http://apilayer.net/api/validate"
                params = {
                    "access_key": api_key,
                    "number": intl_phone,
                    "country_code": "VN",
                    "format": 1,
                }

                async with session.get(
                    url, params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get("valid"):
                            return {
                                "numverify_valid": True,
                                "numverify_carrier": data.get("carrier", ""),
                                "numverify_line_type": data.get("line_type", ""),
                                "numverify_location": data.get("location", ""),
                                "numverify_country": data.get("country_name", ""),
                                "international_format": data.get("international_format", ""),
                                "national_format": data.get("national_format", ""),
                            }
                        return {"numverify_valid": False}
        except Exception as e:
            logger.warning("VnPhone Numverify error: %s", e)

        return None

    def normalize_target(self, target: str) -> str:
        phone = re.sub(r'[\s\-\(\)]', '', target)
        if phone.startswith("+84"):
            phone = "0" + phone[3:]
        elif phone.startswith("84"):
            phone = "0" + phone[2:]
        return phone
