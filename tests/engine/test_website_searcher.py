"""tests/engine/test_website_searcher.py — Website searcher tests."""
import os
import platform
import pytest
from Core.engine.website_searcher import WebsiteSearcher

class TestWebsiteSearcher:
    def test_class_exists(self):
        for m in ('get_report_path', 'traceroute_command', 'google_dorks', 'yandex_dorks'):
            assert hasattr(WebsiteSearcher, m)
    
    def test_get_report_path_strips_protocol(self):
        path = WebsiteSearcher.get_report_path("https://example.com")
        assert "example.com" in path
        assert "https://" not in path
    
    def test_get_report_path_strips_http(self):
        path = WebsiteSearcher.get_report_path("http://test.org")
        assert "test.org" in path
    
    def test_traceroute_command_unix(self):
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(platform, 'system', lambda: 'Linux')
            cmd = WebsiteSearcher.traceroute_command("example.com")
            assert cmd[0] == "traceroute"
            assert cmd[1] == "example.com"
    
    def test_traceroute_command_windows(self):
        with pytest.MonkeyPatch().context() as mp:
            mp.setattr(platform, 'system', lambda: 'Windows')
            cmd = WebsiteSearcher.traceroute_command("example.com")
            assert cmd[0] == "tracert"
    
    def test_google_dorks_creates_dir(self, tmp_path):
        report = WebsiteSearcher.google_dorks("example.com", str(tmp_path))
        assert os.path.exists(tmp_path)
        assert "example.com" in report
    
    def test_yandex_dorks_path(self, tmp_path):
        report = WebsiteSearcher.yandex_dorks("example.com", str(tmp_path))
        assert "yandex" in report
