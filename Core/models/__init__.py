"""
Core/models/__init__.py

Public exports cho Core.models package.
Phần của Story 1.1 — Foundation Refactoring, Epic 1.
"""
from Core.models.scan_context import ScanContext, ScanConfig
from Core.models.scan_result import ScanResult, ScanStatus, ErrorStrategy
from Core.models.exceptions import (
    OSINTError,
    TargetSiteTimeout,
    ProxyDeadError,
    RateLimitExceeded,
    ScraperError,
    ConfigurationError,
    SiteCheckError,
)

__all__ = [
    # Dataclasses
    "ScanContext",
    "ScanConfig",
    "ScanResult",
    # Enums
    "ScanStatus",
    "ErrorStrategy",
    # Exceptions
    "OSINTError",
    "TargetSiteTimeout",
    "ProxyDeadError",
    "RateLimitExceeded",
    "ScraperError",
    "ConfigurationError",
    "SiteCheckError",
]
