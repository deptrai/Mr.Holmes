"""
Core/models/scan_result.py

ScanResult dataclass — thay thế 5 shared mutable lists trong Requests_Search.search():
  successfull, successfullName, ScraperSites, Tags, MostTags

Phần của Story 1.1 — Foundation Refactoring, Epic 1.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ScanStatus(Enum):
    """Trạng thái kết quả kiểm tra 1 site."""
    FOUND = "found"
    NOT_FOUND = "not_found"
    BLOCKED = "blocked"            # HTTP 403
    RATE_LIMITED = "rate_limited"  # HTTP 429
    CAPTCHA = "captcha"            # Phát hiện CAPTCHA trong body (Story 3.3)
    ERROR = "error"                # Generic error
    TIMEOUT = "timeout"            # Request timeout


class ErrorStrategy(Enum):
    """3 error detection strategies của Requests_Search."""
    STATUS_CODE = "Status-Code"
    MESSAGE = "Message"
    RESPONSE_URL = "Response-Url"


@dataclass
class ScanResult:
    """
    Thu thập kết quả kiểm tra 1 site.

    Thay thế pattern mutate-shared-lists:
      - successfull.append(site1)       → ScanResult(url=site1, status=FOUND)
      - successfullName.append(name)    → ScanResult(site_name=name)
      - ScraperSites.append(name)       → ScanResult(is_scrapable=True)
      - Tags.append(tag)                → tích lũy trong ScanResult.tags

    Ví dụ sử dụng:
        result = ScanResult(
            site_name="GitHub",
            url="https://github.com/johndoe",
            status=ScanStatus.FOUND,
            tags=["Developer", "Code"],
        )
        print(result.to_json())
    """

    site_name: str
    url: str
    status: ScanStatus = ScanStatus.NOT_FOUND
    is_scrapable: bool = False
    tags: list[str] = field(default_factory=list)
    main_identifier: str = ""    # thay thế `main` param — profile ID/username on that site
    error_message: Optional[str] = None
    plugin_data: dict = field(default_factory=dict)

    @property
    def found(self) -> bool:
        """Shortcut kiểm tra site có kết quả hay không."""
        return self.status == ScanStatus.FOUND

    def to_json(self) -> str:
        """
        Serialize ra JSON string — dùng cho report output.

        Returns:
            JSON string với tất cả fields.
        """
        return json.dumps({
            "site_name": self.site_name,
            "url": self.url,
            "status": self.status.value,
            "is_scrapable": self.is_scrapable,
            "tags": self.tags,
            "main_identifier": self.main_identifier,
            "error_message": self.error_message,
            "plugin_data": self.plugin_data,
        }, ensure_ascii=False, indent=2)

    def to_dict(self) -> dict:
        """
        Serialize ra dict — dùng cho JSON file writing trong report pipeline.
        """
        return {
            "site": self.url,
            "name": self.site_name,
            "status": self.status.value,
            "is_scrapable": self.is_scrapable,
            "tags": self.tags,
            "main_identifier": self.main_identifier,
            "error_message": self.error_message,
            "plugin_data": self.plugin_data,
        }

