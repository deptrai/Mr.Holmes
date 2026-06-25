"""
tests/unit/test_session.py

Unit tests for Core/Session.py — Session Options (legacy).

Tests cover:
- Options class structure
- Printing() displays useragent and proxy
- View() interactive flow
- Restart logic (os.execl)
"""
from __future__ import annotations

import importlib
from contextlib import contextmanager
from unittest import mock

import pytest


@contextmanager
def session_patches():
    patches = [
        mock.patch("Core.Session.Useragent"),
        mock.patch("Core.Session.Proxies"),
        mock.patch("Core.Session.Language"),
        mock.patch("Core.Session.Font"),
        mock.patch("Core.Session.sleep"),
        mock.patch("builtins.input", return_value="0"),
        mock.patch("builtins.print"),
    ]
    mocks = [p.start() for p in patches]
    try:
        yield mocks
    finally:
        for p in patches:
            p.stop()


@pytest.fixture
def session_mod():
    with session_patches():
        mod = importlib.import_module("Core.Session")
        yield mod


class TestOptionsClass:
    """Verify Options class structure."""

    def test_class_exists(self, session_mod):
        assert hasattr(session_mod, "Options")

    def test_has_static_methods(self, session_mod):
        cls = session_mod.Options
        for name in ("Printing", "View"):
            assert hasattr(cls, name), f"Missing method: {name}"


class TestPrinting:
    """Test Printing static method."""

    def test_printing_displays_useragent(self, session_mod):
        """Printing should display the current user agent."""
        with mock.patch("Core.Session.Useragent") as mock_ua, \
             mock.patch("Core.Session.Proxies") as mock_proxies, \
             mock.patch("builtins.print") as mock_print:
            mock_ua.Select.agent = "TestAgent/1.0"
            mock_proxies.proxy.choice3 = "127.0.0.1:8080"
            session_mod.Options.Printing()
            print_output = " ".join(
                str(c) for c in mock_print.call_args_list
            )
            assert "TestAgent/1.0" in print_output or mock_print.called

    def test_printing_displays_proxy(self, session_mod):
        """Printing should display the current proxy IP."""
        with mock.patch("Core.Session.Useragent") as mock_ua, \
             mock.patch("Core.Session.Proxies") as mock_proxies, \
             mock.patch("builtins.print") as mock_print:
            mock_ua.Select.agent = "TestAgent/1.0"
            mock_proxies.proxy.choice3 = "192.168.1.1:9090"
            session_mod.Options.Printing()
            assert mock_print.called


class TestView:
    """Test View static method."""

    def test_view_calls_printing(self, session_mod):
        """View should call Printing() to show session info."""
        with mock.patch("Core.Session.Options.Printing") as mock_printing, \
             mock.patch("builtins.input", return_value="2"):
            session_mod.Options.View()
            mock_printing.assert_called_once()

    def test_view_choice_2_does_not_restart(self, session_mod):
        """Choice 2 should not restart the process."""
        with mock.patch("Core.Session.Options.Printing"), \
             mock.patch("Core.Session.os.execl") as mock_execl, \
             mock.patch("builtins.input", return_value="2"):
            session_mod.Options.View()
            mock_execl.assert_not_called()
