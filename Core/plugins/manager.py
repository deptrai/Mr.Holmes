"""
Core/plugins/manager.py

Story 7.1 — Plugin Interface Design
Provides PluginManager to discover, register, and execute Intelligence plugins concurrently.
"""
from __future__ import annotations

import asyncio
import importlib
import inspect
import pkgutil
from typing import List

from Core.plugins.base import IntelligencePlugin, PluginResult


class PluginManager:
    """
    AC3 — Quản lý vòng đời (discover, register, load, execute) cho các plugins.
    """

    def __init__(self) -> None:
        self._plugins: list[IntelligencePlugin] = []

    @property
    def plugins(self) -> list[IntelligencePlugin]:
        """Read-only view of registered plugins."""
        return list(self._plugins)

    def register(self, plugin: IntelligencePlugin) -> None:
        """
        Đăng ký (add) một plugin vào manager.
        Bỏ qua nếu plugin cùng tên đã đăng ký (dedup by name).
        """
        existing_names = {p.name for p in self._plugins}
        if plugin.name in existing_names:
            return
        self._plugins.append(plugin)

    def discover_plugins(self) -> int:
        """
        AC3 — Auto-discover plugin classes trong package Core.plugins.

        Quét tất cả submodules trong `Core.plugins`, tìm các class
        có attribute `name`, `requires_api_key`, và `check` (duck-typing
        check cho IntelligencePlugin Protocol).

        Returns:
            Số lượng plugins mới được phát hiện và đăng ký.
        """
        import Core.plugins as plugins_pkg

        discovered = 0
        for importer, modname, ispkg in pkgutil.iter_modules(
            plugins_pkg.__path__, prefix="Core.plugins."
        ):
            # Skip base and manager modules
            if modname in ("Core.plugins.base", "Core.plugins.manager"):
                continue
            try:
                module = importlib.import_module(modname)
            except ImportError:
                continue

            for _attr_name, obj in inspect.getmembers(module, inspect.isclass):
                # Duck-type check: must have name, requires_api_key, check
                if (
                    hasattr(obj, "name")
                    and hasattr(obj, "requires_api_key")
                    and hasattr(obj, "check")
                    and obj is not IntelligencePlugin
                ):
                    try:
                        instance = obj()
                        self.register(instance)
                        discovered += 1
                    except Exception:
                        pass  # Skip classes that can't be instantiated without args

        return discovered

    async def run_all(self, target: str, target_type: str) -> List[PluginResult]:
        """
        Khởi chạy kiểm tra đồng thời (concurrent execution) cho TẤT CẢ plugins đã đăng ký.
        """
        tasks = [
            self._safe_execute(plugin, target, target_type)
            for plugin in self._plugins
        ]
        return list(await asyncio.gather(*tasks))

    async def _safe_execute(
        self, plugin: IntelligencePlugin, target: str, target_type: str
    ) -> PluginResult:
        """Wrap plugin execution with exception safety."""
        try:
            return await plugin.check(target, target_type)
        except Exception as e:
            # Guard: plugin.name itself might throw
            try:
                name = plugin.name
            except Exception:
                name = "unknown"
            return PluginResult(
                plugin_name=name,
                is_success=False,
                data={},
                error_message=f"Plugin Exception: {str(e)}",
            )
