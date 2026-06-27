"""tests/plugins/test_vn_business.py — Vietnamese business plugin tests."""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from Core.plugins.vn_business import VnBusinessPlugin

class TestVnBusinessPlugin:
    def test_name(self):
        p = VnBusinessPlugin()
        assert p.name == "VnBusiness"
    
    def test_no_api_key(self):
        p = VnBusinessPlugin()
        assert p.requires_api_key is False
    
    def test_stage(self):
        p = VnBusinessPlugin()
        assert p.stage == 3
    
    def test_target_types(self):
        p = VnBusinessPlugin()
        assert "tax_id" in p.target_types
    
    def test_wrong_target_type(self):
        p = VnBusinessPlugin()
        result = asyncio.run(p.check("test", "username"))
        assert not result.is_success
    
    def test_invalid_tax_code(self):
        p = VnBusinessPlugin()
        result = asyncio.run(p.check("123", "tax_id"))
        assert not result.is_success
        assert "Invalid tax code" in result.error_message
    
    def test_normalize_tax_id(self):
        p = VnBusinessPlugin()
        assert p.normalize_target("0312-345-678") == "0312345678"
    
    def test_normalize_name(self):
        p = VnBusinessPlugin()
        assert p.normalize_target("FPT Corp") == "fpt corp"
