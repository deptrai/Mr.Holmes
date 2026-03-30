"""
tests/config/test_settings.py

Unit tests cho Core/config/settings.py — Story 4.2.

Test coverage:
    - AC1: Secrets đọc từ environment variables
    - AC4: python-dotenv loads at startup (Settings imports)
    - AC5: Non-secret settings đọc từ Configuration.ini
    - AC6: Settings class exposed via Core.config
"""
from __future__ import annotations

import os
import pytest
from configparser import ConfigParser
from unittest.mock import patch

from Core.config.settings import Settings
from Core.config import settings as singleton_settings


# ---------------------------------------------------------------------------
# AC1: Secrets load từ env vars
# ---------------------------------------------------------------------------

class TestSecretProperties:
    def test_smtp_password_from_env(self, monkeypatch) -> None:
        """AC1: smtp_password reads MH_SMTP_PASSWORD from env."""
        monkeypatch.setenv("MH_SMTP_PASSWORD", "super_secret")
        s = Settings()
        assert s.smtp_password == "super_secret"

    def test_smtp_password_default_empty(self, monkeypatch) -> None:
        """AC1: smtp_password defaults to '' when env var not set."""
        monkeypatch.delenv("MH_SMTP_PASSWORD", raising=False)
        s = Settings()
        assert s.smtp_password == ""

    def test_api_key_from_env(self, monkeypatch) -> None:
        """AC1: api_key reads MH_API_KEY."""
        monkeypatch.setenv("MH_API_KEY", "abc123")
        s = Settings()
        assert s.api_key == "abc123"

    def test_cli_password_default(self, monkeypatch) -> None:
        """AC1: cli_password defaults to 'Holmes'."""
        monkeypatch.delenv("MH_CLI_PASSWORD", raising=False)
        s = Settings()
        assert s.cli_password == "Holmes"

    def test_smtp_status_default_disabled(self, monkeypatch) -> None:
        """AC1: smtp_status defaults to 'Disabled'."""
        monkeypatch.delenv("MH_SMTP_STATUS", raising=False)
        s = Settings()
        assert s.smtp_status == "Disabled"

    def test_smtp_port_default_587(self, monkeypatch) -> None:
        """AC1: smtp_port defaults to 587."""
        monkeypatch.delenv("MH_SMTP_PORT", raising=False)
        s = Settings()
        assert s.smtp_port == 587

    def test_smtp_port_invalid_returns_default(self, monkeypatch) -> None:
        """AC1: smtp_port returns 587 when env var is not a valid integer."""
        monkeypatch.setenv("MH_SMTP_PORT", "not_a_number")
        s = Settings()
        assert s.smtp_port == 587

    def test_smtp_email_from_env(self, monkeypatch) -> None:
        """AC1: smtp_email reads MH_SMTP_EMAIL."""
        monkeypatch.setenv("MH_SMTP_EMAIL", "sender@test.com")
        s = Settings()
        assert s.smtp_email == "sender@test.com"


# ---------------------------------------------------------------------------
# AC5: Non-secret settings từ Configuration.ini
# ---------------------------------------------------------------------------

class TestIniSettings:
    def test_language_fallback_english(self) -> None:
        """AC5: language returns 'english' when .ini missing."""
        s = Settings()
        with patch.object(s, "_read_ini", return_value=ConfigParser()):
            assert s.language == "english"

    def test_date_format_fallback_eu(self) -> None:
        """AC5: date_format returns 'eu' when .ini missing."""
        s = Settings()
        with patch.object(s, "_read_ini", return_value=ConfigParser()):
            assert s.date_format == "eu"

    def test_show_logs_fallback_false(self) -> None:
        """AC5: show_logs returns False when .ini missing."""
        s = Settings()
        with patch.object(s, "_read_ini", return_value=ConfigParser()):
            assert s.show_logs is False

    def test_proxy_list_path_fallback(self) -> None:
        """AC5: proxy_list_path has reasonable default."""
        s = Settings()
        with patch.object(s, "_read_ini", return_value=ConfigParser()):
            assert s.proxy_list_path == "Proxies/Proxy_list.txt"

    def test_useragent_list_path_fallback(self) -> None:
        """AC5: useragent_list_path has reasonable default."""
        s = Settings()
        with patch.object(s, "_read_ini", return_value=ConfigParser()):
            assert s.useragent_list_path == "Useragents/Useragent.txt"


# ---------------------------------------------------------------------------
# AC6: Core.config module exposure + singleton
# ---------------------------------------------------------------------------

class TestSettingsModule:
    def test_singleton_is_settings_instance(self) -> None:
        """AC6: Core.config.settings is a Settings instance."""
        assert isinstance(singleton_settings, Settings)

    def test_smtp_configured_false_when_disabled(self, monkeypatch) -> None:
        """smtp_configured() False when status=Disabled."""
        monkeypatch.setenv("MH_SMTP_STATUS", "Disabled")
        s = Settings()
        assert s.smtp_configured() is False

    def test_smtp_configured_true_when_fully_set(self, monkeypatch) -> None:
        """smtp_configured() True when all SMTP env vars set."""
        monkeypatch.setenv("MH_SMTP_STATUS", "Enabled")
        monkeypatch.setenv("MH_SMTP_EMAIL", "sender@x.com")
        monkeypatch.setenv("MH_SMTP_PASSWORD", "pass")
        monkeypatch.setenv("MH_SMTP_DESTINATION", "dest@x.com")
        monkeypatch.setenv("MH_SMTP_SERVER", "smtp.gmail.com")
        s = Settings()
        assert s.smtp_configured() is True

    def test_smtp_configured_false_when_password_missing(self, monkeypatch) -> None:
        """smtp_configured() False when SMTP enabled but password empty."""
        monkeypatch.setenv("MH_SMTP_STATUS", "Enabled")
        monkeypatch.setenv("MH_SMTP_EMAIL", "sender@x.com")
        monkeypatch.delenv("MH_SMTP_PASSWORD", raising=False)
        s = Settings()
        assert s.smtp_configured() is False


# ---------------------------------------------------------------------------
# Integration: _read_ini reads real Configuration.ini
# ---------------------------------------------------------------------------

class TestIniIntegration:
    def test_read_ini_returns_language_from_real_file(self) -> None:
        """Integration: _read_ini() đọc Configuration/Configuration.ini và trả language."""
        s = Settings()
        # Real .ini tồn tại → language should be 'english' (default value in .ini)
        assert s.language == "english"

    def test_read_ini_caches_parser(self) -> None:
        """Patch #1 verify: _read_ini() returns same parser instance (cached)."""
        s = Settings()
        parser1 = s._read_ini()
        parser2 = s._read_ini()
        assert parser1 is parser2

