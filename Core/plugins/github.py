"""
Core/plugins/github.py

Story 9.7 — GitHub Intelligence Plugin.

Looks up real names and emails from GitHub profiles and commit history,
providing high-confidence identity confirmation from publicly verifiable data.

Supports:
- USERNAME → GET /users/{username} + /users/{username}/events/public
- EMAIL    → GET /search/commits?q=author-email:{email}

Authentication:
- MH_GITHUB_TOKEN env var or api_key parameter → Bearer token header
- Without token: 60 req/hour (unauthenticated)

Rate limiting:
- Checks X-RateLimit-Remaining response header
- On 429: sleep until X-RateLimit-Reset (max 60s), retry once
- If reset > 60s away: return failure
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any
from urllib.parse import quote

import aiohttp

from Core.plugins.base import IntelligencePlugin, PluginResult, get_http_session


_BASE_URL = "https://api.github.com"
_MAX_RATE_WAIT = 60  # seconds — max we'll wait for rate limit reset
_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)

# GitHub's no-reply email domains
_NOREPLY_DOMAINS = frozenset({"noreply.github.com", "users.noreply.github.com"})


class GitHubPlugin(IntelligencePlugin):
    """
    GitHub public API plugin.
    stage=2 (Identity Expansion), tos_risk="safe".
    """

    name: str = "GitHub"
    requires_api_key: bool = False
    stage: int = 2
    tos_risk: str = "safe"

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_token(self) -> str:
        """Return token: explicit api_key > MH_GITHUB_TOKEN env."""
        return self.api_key or os.getenv("MH_GITHUB_TOKEN", "")

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"User-Agent": "MrHolmes-OSINT"}
        token = self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def _is_noreply(email: str) -> bool:
        """Check if email belongs to a GitHub noreply domain."""
        domain = email.rsplit("@", 1)[-1].lower() if "@" in email else ""
        return domain in _NOREPLY_DOMAINS

    _BOT_PATTERNS = frozenset({"github-actions", "dependabot", "renovate", "snyk", "codecov"})

    @staticmethod
    def _is_bot_name(name: str) -> bool:
        """Return True if name matches known bot patterns."""
        if not name or not isinstance(name, str):
            return False
        if name.lower().endswith("[bot]"):
            return True
        return name.lower() in GitHubPlugin._BOT_PATTERNS

    @staticmethod
    def _parse_403_message(data: object) -> str:
        """Return differentiated 403 error message based on response body."""
        if isinstance(data, dict):
            msg = data.get("message", "")
            if isinstance(msg, str) and "rate limit" in msg.lower():
                return "403 Rate limit exceeded."
            return "403 Access denied."
        return "403 Forbidden."

    async def _get_json(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: dict[str, str],
        retry: bool = True,
    ) -> tuple[int, Any, dict]:
        """
        Fetch JSON from url. Returns (status, json_data, response_headers).
        On 429: sleep until X-RateLimit-Reset (max 60s) and retry once.
        """
        async with session.get(url, headers=headers, timeout=_REQUEST_TIMEOUT) as response:
            status = response.status
            # P2: keep CIMultiDictProxy for case-insensitive header lookup
            resp_headers = response.headers
            # P3: content_type=None to avoid ContentTypeError on non-JSON
            data = await response.json(content_type=None) if status not in (204,) else {}

        # P1: Only sleep+retry on 429 (rate limited), not on successful responses
        if status == 429 and retry:
            reset_ts = resp_headers.get("X-RateLimit-Reset")
            if reset_ts:
                wait = int(reset_ts) - int(time.time())
                if wait <= 0:
                    wait = 1
                if wait > _MAX_RATE_WAIT:
                    return -1, None, resp_headers
                await asyncio.sleep(wait)
                return await self._get_json(session, url, headers, retry=False)
            return -1, None, resp_headers

        return status, data, resp_headers

    # ─────────────────────────────────────────────────────────────────────────
    # IntelligencePlugin protocol
    # ─────────────────────────────────────────────────────────────────────────

    async def check(self, target: str, target_type: str) -> PluginResult:
        t = target_type.upper()
        if t == "USERNAME":
            return await self._check_username(target)
        if t == "EMAIL":
            return await self._check_email(target)
        return PluginResult(
            plugin_name=self.name,
            is_success=False,
            data={},
            error_message=f"GitHub plugin does not support target type: {target_type}",
        )

    def extract_clues(self, result: PluginResult) -> list[tuple[str, str]]:
        """AC5/AC4 — extract email and real_name clues from result.data."""
        emails = result.data.get("emails") or []
        real_names = result.data.get("real_names") or []
        return (
            [(email, "EMAIL") for email in emails]
            + [(name, "USERNAME") for name in real_names]
        )

    # ─────────────────────────────────────────────────────────────────────────
    # USERNAME path
    # ─────────────────────────────────────────────────────────────────────────

    async def _check_username(self, username: str) -> PluginResult:
        headers = self._build_headers()
        profile_url = f"{_BASE_URL}/users/{username}"
        events_url = f"{_BASE_URL}/users/{username}/events/public?per_page=100"

        try:
            async with get_http_session(self) as session:
                # Fetch profile
                status, profile_data, _ = await self._get_json(session, profile_url, headers)

                if status == -1:
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=False,
                        data={},
                        error_message="GitHub rate limit exceeded; reset time > 60s. Try again later.",
                    )

                if status == 403:
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=False,
                        data={},
                        error_message=self._parse_403_message(profile_data),
                    )

                if status == 404:
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=False,
                        data={},
                        error_message=f"404 User not found: {username}",
                    )

                if status != 200:
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=False,
                        data={},
                        error_message=f"GitHub API error: HTTP {status}",
                    )

                # P6: Check events status for rate-limit signal
                ev_status, events_data, _ = await self._get_json(session, events_url, headers)
                events_partial = ev_status != 200
                events = events_data if isinstance(events_data, list) else []

        except Exception as exc:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"GitHub Network Error: {exc}",
            )

        # Parse profile — guard against non-dict (e.g. JSON null)
        if not isinstance(profile_data, dict):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="GitHub API returned unexpected data format",
            )

        real_names: list[str] = []
        emails: list[str] = []

        if profile_data.get("name") and not self._is_bot_name(profile_data["name"]):
            real_names.append(profile_data["name"])

        # Parse events for commit authors
        for event in events:
            if event.get("type") == "PushEvent":
                for commit in event.get("payload", {}).get("commits", []):
                    author = commit.get("author", {})
                    name = author.get("name", "").strip()
                    email = author.get("email", "").strip()

                    if name and not self._is_bot_name(name) and name not in real_names:
                        real_names.append(name)
                    # P7: Check specific noreply domains instead of substring
                    if email and "@" in email and not self._is_noreply(email) and email not in emails:
                        emails.append(email)

        data = {
            "username": profile_data.get("login", username),
            "profile_url": profile_data.get("html_url", f"https://github.com/{username}"),
            "real_names": real_names,
            "emails": emails,
            "bio": profile_data.get("bio", ""),
            "avatar_url": profile_data.get("avatar_url", ""),
            "location": profile_data.get("location", ""),
            "company": profile_data.get("company", ""),
            "public_repos": profile_data.get("public_repos", 0),
            "followers": profile_data.get("followers", 0),
        }

        # P6: Warn if events were unavailable (rate-limited or error)
        if events_partial:
            data["_events_partial"] = True

        return PluginResult(plugin_name=self.name, is_success=True, data=data)

    # ─────────────────────────────────────────────────────────────────────────
    # EMAIL path
    # ─────────────────────────────────────────────────────────────────────────

    async def _check_email(self, email: str) -> PluginResult:
        headers = self._build_headers()
        headers["Accept"] = "application/vnd.github.cloak-preview+json"
        # P5: URL-encode email for search query (handles + and special chars)
        search_url = f"{_BASE_URL}/search/commits?q=author-email:{quote(email)}&per_page=10"

        try:
            async with get_http_session(self) as session:
                status, search_data, _ = await self._get_json(session, search_url, headers)

                if status == -1:
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=False,
                        data={},
                        error_message="GitHub rate limit exceeded; reset time > 60s. Try again later.",
                    )

                if status == 403:
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=False,
                        data={},
                        error_message=self._parse_403_message(search_data),
                    )

                if status != 200:
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=False,
                        data={},
                        error_message=f"GitHub Search API error: HTTP {status}",
                    )

        except Exception as exc:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"GitHub Network Error: {exc}",
            )

        items = (search_data.get("items") or []) if isinstance(search_data, dict) else []
        real_names: list[str] = []

        for item in items:
            author = item.get("commit", {}).get("author", {})
            name = author.get("name", "").strip()
            if name and not self._is_bot_name(name) and name not in real_names:
                real_names.append(name)

        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={
                "username": None,
                "profile_url": None,
                "real_names": real_names,
                "emails": [email],
                "bio": "",
                "avatar_url": "",
                "location": "",
                "company": "",
                "public_repos": 0,
                "followers": 0,
            },
        )
