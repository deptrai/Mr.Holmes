"""
tests/unit/test_email_searcher.py

Unit tests cho Core/E_Mail.py — Mail_search class.
Chiến lược: Mock smtp, requests, file I/O, input().
Test validate email regex và site loop logic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, mock_open

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Patch helpers
# ---------------------------------------------------------------------------
@contextmanager
def email_patches():
    """Silence tất cả I/O và network khi test Mail_search."""
    patches = [
        patch("Core.Support.Language.Translation.Get_Language", return_value="English"),
        patch("Core.Support.Language.Translation.Translate_Language",
              side_effect=lambda *a, **kw: "[T]"),
        patch("Core.Support.Clear.Screen.Clear", return_value=None),
        patch("Core.Support.Banner_Selector.Random.Get_Banner", return_value=None),
        patch("Core.Support.Logs.Log.Checker", return_value=None),
        patch("Core.Support.Notification.Notifier.Start", return_value=None),
        patch("Core.Support.Creds.Sender.mail", return_value=None),
        patch("Core.Support.Encoding.Encoder.Encode", return_value=None),
        patch("Core.Support.FileTransfer.Transfer.File", return_value=None),
        patch("Core.Support.DateFormat.Get.Format", return_value="%Y-%m-%d"),
        patch("Core.Support.Font.Color.GREEN", ""),
        patch("Core.Support.Font.Color.BLUE", ""),
        patch("Core.Support.Font.Color.WHITE", ""),
        patch("Core.Support.Font.Color.YELLOW", ""),
        patch("Core.Support.Font.Color.RED", ""),
        patch("Core.Support.ApiCheck.Check.WhoIs", return_value="None"),
    ]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# TestEmailValidation — kiểm thử Validator.Mail() regex logic
# ===========================================================================
class TestEmailValidation:
    """
    Mail_Validator.Validator.Mail() kiểm tra email có hợp lệ không.
    Regex pattern 1: standard RFC email format.
    """

    VALID_EMAILS = [
        "user@example.com",
        "user.name+tag+sorting@example.com",
        "user@subdomain.example.com",
        "user123@example.co.uk",
        "test@gmail.com",
        "hello@world.org",
    ]

    INVALID_EMAILS = [
        "plainaddress",
        "@missinguser.com",
        "user@.com",
        "user@com",
        "user space@example.com",
    ]

    @pytest.mark.parametrize("email", VALID_EMAILS)
    def test_regex_accepts_valid_emails(self, email, tmp_path):
        """Pattern chuẩn phải match các địa chỉ email hợp lệ."""
        import re

        report = tmp_path / "report.txt"
        report.write_text("")

        symbols = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        assert re.fullmatch(symbols, email) is not None, (
            f"Expected valid email '{email}' to match regex"
        )

    @pytest.mark.parametrize("email", INVALID_EMAILS)
    def test_regex_rejects_invalid_emails(self, email, tmp_path):
        """Pattern chuẩn phải reject các email không hợp lệ."""
        import re

        report = tmp_path / "report.txt"
        report.write_text("")

        symbols = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        assert re.fullmatch(symbols, email) is None, (
            f"Expected invalid email '{email}' to be rejected by regex"
        )

    def test_validator_mail_writes_valid_to_report(self, tmp_path):
        """Khi email valid → ghi 'THIS EMAIL IS VALID' vào report."""
        report = tmp_path / "email_report.txt"
        report.write_text("")

        with email_patches():
            import importlib
            import Core.Support.Mail.Mail_Validator
            importlib.reload(Core.Support.Mail.Mail_Validator)
            from Core.Support.Mail.Mail_Validator import Validator

            with patch("Core.Support.Mail.Mail_Validator.sleep"):
                result = Validator.Mail("user@example.com", str(report))

        assert result is True
        content = report.read_text()
        assert "THIS EMAIL IS VALID" in content

    def test_validator_mail_writes_invalid_to_report(self, tmp_path):
        """Khi email invalid → ghi 'THIS EMAIL IS NOT VALID' vào report."""
        report = tmp_path / "email_report.txt"
        report.write_text("")

        with email_patches():
            import importlib
            import Core.Support.Mail.Mail_Validator
            importlib.reload(Core.Support.Mail.Mail_Validator)
            from Core.Support.Mail.Mail_Validator import Validator

            with (
                patch("Core.Support.Mail.Mail_Validator.sleep"),
                patch("builtins.input", return_value=""),
            ):
                result = Validator.Mail("not-an-email", str(report))

        assert result is False
        content = report.read_text()
        assert "THIS EMAIL IS NOT VALID" in content

    def test_validator_mail_returns_true_for_valid(self, tmp_path):
        """Return True khi email hợp lệ."""
        report = tmp_path / "r.txt"
        report.write_text("")

        with email_patches():
            import importlib
            import Core.Support.Mail.Mail_Validator
            importlib.reload(Core.Support.Mail.Mail_Validator)
            from Core.Support.Mail.Mail_Validator import Validator

            with patch("Core.Support.Mail.Mail_Validator.sleep"):
                result = Validator.Mail("test@gmail.com", str(report))

        assert result is True

    def test_validator_mail_returns_false_for_invalid(self, tmp_path):
        """Return False khi email không hợp lệ."""
        report = tmp_path / "r.txt"
        report.write_text("")

        with email_patches():
            import importlib
            import Core.Support.Mail.Mail_Validator
            importlib.reload(Core.Support.Mail.Mail_Validator)
            from Core.Support.Mail.Mail_Validator import Validator

            with (
                patch("Core.Support.Mail.Mail_Validator.sleep"),
                patch("builtins.input", return_value=""),
            ):
                result = Validator.Mail("invalid", str(report))

        assert result is False


# ===========================================================================
# TestEmailReportFolder — Mail_search.Search() tạo folder
# ===========================================================================
class TestEmailReportFolder:
    """Mail_search.Search() phải tạo/overwrite folder GUI/Reports/Email/{email}/."""

    def test_search_creates_email_folder_if_not_exists(self):
        """Khi folder chưa tồn tại → tạo mới."""
        with email_patches():
            with (
                patch("Core.E_Mail.os.path.isfile", return_value=False),
                patch("Core.E_Mail.os.mkdir") as mock_mkdir,
                patch("Core.E_Mail.mail.Validator"),
                patch("Core.E_Mail.Mail_search.Banner"),
                patch("Core.E_Mail.Mail_search.searcher"),
                patch("builtins.open", mock_open(read_data="[]")),
                patch("builtins.input", side_effect=["2", "2", "2", ""]),
            ):
                from Core.E_Mail import Mail_search
                Mail_search.Search("user@example.com", "Desktop")

            mock_mkdir.assert_called_once()

    def test_search_deletes_existing_folder_first(self):
        """Khi folder đã tồn tại → xóa rồi tạo lại."""
        with email_patches():
            with (
                patch("Core.E_Mail.os.path.isfile", return_value=True),
                patch("Core.E_Mail.os.remove") as mock_remove,
                patch("Core.E_Mail.os.mkdir"),
                patch("Core.E_Mail.mail.Validator"),
                patch("Core.E_Mail.Mail_search.Banner"),
                patch("Core.E_Mail.Mail_search.searcher"),
                patch("builtins.open", mock_open(read_data="[]")),
                patch("builtins.input", side_effect=["2", "2", "2", ""]),
            ):
                from Core.E_Mail import Mail_search
                Mail_search.Search("user@example.com", "Desktop")

            mock_remove.assert_called_once()


# ===========================================================================
# TestEmailSiteLookup — Mail_search.Search() site loop
# ===========================================================================
class TestEmailSiteLookup:
    """Mail_search.Search() vòng lặp qua JSON site list."""

    def _make_email_site_list(self) -> list:
        return [
            {
                "haveibeenpwned": {
                    "name": "HaveIBeenPwned",
                    "url": "https://haveibeenpwned.com/account/{}",
                    "main": "haveibeenpwned.com",
                    "Error": "Oh no",
                    "Scrapable": "False",
                    "Tag": ["Email"],
                }
            },
            {
                "ghostproject": {
                    "name": "GhostProject",
                    "url": "https://ghostproject.fr/?a={}",
                    "main": "ghostproject.fr",
                    "Error": "Message",
                    "Scrapable": "False",
                    "Tag": ["Email"],
                }
            },
        ]

    def test_search_writes_links_for_each_site(self):
        """Mỗi site trong list phải được ghi vào file report."""
        site_list = self._make_email_site_list()

        with email_patches():
            with (
                patch("Core.E_Mail.os.path.isfile", return_value=False),
                patch("Core.E_Mail.os.mkdir"),
                patch("Core.E_Mail.Mail_search.Banner"),
                patch("Core.E_Mail.mail.Validator", return_value=MagicMock(
                    Mail=MagicMock(return_value=True)
                )),
                patch("json.loads", return_value=site_list),
                patch("builtins.open", mock_open(read_data=json.dumps(site_list))) as mock_file,
                patch("builtins.input", side_effect=["2", "2", "2", ""]),
            ):
                from Core.E_Mail import Mail_search
                with patch("Core.E_Mail.mail.Validator.Mail", return_value=True):
                    Mail_search.Search("user@example.com", "Desktop")

                # The links should be generated in the report file
                written = "".join([str(call.args[0]) for call in mock_file().write.mock_calls])
                assert "https://haveibeenpwned.com/account/user@example.com" in written
                assert "https://ghostproject.fr/?a=user@example.com" in written

    def test_search_aborts_when_email_invalid(self):
        """Khi Validator.Mail() = False → không chạy site loop."""
        with email_patches():
            with (
                patch("Core.E_Mail.os.path.isfile", return_value=False),
                patch("Core.E_Mail.os.mkdir"),
                patch("Core.E_Mail.Mail_search.Banner"),
                patch("Core.E_Mail.Mail_search.searcher") as mock_searcher,
                patch("builtins.open", mock_open(read_data="[]")),
                patch("builtins.input", side_effect=["2", "2", "2", ""]),
            ):
                from Core.E_Mail import Mail_search

                with patch("Core.E_Mail.mail.Validator.Mail", return_value=False) as mock_validator_mail:
                    Mail_search.Search("notvalid", "Desktop")

            # Không gọi searcher vì email không hợp lệ
            mock_searcher.assert_not_called()


# ===========================================================================
# TestEmailGoogleDork — Google_dork() method
# ===========================================================================
class TestEmailGoogleDork:
    """Mail_search.Google_dork() phải gọi Dorks.Search.dork() với type GOOGLE."""

    def test_google_dork_type_is_correct(self):
        with email_patches():
            import importlib
            import Core.E_Mail
            importlib.reload(Core.E_Mail)
            from Core.E_Mail import Mail_search

            with (
                patch("Core.E_Mail.os.path.isfile", return_value=False),
                patch("Core.Support.Dorks.Search.dork") as mock_dork,
                patch("builtins.open", mock_open(read_data="")),
            ):
                Mail_search.Google_dork("user@example.com")

            args = mock_dork.call_args[0]
            assert args[3] == "GOOGLE"

    def test_google_dork_uses_email_as_param(self):
        """Email phải được truyền đúng vào dork()."""
        with email_patches():
            import importlib
            import Core.E_Mail
            importlib.reload(Core.E_Mail)
            from Core.E_Mail import Mail_search

            with (
                patch("Core.E_Mail.os.path.isfile", return_value=False),
                patch("Core.Support.Dorks.Search.dork") as mock_dork,
                patch("builtins.open", mock_open(read_data="")),
            ):
                Mail_search.Google_dork("test@example.com")

            args = mock_dork.call_args[0]
            assert args[0] == "test@example.com"
