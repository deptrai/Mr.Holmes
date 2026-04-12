"""
tests/plugins/test_github_plugin.py

Story 9.7 — GitHubPlugin unit tests.

Coverage:
- AC1: class attributes (name, requires_api_key, stage, tos_risk)
- AC2: USERNAME path (profile + events), EMAIL path (commit search)
- AC3: auth header with/without token
- AC4: rate limit handling (403, X-RateLimit headers, max wait)
- AC5: extract_clues() returns email clues
- AC2 edge: unsupported target types return failure
"""
from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures & helpers
# ─────────────────────────────────────────────────────────────────────────────

SAMPLE_USER_PROFILE = {
    "login": "deptraidapxichlo",
    "name": "Nguyen Van A",
    "bio": "Python developer",
    "avatar_url": "https://avatars.github.com/u/12345",
    "location": "Ho Chi Minh City",
    "company": "FPT Software",
    "html_url": "https://github.com/deptraidapxichlo",
    "public_repos": 12,
    "followers": 45,
}

SAMPLE_EVENTS = [
    {
        "type": "PushEvent",
        "payload": {
            "commits": [
                {"author": {"name": "Nguyen Van A", "email": "user@example.com"}},
                {"author": {"name": "GitHub Action[bot]", "email": "12345+user@users.noreply.github.com"}},
            ]
        },
    },
    {
        "type": "WatchEvent",
        "payload": {},
    },
]

SAMPLE_COMMIT_SEARCH = {
    "items": [
        {"commit": {"author": {"name": "Nguyen Van A", "email": "user@example.com"}}},
        {"commit": {"author": {"name": "Nguyen Van B", "email": "other@example.com"}}},
    ]
}


def _make_response(status: int, json_data, headers: dict | None = None):
    """Build a mock aiohttp response."""
    mock_resp = AsyncMock()
    mock_resp.status = status
    mock_resp.json = AsyncMock(return_value=json_data)
    mock_resp.headers = headers or {}
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)
    return mock_resp


def _make_session(responses: list):
    """
    Build a mock aiohttp.ClientSession that returns responses in order.
    `responses` is a list of mock response objects returned by get().
    """
    call_count = [-1]

    def _get(*args, **kwargs):
        call_count[0] += 1
        return responses[call_count[0]]

    mock_session = MagicMock()
    mock_session.get = MagicMock(side_effect=_get)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    return mock_session


# ─────────────────────────────────────────────────────────────────────────────
# AC1 — Class attributes
# ─────────────────────────────────────────────────────────────────────────────

class TestGitHubPluginAttributes:
    def test_name(self):
        from Core.plugins.github import GitHubPlugin
        p = GitHubPlugin()
        assert p.name == "GitHub"

    def test_requires_api_key_false(self):
        from Core.plugins.github import GitHubPlugin
        p = GitHubPlugin()
        assert p.requires_api_key is False

    def test_stage_is_2(self):
        from Core.plugins.github import GitHubPlugin
        p = GitHubPlugin()
        assert p.stage == 2

    def test_tos_risk_safe(self):
        from Core.plugins.github import GitHubPlugin
        p = GitHubPlugin()
        assert p.tos_risk == "safe"

    def test_init_no_token(self):
        from Core.plugins.github import GitHubPlugin
        p = GitHubPlugin()
        assert p.api_key == ""

    def test_init_with_token(self):
        from Core.plugins.github import GitHubPlugin
        p = GitHubPlugin(api_key="ghp_test123")
        assert p.api_key == "ghp_test123"


# ─────────────────────────────────────────────────────────────────────────────
# AC2 — USERNAME path
# ─────────────────────────────────────────────────────────────────────────────

class TestGitHubPluginUsernamePath:
    @pytest.mark.asyncio
    async def test_username_returns_success(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        resp_profile = _make_response(200, SAMPLE_USER_PROFILE)
        resp_events = _make_response(200, SAMPLE_EVENTS)
        mock_session = _make_session([resp_profile, resp_events])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("deptraidapxichlo", "USERNAME")

        assert result.is_success is True

    @pytest.mark.asyncio
    async def test_username_extracts_profile_fields(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        resp_profile = _make_response(200, SAMPLE_USER_PROFILE)
        resp_events = _make_response(200, SAMPLE_EVENTS)
        mock_session = _make_session([resp_profile, resp_events])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("deptraidapxichlo", "USERNAME")

        assert result.data["username"] == "deptraidapxichlo"
        assert result.data["profile_url"] == "https://github.com/deptraidapxichlo"
        assert result.data["bio"] == "Python developer"
        assert result.data["location"] == "Ho Chi Minh City"
        assert result.data["company"] == "FPT Software"
        assert result.data["public_repos"] == 12
        assert result.data["followers"] == 45

    @pytest.mark.asyncio
    async def test_username_extracts_real_name(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        resp_profile = _make_response(200, SAMPLE_USER_PROFILE)
        resp_events = _make_response(200, SAMPLE_EVENTS)
        mock_session = _make_session([resp_profile, resp_events])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("deptraidapxichlo", "USERNAME")

        assert "Nguyen Van A" in result.data["real_names"]

    @pytest.mark.asyncio
    async def test_username_extracts_emails_from_events(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        resp_profile = _make_response(200, SAMPLE_USER_PROFILE)
        resp_events = _make_response(200, SAMPLE_EVENTS)
        mock_session = _make_session([resp_profile, resp_events])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("deptraidapxichlo", "USERNAME")

        # user@example.com should be extracted, noreply@github.com should be filtered
        assert "user@example.com" in result.data["emails"]
        assert "12345+user@users.noreply.github.com" not in result.data["emails"]

    @pytest.mark.asyncio
    async def test_username_filters_bot_names(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        resp_profile = _make_response(200, SAMPLE_USER_PROFILE)
        resp_events = _make_response(200, SAMPLE_EVENTS)
        mock_session = _make_session([resp_profile, resp_events])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("deptraidapxichlo", "USERNAME")

        # "GitHub Action[bot]" should be filtered out
        assert not any("[bot]" in n for n in result.data["real_names"])

    @pytest.mark.asyncio
    async def test_username_404_returns_failure(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        resp_profile = _make_response(404, {})
        mock_session = _make_session([resp_profile])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("nonexistentuser99999", "USERNAME")

        assert result.is_success is False
        assert "404" in result.error_message or "not found" in result.error_message.lower()


# ─────────────────────────────────────────────────────────────────────────────
# AC2 — EMAIL path
# ─────────────────────────────────────────────────────────────────────────────

class TestGitHubPluginEmailPath:
    @pytest.mark.asyncio
    async def test_email_returns_success(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        resp_search = _make_response(200, SAMPLE_COMMIT_SEARCH)
        mock_session = _make_session([resp_search])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("user@example.com", "EMAIL")

        assert result.is_success is True

    @pytest.mark.asyncio
    async def test_email_extracts_author_names(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        resp_search = _make_response(200, SAMPLE_COMMIT_SEARCH)
        mock_session = _make_session([resp_search])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("user@example.com", "EMAIL")

        assert "Nguyen Van A" in result.data["real_names"]
        assert "Nguyen Van B" in result.data["real_names"]

    @pytest.mark.asyncio
    async def test_email_empty_search_returns_success_with_empty_data(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        resp_search = _make_response(200, {"items": []})
        mock_session = _make_session([resp_search])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("noemail@example.com", "EMAIL")

        assert result.is_success is True
        assert result.data["real_names"] == []


# ─────────────────────────────────────────────────────────────────────────────
# AC2 — Unsupported target types
# ─────────────────────────────────────────────────────────────────────────────

class TestGitHubPluginUnsupportedTypes:
    @pytest.mark.asyncio
    async def test_ip_returns_failure(self):
        from Core.plugins.github import GitHubPlugin
        result = await GitHubPlugin().check("1.2.3.4", "IP")
        assert result.is_success is False

    @pytest.mark.asyncio
    async def test_domain_returns_failure(self):
        from Core.plugins.github import GitHubPlugin
        result = await GitHubPlugin().check("example.com", "DOMAIN")
        assert result.is_success is False

    @pytest.mark.asyncio
    async def test_phone_returns_failure(self):
        from Core.plugins.github import GitHubPlugin
        result = await GitHubPlugin().check("+84912345678", "PHONE")
        assert result.is_success is False


# ─────────────────────────────────────────────────────────────────────────────
# AC3 — Auth header
# ─────────────────────────────────────────────────────────────────────────────

class TestGitHubPluginAuth:
    @pytest.mark.asyncio
    async def test_with_token_sends_authorization_header(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin(api_key="ghp_mytoken")

        captured_headers = {}

        resp_profile = _make_response(200, SAMPLE_USER_PROFILE)
        resp_events = _make_response(200, [])

        def capture_get(url, headers=None, **kwargs):
            captured_headers.update(headers or {})
            if "events" in url:
                return resp_events
            return resp_profile

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=capture_get)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await plugin.check("someuser", "USERNAME")

        assert captured_headers.get("Authorization") == "Bearer ghp_mytoken"

    @pytest.mark.asyncio
    async def test_without_token_no_authorization_header(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        captured_headers = {}

        resp_profile = _make_response(200, SAMPLE_USER_PROFILE)
        resp_events = _make_response(200, [])

        def capture_get(url, headers=None, **kwargs):
            captured_headers.update(headers or {})
            if "events" in url:
                return resp_events
            return resp_profile

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=capture_get)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            await plugin.check("someuser", "USERNAME")

        assert "Authorization" not in captured_headers

    @pytest.mark.asyncio
    async def test_token_from_env(self):
        from Core.plugins.github import GitHubPlugin
        with patch.dict("os.environ", {"MH_GITHUB_TOKEN": "ghp_envtoken"}):
            plugin = GitHubPlugin()
            # Token should be auto-loaded from env when not provided explicitly
            # (Behavior: if api_key is empty, load from env at check time)
            resp_profile = _make_response(200, SAMPLE_USER_PROFILE)
            resp_events = _make_response(200, [])
            captured = {}

            def capture_get(url, headers=None, **kwargs):
                captured.update(headers or {})
                if "events" in url:
                    return resp_events
                return resp_profile

            mock_session = MagicMock()
            mock_session.get = MagicMock(side_effect=capture_get)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=False)

            with patch("aiohttp.ClientSession", return_value=mock_session):
                await plugin.check("someuser", "USERNAME")

            assert captured.get("Authorization") == "Bearer ghp_envtoken"


# ─────────────────────────────────────────────────────────────────────────────
# AC4 — Rate limit handling
# ─────────────────────────────────────────────────────────────────────────────

class TestGitHubPluginRateLimit:
    @pytest.mark.asyncio
    async def test_403_returns_failure_with_message(self):
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        resp = _make_response(403, {"message": "API rate limit exceeded"})
        mock_session = _make_session([resp])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("someuser", "USERNAME")

        assert result.is_success is False
        assert "403" in result.error_message or "rate limit" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_429_with_short_reset_retries(self):
        """When 429 and reset is soon (<60s), should wait and retry."""
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        reset_time = int(time.time()) + 2
        rate_limit_headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset_time),
        }
        resp_429 = _make_response(429, {"message": "rate limit"}, headers=rate_limit_headers)
        resp_events = _make_response(200, [])
        resp_profile_ok = _make_response(200, SAMPLE_USER_PROFILE)

        call_count = [0]

        def mock_get(url, **kwargs):
            call_count[0] += 1
            if "events" in url:
                return resp_events
            if call_count[0] == 1:
                return resp_429
            return resp_profile_ok

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=mock_get)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session), \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await plugin.check("someuser", "USERNAME")

        mock_sleep.assert_awaited()
        assert result.is_success is True

    @pytest.mark.asyncio
    async def test_429_with_long_reset_returns_failure(self):
        """When 429 and reset time > 60s, should return failure instead of blocking."""
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        reset_time = int(time.time()) + 120
        rate_limit_headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(reset_time),
        }
        resp_429 = _make_response(429, {"message": "rate limit"}, headers=rate_limit_headers)
        mock_session = _make_session([resp_429])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("someuser", "USERNAME")

        assert result.is_success is False
        assert "rate limit" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_email_403_returns_failure(self):
        """EMAIL path: 403 should return failure."""
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        resp = _make_response(403, {"message": "Forbidden"})
        mock_session = _make_session([resp])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("user@example.com", "EMAIL")

        assert result.is_success is False
        assert "403" in result.error_message

    @pytest.mark.asyncio
    async def test_network_exception_returns_failure(self):
        """Network errors should return failure PluginResult, not raise."""
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=aiohttp.ClientConnectionError("timeout"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("someuser", "USERNAME")

        assert result.is_success is False
        assert "Network Error" in result.error_message

    @pytest.mark.asyncio
    async def test_email_network_exception_returns_failure(self):
        """EMAIL path: network errors should return failure PluginResult."""
        from Core.plugins.github import GitHubPlugin
        plugin = GitHubPlugin()

        mock_session = MagicMock()
        mock_session.get = MagicMock(side_effect=aiohttp.ClientConnectionError("timeout"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await plugin.check("user@example.com", "EMAIL")

        assert result.is_success is False
        assert "Network Error" in result.error_message


# ─────────────────────────────────────────────────────────────────────────────
# AC5 — extract_clues()
# ─────────────────────────────────────────────────────────────────────────────

class TestGitHubPluginExtractClues:
    def test_extract_clues_returns_email_tuples(self):
        from Core.plugins.github import GitHubPlugin
        from Core.plugins.base import PluginResult

        plugin = GitHubPlugin()
        result = PluginResult(
            plugin_name="GitHub",
            is_success=True,
            data={"emails": ["a@example.com", "b@example.com"]},
        )
        clues = plugin.extract_clues(result)
        assert ("a@example.com", "EMAIL") in clues
        assert ("b@example.com", "EMAIL") in clues

    def test_extract_clues_empty_emails(self):
        from Core.plugins.github import GitHubPlugin
        from Core.plugins.base import PluginResult

        plugin = GitHubPlugin()
        result = PluginResult(
            plugin_name="GitHub",
            is_success=True,
            data={"emails": []},
        )
        assert plugin.extract_clues(result) == []

    def test_extract_clues_missing_emails_key(self):
        from Core.plugins.github import GitHubPlugin
        from Core.plugins.base import PluginResult

        plugin = GitHubPlugin()
        result = PluginResult(
            plugin_name="GitHub",
            is_success=False,
            data={},
        )
        assert plugin.extract_clues(result) == []

    def test_extract_clues_type_label_is_email(self):
        from Core.plugins.github import GitHubPlugin
        from Core.plugins.base import PluginResult

        plugin = GitHubPlugin()
        result = PluginResult(
            plugin_name="GitHub",
            is_success=True,
            data={"emails": ["x@y.com"]},
        )
        clues = plugin.extract_clues(result)
        assert all(t == "EMAIL" for _, t in clues)


# ─────────────────────────────────────────────────────────────────────────────
# Story 9.17 — AC1: _is_bot_name() static method
# ─────────────────────────────────────────────────────────────────────────────

class TestIsBotName:
    def test_bot_suffix_lowercase(self):
        from Core.plugins.github import GitHubPlugin
        assert GitHubPlugin._is_bot_name("renovate[bot]") is True

    def test_bot_suffix_uppercase(self):
        from Core.plugins.github import GitHubPlugin
        assert GitHubPlugin._is_bot_name("Dependabot[BOT]") is True

    def test_bot_suffix_mixed_case(self):
        from Core.plugins.github import GitHubPlugin
        assert GitHubPlugin._is_bot_name("snyk[Bot]") is True

    def test_known_pattern_github_actions(self):
        from Core.plugins.github import GitHubPlugin
        assert GitHubPlugin._is_bot_name("github-actions") is True

    def test_known_pattern_dependabot(self):
        from Core.plugins.github import GitHubPlugin
        assert GitHubPlugin._is_bot_name("dependabot") is True

    def test_known_pattern_renovate(self):
        from Core.plugins.github import GitHubPlugin
        assert GitHubPlugin._is_bot_name("renovate") is True

    def test_known_pattern_snyk(self):
        from Core.plugins.github import GitHubPlugin
        assert GitHubPlugin._is_bot_name("snyk") is True

    def test_known_pattern_codecov(self):
        from Core.plugins.github import GitHubPlugin
        assert GitHubPlugin._is_bot_name("codecov") is True

    def test_real_user_not_bot(self):
        from Core.plugins.github import GitHubPlugin
        assert GitHubPlugin._is_bot_name("luisphan") is False

    def test_empty_string_not_bot(self):
        from Core.plugins.github import GitHubPlugin
        assert GitHubPlugin._is_bot_name("") is False

    @pytest.mark.asyncio
    async def test_bot_names_filtered_in_username_events(self):
        """Bot names from events must not appear in real_names via _is_bot_name."""
        from Core.plugins.github import GitHubPlugin

        events_with_bots = [
            {
                "type": "PushEvent",
                "payload": {
                    "commits": [
                        {"author": {"name": "renovate[bot]", "email": "bot@renovate.com"}},
                        {"author": {"name": "github-actions", "email": "action@github.com"}},
                        {"author": {"name": "Real User", "email": "real@example.com"}},
                    ]
                },
            }
        ]

        profile_resp = _make_response(200, SAMPLE_USER_PROFILE)
        events_resp = _make_response(200, events_with_bots)
        mock_session = _make_session([profile_resp, events_resp])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await GitHubPlugin().check("someuser", "USERNAME")

        assert result.is_success is True
        assert "renovate[bot]" not in result.data["real_names"]
        assert "github-actions" not in result.data["real_names"]
        assert "Real User" in result.data["real_names"]

    @pytest.mark.asyncio
    async def test_bot_profile_name_filtered(self):
        """Bot display name from profile data must not appear in real_names (P2 patch)."""
        from Core.plugins.github import GitHubPlugin

        bot_profile = dict(SAMPLE_USER_PROFILE, name="dependabot", login="dependabot")
        profile_resp = _make_response(200, bot_profile)
        events_resp = _make_response(200, [])
        mock_session = _make_session([profile_resp, events_resp])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await GitHubPlugin().check("dependabot", "USERNAME")

        assert result.is_success is True
        assert "dependabot" not in result.data["real_names"]

    @pytest.mark.asyncio
    async def test_bot_names_filtered_in_email_commits(self):
        """Bot names from commit search must not appear in real_names."""
        from Core.plugins.github import GitHubPlugin

        commit_items = [
            {"commit": {"author": {"name": "dependabot", "email": "bot@github.com"}}},
            {"commit": {"author": {"name": "codecov", "email": "codecov@example.com"}}},
            {"commit": {"author": {"name": "Alice", "email": "alice@example.com"}}},
        ]
        search_resp = _make_response(200, {"total_count": 3, "items": commit_items})
        mock_session = _make_session([search_resp])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await GitHubPlugin().check("alice@example.com", "EMAIL")

        assert result.is_success is True
        assert "dependabot" not in result.data["real_names"]
        assert "codecov" not in result.data["real_names"]
        assert "Alice" in result.data["real_names"]


# ─────────────────────────────────────────────────────────────────────────────
# Story 9.17 — AC2: 403 differentiation (rate limit vs access denied)
# ─────────────────────────────────────────────────────────────────────────────

class TestGitHub403Differentiation:
    @pytest.mark.asyncio
    async def test_username_403_rate_limit_message(self):
        """USERNAME path: 403 with 'rate limit' in body → 'Rate limit exceeded'."""
        from Core.plugins.github import GitHubPlugin

        resp = _make_response(403, {"message": "API rate limit exceeded for …"})
        mock_session = _make_session([resp])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await GitHubPlugin().check("someuser", "USERNAME")

        assert result.is_success is False
        assert "Rate limit exceeded" in result.error_message
        assert "Access denied" not in result.error_message

    @pytest.mark.asyncio
    async def test_username_403_access_denied_message(self):
        """USERNAME path: 403 without 'rate limit' in body → 'Access denied'."""
        from Core.plugins.github import GitHubPlugin

        resp = _make_response(403, {"message": "Forbidden"})
        mock_session = _make_session([resp])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await GitHubPlugin().check("someuser", "USERNAME")

        assert result.is_success is False
        assert "Access denied" in result.error_message
        assert "Rate limit exceeded" not in result.error_message

    @pytest.mark.asyncio
    async def test_username_403_non_json_body_fallback(self):
        """USERNAME path: 403 with non-parseable body → graceful fallback."""
        from Core.plugins.github import GitHubPlugin

        resp = _make_response(403, None)  # None → _get_json returns None as data
        mock_session = _make_session([resp])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await GitHubPlugin().check("someuser", "USERNAME")

        assert result.is_success is False
        assert "403" in result.error_message

    @pytest.mark.asyncio
    async def test_email_403_rate_limit_message(self):
        """EMAIL path: 403 with 'rate limit' in body → 'Rate limit exceeded'."""
        from Core.plugins.github import GitHubPlugin

        resp = _make_response(403, {"message": "API rate limit exceeded"})
        mock_session = _make_session([resp])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await GitHubPlugin().check("user@example.com", "EMAIL")

        assert result.is_success is False
        assert "Rate limit exceeded" in result.error_message

    @pytest.mark.asyncio
    async def test_email_403_access_denied_message(self):
        """EMAIL path: 403 without 'rate limit' in body → 'Access denied'."""
        from Core.plugins.github import GitHubPlugin

        resp = _make_response(403, {"message": "Forbidden"})
        mock_session = _make_session([resp])

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await GitHubPlugin().check("user@example.com", "EMAIL")

        assert result.is_success is False
        assert "Access denied" in result.error_message


# ─────────────────────────────────────────────────────────────────────────────
# Story 9.17 — AC4: extract_clues returns real_names as USERNAME tuples
# ─────────────────────────────────────────────────────────────────────────────

class TestExtractCluesRealNames:
    def test_extract_clues_includes_real_names_as_username(self):
        from Core.plugins.github import GitHubPlugin
        from Core.plugins.base import PluginResult

        plugin = GitHubPlugin()
        result = PluginResult(
            plugin_name="GitHub",
            is_success=True,
            data={"emails": [], "real_names": ["Alice Smith", "Bob Jones"]},
        )
        clues = plugin.extract_clues(result)
        assert ("Alice Smith", "USERNAME") in clues
        assert ("Bob Jones", "USERNAME") in clues

    def test_extract_clues_real_names_and_emails_together(self):
        from Core.plugins.github import GitHubPlugin
        from Core.plugins.base import PluginResult

        plugin = GitHubPlugin()
        result = PluginResult(
            plugin_name="GitHub",
            is_success=True,
            data={"emails": ["a@example.com"], "real_names": ["Alice"]},
        )
        clues = plugin.extract_clues(result)
        assert ("a@example.com", "EMAIL") in clues
        assert ("Alice", "USERNAME") in clues

    def test_extract_clues_empty_real_names(self):
        from Core.plugins.github import GitHubPlugin
        from Core.plugins.base import PluginResult

        plugin = GitHubPlugin()
        result = PluginResult(
            plugin_name="GitHub",
            is_success=True,
            data={"emails": [], "real_names": []},
        )
        assert plugin.extract_clues(result) == []

    def test_extract_clues_missing_real_names_key(self):
        from Core.plugins.github import GitHubPlugin
        from Core.plugins.base import PluginResult

        plugin = GitHubPlugin()
        result = PluginResult(
            plugin_name="GitHub",
            is_success=True,
            data={"emails": ["x@y.com"]},
        )
        clues = plugin.extract_clues(result)
        # Should still return emails, just no real_names crash
        assert ("x@y.com", "EMAIL") in clues
