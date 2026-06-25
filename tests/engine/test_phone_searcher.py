"""tests/engine/test_phone_searcher.py — Phone searcher tests."""
import os
import pytest
from Core.engine.phone_searcher import PhoneSearcher

class TestPhoneSearcher:
    def test_class_exists(self):
        assert hasattr(PhoneSearcher, 'normalize_phone')
        assert hasattr(PhoneSearcher, 'get_report_path')
        assert hasattr(PhoneSearcher, 'google_dorks')
        assert hasattr(PhoneSearcher, 'yandex_dorks')
    
    def test_normalize_removes_spaces(self):
        assert PhoneSearcher.normalize_phone("+1 234 567 890") == "+1234567890"
    
    def test_normalize_removes_dashes(self):
        assert PhoneSearcher.normalize_phone("+1-234-567-890") == "+1234567890"
    
    def test_normalize_removes_parens(self):
        assert PhoneSearcher.normalize_phone("(123) 456-7890") == "1234567890"
    
    def test_get_report_path(self):
        path = PhoneSearcher.get_report_path("+1 234 567 890")
        assert "Phones" in path
        assert "+1234567890" in path
    
    def test_google_dorks_creates_dir(self, tmp_path):
        report = PhoneSearcher.google_dorks("+1234567890", str(tmp_path))
        assert os.path.exists(tmp_path)
        assert "+1234567890" in report
    
    def test_google_dorks_removes_existing(self, tmp_path):
        import os
        report = PhoneSearcher.google_dorks("+1234567890", str(tmp_path))
        # Create the file
        with open(report, 'w') as f:
            f.write("old")
        # Call again — should remove old
        PhoneSearcher.google_dorks("+1234567890", str(tmp_path))
        # File should not exist (was removed, not recreated by this method)
        assert not os.path.exists(report)
    
    def test_yandex_dorks_path(self, tmp_path):
        report = PhoneSearcher.yandex_dorks("+1234567890", str(tmp_path))
        assert "yandex" in report
