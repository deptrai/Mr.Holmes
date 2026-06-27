"""tests/browser/test_stealth_context.py — Stealth browser tests."""
import pytest
from Core.browser.stealth_context import StealthBrowser, PLAYWRIGHT_AVAILABLE, USER_AGENTS, VIEWPORTS, STEALTH_JS

class TestStealthContext:
    def test_user_agents_not_empty(self):
        assert len(USER_AGENTS) >= 3
    
    def test_viewports_not_empty(self):
        assert len(VIEWPORTS) >= 3
    
    def test_stealth_js_has_webdriver(self):
        assert "webdriver" in STEALTH_JS
    
    def test_stealth_js_has_plugins(self):
        assert "plugins" in STEALTH_JS
    
    def test_stealth_js_has_chrome(self):
        assert "chrome" in STEALTH_JS
    
    def test_playwright_flag(self):
        # Just check the flag is a boolean
        assert isinstance(PLAYWRIGHT_AVAILABLE, bool)
    
    def test_stealth_browser_class_exists(self):
        assert StealthBrowser is not None
    
    def test_stealth_browser_init(self):
        sb = StealthBrowser(headless=True)
        assert sb.headless is True
        assert sb._browser is None
