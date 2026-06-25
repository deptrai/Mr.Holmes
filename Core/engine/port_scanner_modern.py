"""
Core/engine/port_scanner_modern.py

Modern port scanner — extracted from legacy Core/Port_Scanner.py and
Core/Support/Websites/Scanner.py. Scans common ports on a host and
returns structured results without interactive prompts.

Phase-out Phase 1 — PortScanner replaces Core.Port_Scanner.Ports.
"""
from __future__ import annotations

import socket
from typing import Optional

_logger = None


def _logger():
    """Lazy logger để tránh module-level I/O side effects."""
    global _logger
    if _logger is None:
        from Core.config.logging_config import get_logger
        _logger = get_logger(__name__)
    return _logger


class PortScanner:
    """
    Port scanning utilities.

    Replaces legacy Core.Port_Scanner.Ports and Core.Support.Websites.Scanner.
    """

    COMMON_PORTS = [21, 22, 23, 25, 53, 80, 110, 143, 443, 993, 995, 8080]

    @staticmethod
    def scan(
        host: str,
        ports: list[int] | None = None,
        timeout: float = 1.0,
    ) -> list[dict]:
        """Scan ports on host. Returns list of open port dicts.

        Args:
            host: Target hostname or IP address.
            ports: List of ports to scan. Defaults to COMMON_PORTS.
            timeout: Socket timeout in seconds.

        Returns:
            List of dicts with keys ``host``, ``port``, ``state`` for each
            open port.
        """
        if ports is None:
            ports = PortScanner.COMMON_PORTS
        results: list[dict] = []
        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            try:
                result = sock.connect_ex((host, port))
                if result == 0:
                    results.append({
                        "host": host,
                        "port": port,
                        "state": "open",
                    })
            except (socket.error, OSError):
                pass
            finally:
                sock.close()
        return results

    @staticmethod
    def resolve_host(host: str) -> Optional[str]:
        """Resolve hostname to IP address.

        Args:
            host: Target hostname.

        Returns:
            IP address string or None if resolution fails.
        """
        try:
            return socket.gethostbyname(host)
        except socket.error:
            return None
