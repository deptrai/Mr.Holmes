"""Tests for Sprint 2 social media plugins."""
from __future__ import annotations

import asyncio

import pytest


# ─── FacebookVn Plugin ────────────────────────────────────────────────────────

class TestFacebookVnPlugin:
    def test_name(self):
        from Core.plugins.facebook_vn import FacebookVnPlugin
        assert FacebookVnPlugin().name == "FacebookVn"

    def test_requires_api_key(self):
        from Core.plugins.facebook_vn import FacebookVnPlugin
        assert FacebookVnPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.facebook_vn import FacebookVnPlugin
        assert FacebookVnPlugin().stage == 3

    def test_tos_risk(self):
        from Core.plugins.facebook_vn import FacebookVnPlugin
        assert FacebookVnPlugin().tos_risk == "tos_risk"

    def test_unsupported_target_type(self):
        from Core.plugins.facebook_vn import FacebookVnPlugin
        plugin = FacebookVnPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("192.168.1.1", "IP")
        )
        assert result.is_success is False
        assert "supports username/name/phone/url" in result.error_message


# ─── Instagram Plugin ─────────────────────────────────────────────────────────

class TestInstagramPlugin:
    def test_name(self):
        from Core.plugins.instagram import InstagramPlugin
        assert InstagramPlugin().name == "Instagram"

    def test_requires_api_key(self):
        from Core.plugins.instagram import InstagramPlugin
        assert InstagramPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.instagram import InstagramPlugin
        assert InstagramPlugin().stage == 2

    def test_tos_risk(self):
        from Core.plugins.instagram import InstagramPlugin
        assert InstagramPlugin().tos_risk == "tos_risk"

    def test_unsupported_target_type(self):
        from Core.plugins.instagram import InstagramPlugin
        plugin = InstagramPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("192.168.1.1", "IP")
        )
        assert result.is_success is False

    def test_empty_username(self):
        from Core.plugins.instagram import InstagramPlugin
        plugin = InstagramPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("", "username")
        )
        assert result.is_success is False
        assert "Invalid username" in result.error_message


# ─── TikTokVn Plugin ──────────────────────────────────────────────────────────

class TestTikTokVnPlugin:
    def test_name(self):
        from Core.plugins.tiktok_vn import TikTokVnPlugin
        assert TikTokVnPlugin().name == "TikTokVn"

    def test_requires_api_key(self):
        from Core.plugins.tiktok_vn import TikTokVnPlugin
        assert TikTokVnPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.tiktok_vn import TikTokVnPlugin
        assert TikTokVnPlugin().stage == 3

    def test_tos_risk(self):
        from Core.plugins.tiktok_vn import TikTokVnPlugin
        assert TikTokVnPlugin().tos_risk == "tos_risk"

    def test_unsupported_target_type(self):
        from Core.plugins.tiktok_vn import TikTokVnPlugin
        plugin = TikTokVnPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("test@example.com", "EMAIL")
        )
        assert result.is_success is False

    def test_empty_username(self):
        from Core.plugins.tiktok_vn import TikTokVnPlugin
        plugin = TikTokVnPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("", "username")
        )
        assert result.is_success is False
        assert "Invalid username" in result.error_message


# ─── Zalo Plugin ──────────────────────────────────────────────────────────────

class TestZaloPlugin:
    def test_name(self):
        from Core.plugins.zalo import ZaloPlugin
        assert ZaloPlugin().name == "Zalo"

    def test_requires_api_key(self):
        from Core.plugins.zalo import ZaloPlugin
        assert ZaloPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.zalo import ZaloPlugin
        assert ZaloPlugin().stage == 3

    def test_tos_risk(self):
        from Core.plugins.zalo import ZaloPlugin
        assert ZaloPlugin().tos_risk == "tos_risk"

    def test_unsupported_target_type(self):
        from Core.plugins.zalo import ZaloPlugin
        plugin = ZaloPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("192.168.1.1", "IP")
        )
        assert result.is_success is False

    def test_empty_target(self):
        from Core.plugins.zalo import ZaloPlugin
        plugin = ZaloPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("", "username")
        )
        assert result.is_success is False
        assert "Invalid Zalo ID" in result.error_message


# ─── LinkedIn Plugin ──────────────────────────────────────────────────────────

class TestLinkedInPlugin:
    def test_name(self):
        from Core.plugins.linkedin import LinkedInPlugin
        assert LinkedInPlugin().name == "LinkedIn"

    def test_requires_api_key(self):
        from Core.plugins.linkedin import LinkedInPlugin
        assert LinkedInPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.linkedin import LinkedInPlugin
        assert LinkedInPlugin().stage == 3

    def test_tos_risk(self):
        from Core.plugins.linkedin import LinkedInPlugin
        assert LinkedInPlugin().tos_risk == "tos_risk"

    def test_unsupported_target_type(self):
        from Core.plugins.linkedin import LinkedInPlugin
        plugin = LinkedInPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("192.168.1.1", "IP")
        )
        assert result.is_success is False
