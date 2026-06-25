"""
tests/engine/test_session_manager.py

Unit tests cho Core/engine/session_manager.py — SessionManager class.

Test coverage:
    - get_useragent() returns the configured user agent
    - get_proxy() returns the configured proxy IP
    - display_session_info() returns a dict with both
"""
from __future__ import annotations

import importlib
from unittest import mock

import pytest


@pytest.fixture
def session_manager_mod():
    """Import SessionManager với patches active (no I/O side effects)."""
    with mock.patch("Core.engine.session_manager.Useragent"), \
         mock.patch("Core.engine.session_manager.Proxies"):
        mod = importlib.import_module("Core.engine.session_manager")
        importlib.reload(mod)
        yield mod


class TestSessionManagerClass:
    """Verify SessionManager class structure."""

    def test_class_exists(self, session_manager_mod):
        assert hasattr(session_manager_mod, "SessionManager")

    def test_has_static_methods(self, session_manager_mod):
        cls = session_manager_mod.SessionManager
        for name in ("get_useragent", "get_proxy", "display_session_info"):
            assert hasattr(cls, name), f"Missing method: {name}"


class TestGetUseragent:
    """Test get_useragent static method."""

    def test_returns_useragent_string(self, session_manager_mod):
        with mock.patch.object(session_manager_mod.Useragent, "Select") as mock_sel:
            mock_sel.agent = "Mozilla/5.0 (Test Agent)"
            result = session_manager_mod.SessionManager.get_useragent()
        assert result == "Mozilla/5.0 (Test Agent)"

    def test_returns_empty_when_unset(self, session_manager_mod):
        with mock.patch.object(session_manager_mod.Useragent, "Select") as mock_sel:
            mock_sel.agent = ""
            result = session_manager_mod.SessionManager.get_useragent()
        assert result == ""


class TestGetProxy:
    """Test get_proxy static method."""

    def test_returns_proxy_ip(self, session_manager_mod):
        with mock.patch.object(session_manager_mod.Proxies, "proxy") as mock_proxy:
            mock_proxy.choice3 = "1.2.3.4"
            result = session_manager_mod.SessionManager.get_proxy()
        assert result == "1.2.3.4"

    def test_returns_proxy_string(self, session_manager_mod):
        with mock.patch.object(session_manager_mod.Proxies, "proxy") as mock_proxy:
            mock_proxy.choice3 = "10.0.0.1"
            result = session_manager_mod.SessionManager.get_proxy()
        assert isinstance(result, str)


class TestDisplaySessionInfo:
    """Test display_session_info static method."""

    def test_returns_dict_with_keys(self, session_manager_mod):
        with mock.patch.object(session_manager_mod.Useragent, "Select") as mock_sel, \
             mock.patch.object(session_manager_mod.Proxies, "proxy") as mock_proxy:
            mock_sel.agent = "TestAgent"
            mock_proxy.choice3 = "5.6.7.8"
            info = session_manager_mod.SessionManager.display_session_info()
        assert isinstance(info, dict)
        assert "useragent" in info
        assert "proxy" in info

    def test_dict_values_match(self, session_manager_mod):
        with mock.patch.object(session_manager_mod.Useragent, "Select") as mock_sel, \
             mock.patch.object(session_manager_mod.Proxies, "proxy") as mock_proxy:
            mock_sel.agent = "MyAgent/1.0"
            mock_proxy.choice3 = "9.9.9.9"
            info = session_manager_mod.SessionManager.display_session_info()
        assert info["useragent"] == "MyAgent/1.0"
        assert info["proxy"] == "9.9.9.9"

    def test_dict_consistent_with_individual_methods(self, session_manager_mod):
        with mock.patch.object(session_manager_mod.Useragent, "Select") as mock_sel, \
             mock.patch.object(session_manager_mod.Proxies, "proxy") as mock_proxy:
            mock_sel.agent = "AgentX"
            mock_proxy.choice3 = "1.1.1.1"
            info = session_manager_mod.SessionManager.display_session_info()
            ua = session_manager_mod.SessionManager.get_useragent()
            px = session_manager_mod.SessionManager.get_proxy()
        assert info["useragent"] == ua
        assert info["proxy"] == px
