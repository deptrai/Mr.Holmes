"""
Core/config/settings.py

Centralized configuration and secrets management cho Mr.Holmes.

Story 4.2 — Secrets Migration → .env + python-dotenv, Epic 4.

Design:
    - Secrets (SMTP password, API keys): load từ environment variables,
      populated via python-dotenv from .env file.
    - Non-secret settings (language, date format, log paths): vẫn đọc
      từ Configuration/Configuration.ini (AC5).
    - Fail-soft: nếu .env không tồn tại, fallback về environment variables
      (hữu ích cho Docker / CI).
    - Singleton `settings` instance dùng xuyên suốt project.

Usage:
    from Core.config import settings

    # Secrets:
    smtp_pass = settings.smtp_password
    api_key   = settings.api_key

    # Non-secret (from .ini):
    language  = settings.language
    date_fmt  = settings.date_format
"""
from __future__ import annotations

import os
from configparser import ConfigParser
from pathlib import Path

try:
    from dotenv import load_dotenv  # python-dotenv installed
    _DOTENV_AVAILABLE = True
except ImportError:
    _DOTENV_AVAILABLE = False

# ---------------------------------------------------------------------------
# Bootstrap: load .env at import time
# ---------------------------------------------------------------------------

# Resolve project root (parent of Core/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

if _DOTENV_AVAILABLE:
    # override=False → environment variables already set (e.g., Docker) take priority
    load_dotenv(_ENV_FILE, override=False)

# ---------------------------------------------------------------------------
# Configuration.ini path (non-secret settings)
# ---------------------------------------------------------------------------

_INI_FILE = _PROJECT_ROOT / "Configuration" / "Configuration.ini"


class Settings:
    """
    Centralized config access point.

    Secrets: read from environment variables (loaded from .env via dotenv).
    Non-secrets: read from Configuration/Configuration.ini.
    """

    def __init__(self) -> None:
        self._ini_parser: ConfigParser | None = None

    # ------------------------------------------------------------------
    # Secrets — from .env / environment (AC1, AC4)
    # ------------------------------------------------------------------

    @property
    def smtp_status(self) -> str:
        """SMTP enabled/disabled. Default: Disabled."""
        return os.environ.get("MH_SMTP_STATUS", "Disabled")

    @property
    def smtp_email(self) -> str:
        """SMTP sender email."""
        return os.environ.get("MH_SMTP_EMAIL", "")

    @property
    def smtp_password(self) -> str:
        """SMTP password — never stored in .ini."""
        return os.environ.get("MH_SMTP_PASSWORD", "")

    @property
    def smtp_destination(self) -> str:
        """SMTP recipient email."""
        return os.environ.get("MH_SMTP_DESTINATION", "")

    @property
    def smtp_server(self) -> str:
        """SMTP server hostname."""
        return os.environ.get("MH_SMTP_SERVER", "smtp.gmail.com")

    @property
    def smtp_port(self) -> int:
        """SMTP port."""
        try:
            return int(os.environ.get("MH_SMTP_PORT", "587"))
        except ValueError:
            return 587

    @property
    def api_key(self) -> str:
        """WhoIs / general OSINT API key."""
        return os.environ.get("MH_API_KEY", "")

    @property
    def cli_password(self) -> str:
        """CLI access password. Default: Holmes."""
        return os.environ.get("MH_CLI_PASSWORD", "Holmes")

    # ------------------------------------------------------------------
    # Non-secret settings — from Configuration.ini (AC5)
    # ------------------------------------------------------------------

    def _read_ini(self) -> ConfigParser:
        """Read Configuration.ini lazily and cache the result."""
        if self._ini_parser is None:
            self._ini_parser = ConfigParser()
            self._ini_parser.read(str(_INI_FILE))
        return self._ini_parser

    @property
    def language(self) -> str:
        """UI language. Default: english."""
        parser = self._read_ini()
        return parser.get("Settings", "language", fallback="english")

    @property
    def date_format(self) -> str:
        """Date format: 'eu' or 'us'. Default: eu."""
        parser = self._read_ini()
        return parser.get("Settings", "date_format", fallback="eu")

    @property
    def show_logs(self) -> bool:
        """Whether to show verbose logs."""
        parser = self._read_ini()
        return parser.getboolean("Settings", "show_logs", fallback=False)

    @property
    def database_enabled(self) -> bool:
        """Whether database GUI is enabled."""
        parser = self._read_ini()
        return parser.getboolean("Settings", "database", fallback=False)

    @property
    def proxy_list_path(self) -> str:
        """Path to proxy list file."""
        parser = self._read_ini()
        return parser.get("Settings", "proxy_list", fallback="Proxies/Proxy_list.txt")

    @property
    def useragent_list_path(self) -> str:
        """Path to user-agent list file."""
        parser = self._read_ini()
        return parser.get("Settings", "useragent_list", fallback="Useragents/Useragent.txt")

    # ------------------------------------------------------------------
    # Validation helper
    # ------------------------------------------------------------------

    def smtp_configured(self) -> bool:
        """Returns True only if SMTP is Enabled AND all required fields set."""
        return (
            self.smtp_status == "Enabled"
            and bool(self.smtp_email)
            and bool(self.smtp_password)
            and bool(self.smtp_destination)
            and bool(self.smtp_server)
        )


# ---------------------------------------------------------------------------
# Singleton — import and use directly
# ---------------------------------------------------------------------------

settings = Settings()
