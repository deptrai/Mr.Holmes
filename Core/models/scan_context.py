"""
Core/models/scan_context.py

Typed dataclasses thay thế 19-parameter method signature trong Requests_Search.search().
Phần của Story 1.1 — Foundation Refactoring, Epic 1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScanContext:
    """
    Chứa tất cả input configuration cho 1 scan session.

    Thay thế các params: username, subject, report, json_file, json_file2
    và tất cả per-site caller context.

    Ví dụ sử dụng:
        ctx = ScanContext(target="johndoe", subject_type="USERNAME")
    """

    # Primary target
    target: str
    subject_type: str  # "USERNAME" | "PHONE-NUMBER" | "EMAIL" | "WEBSITE" | "PERSON"

    # Report output paths
    report_path: str = ""
    json_output_path: str = ""  # thay thế json_file
    json_names_path: str = ""   # thay thế json_file2

    # Scan metadata
    nsfw_enabled: bool = False
    concurrency_limit: int = 20  # used by Story 2.2 asyncio.Semaphore


@dataclass
class ScanConfig:
    """
    Chứa runtime configuration tách biệt khỏi target context.

    Thay thế các params: http_proxy, Writable, cùng các settings liên quan proxy.

    Ví dụ sử dụng:
        cfg = ScanConfig(proxy_dict={"http": "http://proxy:8080"}, writable=True)
    """

    # Proxy settings — thay thế http_proxy
    proxy_enabled: bool = False
    proxy_dict: Optional[dict] = None  # format: {"http": "...", "https": "..."}
    proxy_identity: Optional[str] = None  # thay thế identity string từ ip-api.com

    # Output mode
    writable: bool = True              # thay thế Writable param

    # Tags behavior
    process_tags: bool = True          # False khi subject_type == PHONE-NUMBER
