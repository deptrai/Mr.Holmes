"""Tests for Sprint 5 advanced enrichment plugins."""
from __future__ import annotations

import asyncio

import pytest


# ─── VnPhone Plugin (enhanced) ────────────────────────────────────────────────

class TestVnPhonePlugin:
    def test_name(self):
        from Core.plugins.vn_phone import VnPhonePlugin
        assert VnPhonePlugin().name == "VnPhone"

    def test_requires_api_key(self):
        from Core.plugins.vn_phone import VnPhonePlugin
        assert VnPhonePlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.vn_phone import VnPhonePlugin
        assert VnPhonePlugin().stage == 3

    def test_tos_risk(self):
        from Core.plugins.vn_phone import VnPhonePlugin
        assert VnPhonePlugin().tos_risk == "safe"

    def test_unsupported_target_type(self):
        from Core.plugins.vn_phone import VnPhonePlugin
        plugin = VnPhonePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("test@example.com", "EMAIL")
        )
        assert result.is_success is False
        assert "supports phone" in result.error_message

    def test_non_vietnamese_phone(self):
        from Core.plugins.vn_phone import VnPhonePlugin
        plugin = VnPhonePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("+1234567890", "phone")
        )
        assert result.is_success is False
        assert "Not a Vietnamese" in result.error_message

    def test_viettel_prefix(self):
        from Core.plugins.vn_phone import VnPhonePlugin
        plugin = VnPhonePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("0981234567", "phone")
        )
        assert result.is_success is True
        assert result.data["carrier"] == "viettel"
        assert result.data["is_mobile"] is True

    def test_mobifone_prefix(self):
        from Core.plugins.vn_phone import VnPhonePlugin
        plugin = VnPhonePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("0901234567", "phone")
        )
        assert result.is_success is True
        assert result.data["carrier"] == "mobifone"

    def test_plus84_normalization(self):
        from Core.plugins.vn_phone import VnPhonePlugin
        plugin = VnPhonePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("+84981234567", "phone")
        )
        assert result.is_success is True
        assert result.data["phone"] == "0981234567"


# ─── VnEmail Plugin ───────────────────────────────────────────────────────────

class TestVnEmailPlugin:
    def test_name(self):
        from Core.plugins.vn_email import VnEmailPlugin
        assert VnEmailPlugin().name == "VnEmail"

    def test_requires_api_key(self):
        from Core.plugins.vn_email import VnEmailPlugin
        assert VnEmailPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.vn_email import VnEmailPlugin
        assert VnEmailPlugin().stage == 1

    def test_tos_risk(self):
        from Core.plugins.vn_email import VnEmailPlugin
        assert VnEmailPlugin().tos_risk == "safe"

    def test_invalid_email(self):
        from Core.plugins.vn_email import VnEmailPlugin
        plugin = VnEmailPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("not-an-email", "email")
        )
        assert result.is_success is False
        assert "Invalid email format" in result.error_message

    def test_unsupported_target_type(self):
        from Core.plugins.vn_email import VnEmailPlugin
        plugin = VnEmailPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("0901234567", "phone")
        )
        assert result.is_success is False
        assert "supports email" in result.error_message


# ─── VnDomain Plugin ──────────────────────────────────────────────────────────

class TestVnDomainPlugin:
    def test_name(self):
        from Core.plugins.vn_domain import VnDomainPlugin
        assert VnDomainPlugin().name == "VnDomain"

    def test_requires_api_key(self):
        from Core.plugins.vn_domain import VnDomainPlugin
        assert VnDomainPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.vn_domain import VnDomainPlugin
        assert VnDomainPlugin().stage == 1

    def test_tos_risk(self):
        from Core.plugins.vn_domain import VnDomainPlugin
        assert VnDomainPlugin().tos_risk == "safe"

    def test_invalid_domain(self):
        from Core.plugins.vn_domain import VnDomainPlugin
        plugin = VnDomainPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("not-a-domain", "domain")
        )
        assert result.is_success is False
        assert "Invalid domain" in result.error_message

    def test_unsupported_target_type(self):
        from Core.plugins.vn_domain import VnDomainPlugin
        plugin = VnDomainPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("test@example.com", "EMAIL")
        )
        assert result.is_success is False
        assert "supports domain" in result.error_message

    def test_vn_tld_detection(self):
        from Core.plugins.vn_domain import VnDomainPlugin
        plugin = VnDomainPlugin()
        # Use a real .vn domain — will try DNS but may fail offline
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("fpt.vn", "domain")
        )
        assert result.is_success is True
        assert result.data["is_vn_tld"] is True
