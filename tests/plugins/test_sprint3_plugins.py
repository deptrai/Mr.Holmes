"""Tests for Sprint 3 enrichment plugins: Truecaller, Snusbase, AvatarReverse."""
from __future__ import annotations

import asyncio
import os
from unittest.mock import patch

import pytest


# ─── Truecaller Plugin ────────────────────────────────────────────────────────

class TestTruecallerPlugin:
    def test_name(self):
        from Core.plugins.truecaller import TruecallerPlugin
        assert TruecallerPlugin().name == "Truecaller"

    def test_requires_api_key(self):
        from Core.plugins.truecaller import TruecallerPlugin
        assert TruecallerPlugin().requires_api_key is True

    def test_stage(self):
        from Core.plugins.truecaller import TruecallerPlugin
        assert TruecallerPlugin().stage == 3

    def test_tos_risk(self):
        from Core.plugins.truecaller import TruecallerPlugin
        assert TruecallerPlugin().tos_risk == "safe"

    def test_unsupported_target_type(self):
        from Core.plugins.truecaller import TruecallerPlugin
        plugin = TruecallerPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("test@example.com", "EMAIL")
        )
        assert result.is_success is False
        assert "supports phone" in result.error_message

    def test_invalid_phone(self):
        from Core.plugins.truecaller import TruecallerPlugin
        plugin = TruecallerPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("abc", "phone")
        )
        assert result.is_success is False
        assert "Invalid phone number" in result.error_message

    def test_missing_api_key(self):
        from Core.plugins.truecaller import TruecallerPlugin
        with patch.dict(os.environ, {"MH_TRUECALLER_API_KEY": ""}):
            plugin = TruecallerPlugin()
            result = asyncio.get_event_loop().run_until_complete(
                plugin.check("+84901234567", "phone")
            )
            assert result.is_success is False
            assert "MH_TRUECALLER_API_KEY not configured" in result.error_message


# ─── Snusbase Plugin ──────────────────────────────────────────────────────────

class TestSnusbasePlugin:
    def test_name(self):
        from Core.plugins.snusbase import SnusbasePlugin
        assert SnusbasePlugin().name == "Snusbase"

    def test_requires_api_key(self):
        from Core.plugins.snusbase import SnusbasePlugin
        assert SnusbasePlugin().requires_api_key is True

    def test_stage(self):
        from Core.plugins.snusbase import SnusbasePlugin
        assert SnusbasePlugin().stage == 1

    def test_tos_risk(self):
        from Core.plugins.snusbase import SnusbasePlugin
        assert SnusbasePlugin().tos_risk == "safe"

    def test_unsupported_target_type(self):
        from Core.plugins.snusbase import SnusbasePlugin
        plugin = SnusbasePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("test", "UNSUPPORTED_TYPE")
        )
        assert result.is_success is False
        assert "supports email/username/phone/ip/name/password/domain" in result.error_message

    def test_short_target(self):
        from Core.plugins.snusbase import SnusbasePlugin
        plugin = SnusbasePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("a", "email")
        )
        assert result.is_success is False
        assert "too short" in result.error_message

    def test_missing_api_key(self):
        from Core.plugins.snusbase import SnusbasePlugin
        with patch.dict(os.environ, {"MH_SNUSBASE_API_KEY": ""}):
            plugin = SnusbasePlugin()
            result = asyncio.get_event_loop().run_until_complete(
                plugin.check("test@example.com", "email")
            )
            assert result.is_success is False
            assert "MH_SNUSBASE_API_KEY not configured" in result.error_message


# ─── AvatarReverse Plugin ─────────────────────────────────────────────────────

class TestAvatarReversePlugin:
    def test_name(self):
        from Core.plugins.avatar_reverse import AvatarReversePlugin
        assert AvatarReversePlugin().name == "AvatarReverse"

    def test_requires_api_key(self):
        from Core.plugins.avatar_reverse import AvatarReversePlugin
        assert AvatarReversePlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.avatar_reverse import AvatarReversePlugin
        assert AvatarReversePlugin().stage == 3

    def test_tos_risk(self):
        from Core.plugins.avatar_reverse import AvatarReversePlugin
        assert AvatarReversePlugin().tos_risk == "safe"

    def test_unsupported_target_type(self):
        from Core.plugins.avatar_reverse import AvatarReversePlugin
        plugin = AvatarReversePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("192.168.1.1", "IP")
        )
        assert result.is_success is False
        assert "supports image_url/url" in result.error_message

    def test_invalid_image_url(self):
        from Core.plugins.avatar_reverse import AvatarReversePlugin
        plugin = AvatarReversePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("not-a-url", "image_url")
        )
        assert result.is_success is False
        assert "Invalid image URL" in result.error_message

    def test_empty_target(self):
        from Core.plugins.avatar_reverse import AvatarReversePlugin
        plugin = AvatarReversePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("", "image_url")
        )
        assert result.is_success is False
        assert "Invalid image URL" in result.error_message
