"""
Core/plugins/intelx.py — Intelligence X (IntelX) Plugin.

Searches breaches, leaks, and pastes across multiple sources via IntelX API.
Supports EMAIL, USERNAME, PHONE, DOMAIN, and IP targets.
Free alternative to HaveIBeenPwned with broader source coverage.
"""
from __future__ import annotations

import asyncio
import time
import aiohttp

from Core.plugins.base import IntelligencePlugin, PluginResult, get_http_session


class IntelXPlugin(IntelligencePlugin):
    """
    Intelligence X Plugin.

    Searches across breaches, leaks, pastes, and darknet datasets.
    API docs: https://github.com/IntelligenceX/SDK/blob/main/README.md
    """

    BASE_URL = "https://free.intelx.io"  # Free tier; paid users use "https://2.intelx.io"
    SUPPORTED_TYPES = {"EMAIL", "USERNAME", "PHONE", "DOMAIN", "IP"}

    # Class-level rate limiting (1 req per 0.5s — IntelX is generous)
    _lock = asyncio.Lock()
    _last_request_time = 0.0
    _rate_limit_delay = 0.5

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "IntelX"

    @property
    def requires_api_key(self) -> bool:
        return True

    stage: int = 1
    tos_risk: str = "safe"

    async def check(self, target: str, target_type: str) -> PluginResult:
        """Search IntelX for breach/leak data for the given target."""
        target_type_upper = target_type.upper()
        if target_type_upper not in self.SUPPORTED_TYPES:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"IntelX supports {', '.join(self.SUPPORTED_TYPES)}, got {target_type}",
            )

        if not self.api_key:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="IntelX API Key missing. Please configure MH_INTELX_API_KEY.",
            )

        # Rate limit
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._rate_limit_delay:
                await asyncio.sleep(self._rate_limit_delay - elapsed)
            self.__class__._last_request_time = time.monotonic()

        try:
            # Step 1: Start search — POST /intelligent/search
            search_payload = {
                "term": target,
                "buckets": [],
                "lookuplevel": 0,
                "maxresults": 100,
                "timeout": 0,
                "datefrom": "",
                "dateto": "",
                "sort": 4,
                "media": 0,
                "terminate": [],
            }
            headers = {"x-key": self.api_key, "Content-Type": "application/json"}

            async with get_http_session(self) as session:
                # Initiate search
                async with session.post(
                    f"{self.BASE_URL}/intelligent/search",
                    json=search_payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 401:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="401 Unauthorized — Invalid IntelX API key.",
                        )
                    if resp.status == 429:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="429 Rate Limit — IntelX.",
                        )
                    resp.raise_for_status()
                    init_data = await resp.json()
                    search_id = init_data.get("id")
                    if not search_id:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="IntelX returned no search ID.",
                        )

                # Step 2: Poll for results — GET /intelligent/search/result?id=...
                results: list[dict] = []
                for _attempt in range(10):
                    await asyncio.sleep(1.0)
                    async with session.get(
                        f"{self.BASE_URL}/intelligent/search/result",
                        params={"id": search_id, "limit": 100, "offset": 0},
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as r:
                        if r.status != 200:
                            break
                        poll_data = await r.json()
                        status = poll_data.get("status", 0)
                        # status 0 = in progress, 1 = completed, 2 = no results
                        records = poll_data.get("records") or []
                        results.extend(records)
                        if status in (1, 2):
                            break

            # Step 3: Parse results
            if not results:
                return PluginResult(
                    plugin_name=self.name,
                    is_success=True,
                    data={
                        "breach_count": 0,
                        "breaches": [],
                        "sources": [],
                        "data_classes": [],
                    },
                )

            breaches: list[dict] = []
            sources_set: set[str] = set()
            data_classes_set: set[str] = set()

            for record in results:
                breach_name = record.get("bucket", "") or record.get("source", "")
                preview = record.get("preview", "")
                record_type = record.get("type", "")
                date = record.get("added", "") or record.get("date", "")

                breaches.append({
                    "name": breach_name,
                    "date": date,
                    "type": record_type,
                    "preview": preview[:200],
                })
                if breach_name:
                    sources_set.add(breach_name)
                if record_type:
                    data_classes_set.add(record_type)

            return PluginResult(
                plugin_name=self.name,
                is_success=True,
                data={
                    "breach_count": len(breaches),
                    "breaches": breaches,
                    "sources": sorted(sources_set),
                    "data_classes": sorted(data_classes_set),
                },
            )

        except asyncio.TimeoutError:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="IntelX request timed out.",
            )
        except aiohttp.ClientError as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"IntelX network error: {e}",
            )
        except Exception as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"IntelX error: {e}",
            )

    def extract_clues(self, result: PluginResult) -> list[tuple[str, str]]:
        """Extract domain/email clues from IntelX breach previews."""
        if not result.is_success or not result.data:
            return []
        clues: list[tuple[str, str]] = []
        for breach in result.data.get("breaches", []):
            preview = breach.get("preview", "")
            # Simple email extraction from preview
            if "@" in preview:
                import re
                emails = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', preview)
                for email in emails:
                    clues.append((email, "EMAIL"))
        return clues
