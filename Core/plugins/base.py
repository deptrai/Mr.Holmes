"""
Core/plugins/base.py

Story 7.1 — Plugin Interface Design
Defines standard interfaces and dataclasses for external intelligence API plugins.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Protocol

import aiohttp


@dataclass
class PluginResult:
    """
    AC2 — Dữ liệu chuẩn hoá trả về từ một External Plugin.
    """
    plugin_name: str
    is_success: bool
    data: dict[str, Any]
    error_message: str | None = None


class IntelligencePlugin(Protocol):
    """
    AC1 — Chuẩn giao tiếp (Protocol) bắt buộc dành cho các External OSINT sources.
    Bất cứ plugin nào (HIBP, Shodan, v.v) đều phải implement Protocol này.

    Epic 9 additions (backward compatible — existing plugins not required to implement):
        stage: int  — enrichment stage (1=legacy, 2=identity expansion, 3=deep enrichment)
                      Default: 1 (Epic 8 plugins without this attribute default to stage 1
                      via getattr(plugin, 'stage', 1) in StageRouter.filter_plugins())
        tos_risk: str — "safe" | "tos_risk" | "ban_risk" (for CLI ToS summary display)
    """
    @property
    def name(self) -> str:
        """Tên định danh của plugin (e.g. 'HaveIBeenPwned')."""
        ...

    @property
    def requires_api_key(self) -> bool:
        """Plugin có cần cấp API Key để hoạt động không?"""
        ...

    async def check(self, target: str, target_type: str) -> PluginResult:
        """
        AC2 — Hàm quét mục tiêu thông qua Plugin.
        Args:
            target: Chuỗi giá trị cần quét (e.g. 'foo@bar.com', '192.168.1.1').
            target_type: Phân loại target (e.g. 'EMAIL', 'IP', 'USERNAME').
        """
        ...


@asynccontextmanager
async def get_http_session(plugin: object) -> AsyncIterator[aiohttp.ClientSession]:
    """Yield a shared aiohttp session from PluginManager if available, else create one.

    PluginManager sets ``plugin._shared_session`` before calling ``check()``.
    When used standalone (no manager), a fresh session is created and closed
    automatically — fully backward compatible.
    """
    shared = getattr(plugin, "_shared_session", None)
    if shared is not None and not shared.closed:
        yield shared
    else:
        async with aiohttp.ClientSession() as session:
            yield session
