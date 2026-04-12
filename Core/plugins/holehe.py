"""
Core/plugins/holehe.py

Story 9.3 — HolehPlugin: Holehe email-to-service Intelligence Plugin.
Checks an email against 120+ services via the holehe library.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any

from Core.plugins.base import IntelligencePlugin, PluginResult


def _run_holehe_sync(email: str) -> list[dict]:
    """
    Run holehe in a synchronous context (called via run_in_executor).

    holehe uses trio internally, so we must run it via trio.run() in a
    separate thread to avoid nested event loop conflicts.

    Raises:
        ImportError: if holehe or trio are not installed.
    """
    import trio
    import httpx
    from holehe.core import get_functions, import_submodules, launch_module

    modules = import_submodules("holehe.modules")
    functions = get_functions(modules)
    results: list[dict] = []

    async def _collect() -> None:
        async with httpx.AsyncClient(timeout=10) as client:
            tasks = [
                trio.lowlevel.checkpoint,  # placeholder
            ]
            async with trio.open_nursery() as nursery:
                for fn in functions:
                    nursery.start_soon(launch_module, fn, email, client, results)

    trio.run(_collect)
    return results


class HolehPlugin:
    """
    Holehe Intelligence Plugin.

    Checks an email against 120+ services via holehe library.
    No API key required; holehe sends real HTTP requests to each service.

    stage = 2  — identity expansion (Epic 9 StageRouter)
    tos_risk = "tos_risk"  — sends real requests to third-party services
    """

    name: str = "Holehe"
    requires_api_key: bool = False
    stage: int = 2
    tos_risk: str = "tos_risk"

    # Class-level semaphore: max 3 concurrent holehe runs
    _semaphore: asyncio.Semaphore = asyncio.Semaphore(3)

    async def check(self, target: str, target_type: str) -> PluginResult:
        """
        Check an email address against 120+ services via holehe.

        Args:
            target: The email address to check.
            target_type: Must be "EMAIL" — other types return failure.

        Returns:
            PluginResult with registered services and recovery data.
        """
        if target_type.upper() != "EMAIL":
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Holehe only supports EMAIL targets, got {target_type}",
            )

        async with self._semaphore:
            try:
                loop = asyncio.get_running_loop()
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    results = await loop.run_in_executor(pool, _run_holehe_sync, target)

                # Parse holehe results
                registered: list[str] = []
                recovery_phones: list[str] = []
                recovery_emails: list[str] = []

                for item in results:
                    if item.get("exists"):
                        service_name = item.get("name", "")
                        if service_name:
                            registered.append(service_name)

                        phone = item.get("phoneNumber") or ""
                        if phone and "*" not in phone:
                            recovery_phones.append(phone)

                        email = item.get("emailrecovery") or ""
                        if email and "*" not in email:
                            recovery_emails.append(email)

                return PluginResult(
                    plugin_name=self.name,
                    is_success=True,
                    data={
                        "registered": registered,
                        "recovery_phones": recovery_phones,
                        "recovery_emails": recovery_emails,
                        "total_checked": len(results),
                        "total_registered": len(registered),
                    },
                )

            except ImportError:
                return PluginResult(
                    plugin_name=self.name,
                    is_success=False,
                    data={},
                    error_message=(
                        "holehe not installed. Run: pip install holehe"
                    ),
                )

            except Exception as exc:
                return PluginResult(
                    plugin_name=self.name,
                    is_success=False,
                    data={},
                    error_message=f"Holehe Error: {str(exc)}",
                )

    def extract_clues(self, result: PluginResult) -> list[tuple[str, str]]:
        """
        Extract typed clues from a PluginResult for BFS chaining.

        Args:
            result: PluginResult from check().

        Returns:
            List of (value, type) tuples — only fully revealed values (no '*').
            e.g. [("+84928881690", "PHONE"), ("user@gmail.com", "EMAIL")]
        """
        if not result.is_success or not result.data:
            return []

        clues: list[tuple[str, str]] = []

        for phone in result.data.get("recovery_phones", []):
            if phone and "*" not in phone:
                clues.append((phone, "PHONE"))

        for email in result.data.get("recovery_emails", []):
            if email and "*" not in email:
                clues.append((email, "EMAIL"))

        return clues
