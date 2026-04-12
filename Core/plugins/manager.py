"""
Core/plugins/manager.py

Story 7.1 — Plugin Interface Design
Provides PluginManager to discover, register, and execute Intelligence plugins concurrently.

Story 9.5 — Cache Layer
PluginManager now accepts an optional PluginCache for transparent result caching.
"""
from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
import pkgutil
from typing import TYPE_CHECKING, List

import aiohttp

from Core.plugins.base import IntelligencePlugin, PluginResult

if TYPE_CHECKING:
    from Core.cache.plugin_cache import PluginCache

logger = logging.getLogger(__name__)


class PluginManager:
    """
    AC3 — Quản lý vòng đời (discover, register, load, execute) cho các plugins.

    Story 9.5: accepts optional `cache` parameter for transparent result caching.
    Plugins are unaware of caching — it is applied transparently in _safe_execute().
    """

    def __init__(self, cache: PluginCache | None = None) -> None:
        self._plugins: list[IntelligencePlugin] = []
        self._cache = cache

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
                    except Exception as e:
                        logger.warning("Failed to instantiate plugin %s.%s: %s", modname, _attr_name, e)

        return discovered

    async def run_all(self, target: str, target_type: str) -> List[PluginResult]:
        """
        Khởi chạy kiểm tra đồng thời (concurrent execution) cho TẤT CẢ plugins đã đăng ký.
        Uses a shared aiohttp session for connection pooling across plugins.
        """
        async with aiohttp.ClientSession() as shared_session:
            for plugin in self._plugins:
                plugin._shared_session = shared_session  # type: ignore[attr-defined]
            tasks = [
                self._safe_execute(plugin, target, target_type)
                for plugin in self._plugins
            ]
            results = list(await asyncio.gather(*tasks))
            for plugin in self._plugins:
                plugin._shared_session = None  # type: ignore[attr-defined]
        return results

    async def _safe_execute(
        self, plugin: IntelligencePlugin, target: str, target_type: str
    ) -> PluginResult:
        """
        Wrap plugin execution with cache check and exception safety.

        Cache logic (AC7):
        - Check cache before calling plugin.
        - On cache hit: return reconstructed PluginResult from cached data.
        - On cache miss: run plugin, store result if is_success=True and data non-empty.
        - Failed results are never cached.
        """
        # Cache check
        key: str | None = None
        if self._cache is not None:
            key = self._cache_key(plugin, target, target_type)
            try:
                cached = self._cache.get(key)
            except Exception:
                cached = None
            if cached is not None:
                logger.debug("Cache hit for %s: %s", plugin.name, target)
                return PluginResult(plugin_name=plugin.name, is_success=True, data=cached)

        # Run plugin
        try:
            result = await plugin.check(target, target_type)
        except Exception as e:
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

        # Cache successful results
        if self._cache is not None and result.is_success and result.data:
            if key is None:
                key = self._cache_key(plugin, target, target_type)
            try:
                await self._cache.set(key, result.data)
            except Exception as e:
                logger.warning("Cache write failed for %s: %s", plugin.name, e)

        return result

    def _cache_key(self, plugin: IntelligencePlugin, target: str, target_type: str) -> str:
        """Build a deterministic cache key: '{plugin_name}:{TARGET_TYPE}:{normalized_target}'.

        If the plugin defines a ``normalize_target(target)`` method, it is called
        to canonicalize the target before key construction.  This ensures that
        different surface formats of the same value (e.g. '+84 928 881 690' vs
        '+84928881690') share a single cache entry.
        """
        try:
            name = plugin.name
        except Exception:
            name = "unknown"
        # Allow plugins to normalize target for cache dedup
        if hasattr(plugin, "normalize_target"):
            try:
                target = plugin.normalize_target(target)
            except Exception:
                pass
        return f"{name}:{target_type.upper()}:{target.casefold()}"
