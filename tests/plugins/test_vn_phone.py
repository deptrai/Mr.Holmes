"""tests/plugins/test_vn_phone.py — Vietnamese phone plugin tests."""
import pytest
import asyncio
from Core.plugins.vn_phone import VnPhonePlugin, VN_CARRIERS

class TestVnPhonePlugin:
    def test_name(self):
        assert VnPhonePlugin().name == "VnPhone"
    
    def test_no_api_key(self):
        assert VnPhonePlugin().requires_api_key is False
    
    def test_wrong_target_type(self):
        p = VnPhonePlugin()
        result = asyncio.run(p.check("test", "username"))
        assert not result.is_success
    
    def test_viettel_detection(self):
        p = VnPhonePlugin()
        result = asyncio.run(p.check("0987654321", "phone"))
        assert result.is_success
        assert result.data["carrier"] == "viettel"
        assert result.data["is_mobile"] is True
    
    def test_mobifone_detection(self):
        p = VnPhonePlugin()
        result = asyncio.run(p.check("0901234567", "phone"))
        assert result.is_success
        assert result.data["carrier"] == "mobifone"
    
    def test_vinaphone_detection(self):
        p = VnPhonePlugin()
        result = asyncio.run(p.check("0912345678", "phone"))
        assert result.is_success
        assert result.data["carrier"] == "vinaphone"
    
    def test_plus84_normalization(self):
        p = VnPhonePlugin()
        result = asyncio.run(p.check("+84987654321", "phone"))
        assert result.is_success
        assert result.data["phone"] == "0987654321"
        assert result.data["carrier"] == "viettel"
    
    def test_84_normalization(self):
        p = VnPhonePlugin()
        result = asyncio.run(p.check("84987654321", "phone"))
        assert result.is_success
        assert result.data["phone"] == "0987654321"
    
    def test_non_vietnamese(self):
        p = VnPhonePlugin()
        result = asyncio.run(p.check("+1234567890", "phone"))
        assert not result.is_success
        assert "Not a Vietnamese" in result.error_message
    
    def test_landline_detection(self):
        p = VnPhonePlugin()
        # 024 = Hanoi landline
        result = asyncio.run(p.check("0241234567", "phone"))
        assert result.is_success
        assert result.data["is_landline"] is True
    
    def test_normalize(self):
        p = VnPhonePlugin()
        assert p.normalize_target("+84 987 654 321") == "0987654321"
    
    def test_all_carriers_have_prefixes(self):
        for carrier, info in VN_CARRIERS.items():
            assert len(info["prefixes"]) > 0
            assert "name" in info
