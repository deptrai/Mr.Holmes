"""
tests/engine/test_email_searcher.py

Unit tests cho Core/engine/email_searcher.py — EmailSearcher class.

Test coverage:
    - validate() accepts valid emails and rejects invalid ones
    - google_dorks() calls Dorks.Search.dork with GOOGLE type
    - yandex_dorks() calls Dorks.Search.dork with YANDEX type
    - search() validates then generates dorks
    - Report path construction
"""
from __future__ import annotations

import importlib
from unittest import mock

import pytest


@pytest.fixture
def email_searcher_mod():
    """Import EmailSearcher với patches active (no I/O side effects)."""
    with mock.patch("Core.engine.email_searcher.Dorks"), \
         mock.patch("Core.engine.email_searcher.Font"), \
         mock.patch("Core.engine.email_searcher.Language"), \
         mock.patch("Core.engine.email_searcher.Mail_Validator"):
        mod = importlib.import_module("Core.engine.email_searcher")
        importlib.reload(mod)
        yield mod


class TestEmailSearcherClass:
    """Verify EmailSearcher class structure."""

    def test_class_exists(self, email_searcher_mod):
        assert hasattr(email_searcher_mod, "EmailSearcher")

    def test_has_static_methods(self, email_searcher_mod):
        cls = email_searcher_mod.EmailSearcher
        for name in ("validate", "search", "google_dorks", "yandex_dorks"):
            assert hasattr(cls, name), f"Missing method: {name}"

    def test_email_regex_constant(self, email_searcher_mod):
        assert isinstance(email_searcher_mod.EmailSearcher.EMAIL_REGEX, str)
        assert "@" in email_searcher_mod.EmailSearcher.EMAIL_REGEX


class TestValidate:
    """Test validate static method."""

    def test_valid_email(self, email_searcher_mod):
        assert email_searcher_mod.EmailSearcher.validate("user@example.com") is True

    def test_valid_email_with_subdomain(self, email_searcher_mod):
        assert email_searcher_mod.EmailSearcher.validate("a.b+c@mail.example.org") is True

    def test_invalid_email_no_at(self, email_searcher_mod):
        assert email_searcher_mod.EmailSearcher.validate("notanemail") is False

    def test_invalid_email_no_domain(self, email_searcher_mod):
        assert email_searcher_mod.EmailSearcher.validate("user@") is False

    def test_invalid_email_no_tld(self, email_searcher_mod):
        assert email_searcher_mod.EmailSearcher.validate("user@example") is False

    def test_invalid_email_empty(self, email_searcher_mod):
        assert email_searcher_mod.EmailSearcher.validate("") is False


class TestGoogleDorks:
    """Test google_dorks static method."""

    def test_google_dorks_calls_dorks_search(self, email_searcher_mod):
        with mock.patch.object(email_searcher_mod, "Dorks") as mock_dorks, \
             mock.patch.object(email_searcher_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            result = email_searcher_mod.EmailSearcher.google_dorks("user@example.com")
            mock_dorks.Search.dork.assert_called_once()
            args = mock_dorks.Search.dork.call_args[0]
            assert args[0] == "user@example.com"
            assert "user@example.com_Dorks.txt" in args[1]
            assert "Google_dorks.txt" in args[2]
            assert args[3] == "GOOGLE"
            assert "user@example.com_Dorks.txt" in result

    def test_google_dorks_default_report_dir(self, email_searcher_mod):
        with mock.patch.object(email_searcher_mod, "Dorks"), \
             mock.patch.object(email_searcher_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            result = email_searcher_mod.EmailSearcher.google_dorks("a@b.com")
            assert result == "GUI/Reports/E-Mails/Dorks/a@b.com_Dorks.txt"

    def test_google_dorks_custom_report_dir(self, email_searcher_mod):
        with mock.patch.object(email_searcher_mod, "Dorks"), \
             mock.patch.object(email_searcher_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            result = email_searcher_mod.EmailSearcher.google_dorks(
                "a@b.com", report_dir="/tmp/dorks")
            assert result == "/tmp/dorks/a@b.com_Dorks.txt"

    def test_google_dorks_removes_existing_report(self, email_searcher_mod):
        with mock.patch.object(email_searcher_mod, "Dorks"), \
             mock.patch.object(email_searcher_mod.os, "path") as mock_path, \
             mock.patch.object(email_searcher_mod.os, "remove") as mock_remove, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = True
            email_searcher_mod.EmailSearcher.google_dorks("user@example.com")
            mock_remove.assert_called_once()


class TestYandexDorks:
    """Test yandex_dorks static method."""

    def test_yandex_dorks_calls_dorks_search(self, email_searcher_mod):
        with mock.patch.object(email_searcher_mod, "Dorks") as mock_dorks, \
             mock.patch.object(email_searcher_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            result = email_searcher_mod.EmailSearcher.yandex_dorks("user@example.com")
            mock_dorks.Search.dork.assert_called_once()
            args = mock_dorks.Search.dork.call_args[0]
            assert args[0] == "user@example.com"
            assert "Yandex_dorks.txt" in args[2]
            assert args[3] == "YANDEX"
            assert "user@example.com_Dorks.txt" in result

    def test_yandex_dorks_default_report_dir(self, email_searcher_mod):
        with mock.patch.object(email_searcher_mod, "Dorks"), \
             mock.patch.object(email_searcher_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            result = email_searcher_mod.EmailSearcher.yandex_dorks("a@b.com")
            assert result == "GUI/Reports/E-Mails/Dorks/a@b.com_Dorks.txt"


class TestSearch:
    """Test search static method."""

    def test_search_returns_report_path(self, email_searcher_mod):
        with mock.patch.object(email_searcher_mod, "Mail_Validator") as mock_mail, \
             mock.patch.object(email_searcher_mod, "Dorks"), \
             mock.patch.object(email_searcher_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_mail.Validator.Mail.return_value = True
            mock_path.isfile.return_value = False
            result = email_searcher_mod.EmailSearcher.search("user@example.com")
            assert "user@example.com" in result
            assert result.endswith(".txt")

    def test_search_validates_email(self, email_searcher_mod):
        with mock.patch.object(email_searcher_mod, "Mail_Validator") as mock_mail, \
             mock.patch.object(email_searcher_mod, "Dorks"), \
             mock.patch.object(email_searcher_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_mail.Validator.Mail.return_value = False
            mock_path.isfile.return_value = False
            email_searcher_mod.EmailSearcher.search("user@example.com")
            mock_mail.Validator.Mail.assert_called_once()
