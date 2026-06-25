"""
tests/engine/test_port_scanner_modern.py

Unit tests cho Core/engine/port_scanner_modern.py — PortScanner class.

Test coverage:
    - COMMON_PORTS constant
    - scan() with mocked socket returns open ports
    - scan() uses default ports when none provided
    - scan() respects custom port list
    - timeout handling
    - resolve_host() success and failure
"""
from __future__ import annotations

import importlib
from unittest import mock

import pytest


@pytest.fixture
def port_scanner_mod():
    """Import PortScanner (no I/O side effects at module level)."""
    mod = importlib.import_module("Core.engine.port_scanner_modern")
    importlib.reload(mod)
    yield mod


class TestPortScannerClass:
    """Verify PortScanner class structure."""

    def test_class_exists(self, port_scanner_mod):
        assert hasattr(port_scanner_mod, "PortScanner")

    def test_has_static_methods(self, port_scanner_mod):
        cls = port_scanner_mod.PortScanner
        for name in ("scan", "resolve_host"):
            assert hasattr(cls, name), f"Missing method: {name}"

    def test_common_ports_is_list(self, port_scanner_mod):
        ports = port_scanner_mod.PortScanner.COMMON_PORTS
        assert isinstance(ports, list)
        assert len(ports) > 0

    def test_common_ports_contains_80_and_443(self, port_scanner_mod):
        ports = port_scanner_mod.PortScanner.COMMON_PORTS
        assert 80 in ports
        assert 443 in ports

    def test_common_ports_all_integers(self, port_scanner_mod):
        for p in port_scanner_mod.PortScanner.COMMON_PORTS:
            assert isinstance(p, int)
            assert 0 < p < 65536


class TestScan:
    """Test scan static method."""

    def test_scan_open_port(self, port_scanner_mod):
        """scan() should return a dict for an open port."""
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.return_value = 0
        with mock.patch.object(port_scanner_mod.socket, "socket",
                               return_value=mock_sock):
            results = port_scanner_mod.PortScanner.scan(
                "example.com", ports=[80])
        assert len(results) == 1
        assert results[0]["port"] == 80
        assert results[0]["state"] == "open"
        assert results[0]["host"] == "example.com"

    def test_scan_closed_port(self, port_scanner_mod):
        """scan() should not return closed ports."""
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.return_value = 1
        with mock.patch.object(port_scanner_mod.socket, "socket",
                               return_value=mock_sock):
            results = port_scanner_mod.PortScanner.scan(
                "example.com", ports=[80])
        assert results == []

    def test_scan_uses_default_ports(self, port_scanner_mod):
        """scan() should use COMMON_PORTS when ports is None."""
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.return_value = 1
        with mock.patch.object(port_scanner_mod.socket, "socket",
                               return_value=mock_sock) as mock_socket_factory:
            port_scanner_mod.PortScanner.scan("example.com")
        assert mock_socket_factory.call_count == len(
            port_scanner_mod.PortScanner.COMMON_PORTS)

    def test_scan_custom_ports(self, port_scanner_mod):
        """scan() should respect a custom port list."""
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.return_value = 1
        with mock.patch.object(port_scanner_mod.socket, "socket",
                               return_value=mock_sock) as mock_socket_factory:
            port_scanner_mod.PortScanner.scan("example.com", ports=[22, 8080])
        assert mock_socket_factory.call_count == 2

    def test_scan_sets_timeout(self, port_scanner_mod):
        """scan() should set the socket timeout."""
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.return_value = 1
        with mock.patch.object(port_scanner_mod.socket, "socket",
                               return_value=mock_sock):
            port_scanner_mod.PortScanner.scan(
                "example.com", ports=[80], timeout=2.5)
        mock_sock.settimeout.assert_called_once_with(2.5)

    def test_scan_closes_socket(self, port_scanner_mod):
        """scan() should close each socket after probing."""
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.return_value = 1
        with mock.patch.object(port_scanner_mod.socket, "socket",
                               return_value=mock_sock):
            port_scanner_mod.PortScanner.scan("example.com", ports=[80, 443])
        assert mock_sock.close.call_count == 2

    def test_scan_handles_socket_error(self, port_scanner_mod):
        """scan() should swallow socket errors and return empty list."""
        mock_sock = mock.MagicMock()
        mock_sock.connect_ex.side_effect = port_scanner_mod.socket.error("fail")
        with mock.patch.object(port_scanner_mod.socket, "socket",
                               return_value=mock_sock):
            results = port_scanner_mod.PortScanner.scan(
                "example.com", ports=[80])
        assert results == []


class TestResolveHost:
    """Test resolve_host static method."""

    def test_resolve_host_success(self, port_scanner_mod):
        with mock.patch.object(port_scanner_mod.socket, "gethostbyname",
                               return_value="93.184.216.34"):
            result = port_scanner_mod.PortScanner.resolve_host("example.com")
        assert result == "93.184.216.34"

    def test_resolve_host_failure(self, port_scanner_mod):
        with mock.patch.object(port_scanner_mod.socket, "gethostbyname",
                               side_effect=port_scanner_mod.socket.error("fail")):
            result = port_scanner_mod.PortScanner.resolve_host("nonexistent.invalid")
        assert result is None
