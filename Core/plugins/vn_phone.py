"""Core/plugins/vn_phone.py — Vietnamese phone carrier and region lookup.

Identifies carrier (Viettel, MobiFone, VinaPhone, etc.) and region
from Vietnamese phone number prefixes.
"""
from __future__ import annotations
import re
from typing import Any

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
        return False
    
    @property
    def stage(self) -> int:
        return 3
    
    @property
    def target_types(self) -> list[str]:
        return ["phone"]
    
    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult
        
        if target_type != "phone":
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"VnPhone only supports phone targets, got {target_type}"
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
                error_message=f"Not a Vietnamese phone number: {target}"
            )
        
        # Detect carrier
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
        
        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={
                "phone": phone,
                "original": target,
                "is_vietnamese": True,
                "is_mobile": is_mobile,
                "is_landline": is_landline,
                "carrier": carrier,
                "carrier_name": carrier_name,
                "region": region,
            }
        )
    
    def normalize_target(self, target: str) -> str:
        phone = re.sub(r'[\s\-\(\)]', '', target)
        if phone.startswith("+84"):
            phone = "0" + phone[3:]
        elif phone.startswith("84"):
            phone = "0" + phone[2:]
        return phone
