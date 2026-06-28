"""Tests for Sprint 4 Vietnam government record plugins."""
from __future__ import annotations

import asyncio

import pytest


# ─── VnBusiness Plugin (enhanced) ─────────────────────────────────────────────

class TestVnBusinessPlugin:
    def test_name(self):
        from Core.plugins.vn_business import VnBusinessPlugin
        assert VnBusinessPlugin().name == "VnBusiness"

    def test_requires_api_key(self):
        from Core.plugins.vn_business import VnBusinessPlugin
        assert VnBusinessPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.vn_business import VnBusinessPlugin
        assert VnBusinessPlugin().stage == 3

    def test_tos_risk(self):
        from Core.plugins.vn_business import VnBusinessPlugin
        assert VnBusinessPlugin().tos_risk == "safe"

    def test_invalid_tax_code(self):
        from Core.plugins.vn_business import VnBusinessPlugin
        plugin = VnBusinessPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("abc", "tax_id")
        )
        assert result.is_success is False
        assert "Invalid tax code" in result.error_message

    def test_unsupported_target_type(self):
        from Core.plugins.vn_business import VnBusinessPlugin
        plugin = VnBusinessPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("test@example.com", "EMAIL")
        )
        assert result.is_success is False
        assert "supports tax_id" in result.error_message


# ─── VnLand Plugin ────────────────────────────────────────────────────────────

class TestVnLandPlugin:
    def test_name(self):
        from Core.plugins.vn_land import VnLandPlugin
        assert VnLandPlugin().name == "VnLand"

    def test_requires_api_key(self):
        from Core.plugins.vn_land import VnLandPlugin
        assert VnLandPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.vn_land import VnLandPlugin
        assert VnLandPlugin().stage == 3

    def test_tos_risk(self):
        from Core.plugins.vn_land import VnLandPlugin
        assert VnLandPlugin().tos_risk == "safe"

    def test_short_query(self):
        from Core.plugins.vn_land import VnLandPlugin
        plugin = VnLandPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("ab", "address")
        )
        assert result.is_success is False
        assert "too short" in result.error_message

    def test_unsupported_target_type(self):
        from Core.plugins.vn_land import VnLandPlugin
        plugin = VnLandPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("test@example.com", "EMAIL")
        )
        assert result.is_success is False
        assert "supports address" in result.error_message


# ─── VnVehicle Plugin ─────────────────────────────────────────────────────────

class TestVnVehiclePlugin:
    def test_name(self):
        from Core.plugins.vn_vehicle import VnVehiclePlugin
        assert VnVehiclePlugin().name == "VnVehicle"

    def test_requires_api_key(self):
        from Core.plugins.vn_vehicle import VnVehiclePlugin
        assert VnVehiclePlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.vn_vehicle import VnVehiclePlugin
        assert VnVehiclePlugin().stage == 3

    def test_tos_risk(self):
        from Core.plugins.vn_vehicle import VnVehiclePlugin
        assert VnVehiclePlugin().tos_risk == "safe"

    def test_short_plate(self):
        from Core.plugins.vn_vehicle import VnVehiclePlugin
        plugin = VnVehiclePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("AB", "license_plate")
        )
        assert result.is_success is False
        assert "Invalid license plate" in result.error_message

    def test_unsupported_target_type(self):
        from Core.plugins.vn_vehicle import VnVehiclePlugin
        plugin = VnVehiclePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("test@example.com", "EMAIL")
        )
        assert result.is_success is False
        assert "supports license_plate" in result.error_message
