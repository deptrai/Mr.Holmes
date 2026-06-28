"""Tests for v2.1 plugins: XInvoice, VnTax, VnCourt, VnNews."""
from __future__ import annotations

import asyncio
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ─── XInvoice Plugin ──────────────────────────────────────────────────────────

class TestXInvoicePlugin:
    def test_name(self):
        from Core.plugins.xinvoice import XInvoicePlugin
        assert XInvoicePlugin().name == "XInvoice"

    def test_requires_api_key(self):
        from Core.plugins.xinvoice import XInvoicePlugin
        assert XInvoicePlugin().requires_api_key is True

    def test_stage(self):
        from Core.plugins.xinvoice import XInvoicePlugin
        assert XInvoicePlugin().stage == 3

    def test_invalid_tax_code(self):
        from Core.plugins.xinvoice import XInvoicePlugin
        plugin = XInvoicePlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("abc", "tax_id")
        )
        assert result.is_success is False
        assert "Invalid tax code" in result.error_message

    def test_missing_api_key(self):
        from Core.plugins.xinvoice import XInvoicePlugin
        with patch.dict(os.environ, {"MH_XINVOICE_API_KEY": ""}):
            plugin = XInvoicePlugin()
            result = asyncio.get_event_loop().run_until_complete(
                plugin.check("0101248141", "tax_id")
            )
            assert result.is_success is False
            assert "MH_XINVOICE_API_KEY not configured" in result.error_message


# ─── VnTax Plugin ─────────────────────────────────────────────────────────────

class TestVnTaxPlugin:
    def test_name(self):
        from Core.plugins.vntax import VnTaxPlugin
        assert VnTaxPlugin().name == "VnTax"

    def test_requires_api_key(self):
        from Core.plugins.vntax import VnTaxPlugin
        assert VnTaxPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.vntax import VnTaxPlugin
        assert VnTaxPlugin().stage == 3

    def test_invalid_tax_code(self):
        from Core.plugins.vntax import VnTaxPlugin
        plugin = VnTaxPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("abc", "tax_id")
        )
        assert result.is_success is False
        assert "Invalid tax code" in result.error_message

    def test_unsupported_target_type(self):
        from Core.plugins.vntax import VnTaxPlugin
        plugin = VnTaxPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("test@example.com", "EMAIL")
        )
        assert result.is_success is False


# ─── VnCourt Plugin ───────────────────────────────────────────────────────────

class TestVnCourtPlugin:
    def test_name(self):
        from Core.plugins.vncourt import VnCourtPlugin
        assert VnCourtPlugin().name == "VnCourt"

    def test_requires_api_key(self):
        from Core.plugins.vncourt import VnCourtPlugin
        assert VnCourtPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.vncourt import VnCourtPlugin
        assert VnCourtPlugin().stage == 3

    def test_short_query(self):
        from Core.plugins.vncourt import VnCourtPlugin
        plugin = VnCourtPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("a", "name")
        )
        assert result.is_success is False
        assert "too short" in result.error_message

    def test_unsupported_target_type(self):
        from Core.plugins.vncourt import VnCourtPlugin
        plugin = VnCourtPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("test", "EMAIL")
        )
        assert result.is_success is False


# ─── VnNews Plugin ────────────────────────────────────────────────────────────

class TestVnNewsPlugin:
    def test_name(self):
        from Core.plugins.vnnews import VnNewsPlugin
        assert VnNewsPlugin().name == "VnNews"

    def test_requires_api_key(self):
        from Core.plugins.vnnews import VnNewsPlugin
        assert VnNewsPlugin().requires_api_key is False

    def test_stage(self):
        from Core.plugins.vnnews import VnNewsPlugin
        assert VnNewsPlugin().stage == 2

    def test_short_query(self):
        from Core.plugins.vnnews import VnNewsPlugin
        plugin = VnNewsPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("a", "name")
        )
        assert result.is_success is False
        assert "too short" in result.error_message

    def test_unsupported_target_type(self):
        from Core.plugins.vnnews import VnNewsPlugin
        plugin = VnNewsPlugin()
        result = asyncio.get_event_loop().run_until_complete(
            plugin.check("test", "IP")
        )
        assert result.is_success is False
