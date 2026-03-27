"""
Core/cli/output.py

OutputHandler Protocol and implementations for Mr.Holmes output abstraction.

Story 5.2 — Abstract Output Layer
AC1: OutputHandler Protocol
AC2: Methods: found(), not_found(), error(), progress(), summary()
AC3: ConsoleOutput — print-based (backward compat)
AC4: SilentOutput — no-op (batch / scripting)
"""
from __future__ import annotations

import sys
from typing import Optional

# typing_extensions fallback for Python < 3.8 Protocol support
try:
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover
    from typing_extensions import Protocol, runtime_checkable  # type: ignore

from Core.config.logging_config import get_logger

_logger = get_logger(__name__)


@runtime_checkable
class OutputHandler(Protocol):
    """
    Protocol for all OSINT output adapters.

    Implementing classes must provide all five methods.
    The default implementations are no-ops so subclassing is optional —
    only structural conformance (duck-typing) is required.
    """

    def found(self, url: str, site_name: str = "") -> None:
        """Called for each found result URL."""
        ...

    def not_found(self, site_name: str) -> None:
        """Called when a site does not match the target."""
        ...

    def error(self, message: str, exc: Optional[BaseException] = None) -> None:
        """Called to report an error during scanning."""
        ...

    def progress(self, current: int, total: int, message: str = "") -> None:
        """Called to report scan progress (site N of M)."""
        ...

    def summary(self, found: int, total: int, target: str) -> None:
        """Called once at the end with final totals."""
        ...


# ---------------------------------------------------------------------------
# ConsoleOutput — AC3
# ---------------------------------------------------------------------------

class ConsoleOutput:
    """
    Print-based output implementation (backward compatible with existing CLI).

    Uses Font.Color ANSI codes for colored output when available,
    falls back to plain stdout if Font is not importable.
    """

    def __init__(self) -> None:
        # Lazy-import Font so tests can run without the full support stack
        try:
            from Core.Support import Font
            self._green = Font.Color.GREEN
            self._red = Font.Color.RED
            self._blue = Font.Color.BLUE
            self._white = Font.Color.WHITE
            self._yellow = Font.Color.YELLOW
        except Exception:
            self._green = self._red = self._blue = self._white = self._yellow = ""

    def found(self, url: str, site_name: str = "") -> None:
        label = f"[{site_name}] " if site_name else ""
        print(
            self._green + "[+]" + self._white +
            f" {label}FOUND: {url}"
        )

    def not_found(self, site_name: str) -> None:
        # Intentionally silent in console mode to reduce noise
        pass

    def error(self, message: str, exc: Optional[BaseException] = None) -> None:
        print(
            self._red + "[!]" + self._white + f" {message}",
            file=sys.stderr,
        )
        if exc:
            _logger.debug("OutputHandler error detail", exc_info=exc)

    def progress(self, current: int, total: int, message: str = "") -> None:
        pct = int(current / total * 100) if total else 0
        suffix = f" — {message}" if message else ""
        print(
            self._blue + f"[{pct:3d}%]" + self._white +
            f" {current}/{total}{suffix}"
        )

    def summary(self, found: int, total: int, target: str) -> None:
        pct = round(found / total * 100, 1) if total else 0.0
        print(
            self._green +
            f"\n[✓] Scan complete for '{target}'" + self._white +
            f"\n    Found: {found} / {total} ({pct}%)"
        )


# ---------------------------------------------------------------------------
# SilentOutput — AC4
# ---------------------------------------------------------------------------

class SilentOutput:
    """
    No-op output implementation for batch / scripting mode.

    All methods discard their arguments silently.
    Errors are still forwarded to the logger at DEBUG level
    so they don't disappear completely.
    """

    def found(self, url: str, site_name: str = "") -> None:
        pass

    def not_found(self, site_name: str) -> None:
        pass

    def error(self, message: str, exc: Optional[BaseException] = None) -> None:
        _logger.debug("SilentOutput.error suppressed: %s", message, exc_info=exc)

    def progress(self, current: int, total: int, message: str = "") -> None:
        pass

    def summary(self, found: int, total: int, target: str) -> None:
        pass
