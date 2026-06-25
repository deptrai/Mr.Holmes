"""
tests/unit/test_dork.py

Unit tests cho Core/Dork.py — List class (Google/Yandex Dork generator).

Tests cover:
- Class structure (List class exists, has expected methods)
- Banner method dispatch
- Main() method dispatch (type1 = 1/2/3, add = 0/1)
- Dork file reading (Google_dorks.txt, Yandex_dorks.txt)
- Report generation (report path, file writes)
- GoogleDorks / YandexDorks dispatch to Dorks.Search.Generator
"""
from __future__ import annotations

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
def dork_patches():
    """Silence tất cả I/O và network khi test Dork.List."""
    patches = [
        patch("Core.Support.Language.Translation.Get_Language", return_value="English"),
        patch("Core.Support.Language.Translation.Translate_Language",
              side_effect=lambda *a, **kw: "[T]"),
        patch("Core.Support.Clear.Screen.Clear", return_value=None),
        patch("Core.Support.Banner_Selector.Random.Get_Banner", return_value=None),
        patch("Core.Support.DateFormat.Get.Format", return_value="%Y-%m-%d"),
        patch("Core.Support.Notification.Notifier.Start", return_value=None),
        patch("Core.Support.Creds.Sender.mail", return_value=None),
        patch("Core.Support.FileTransfer.Transfer.File", return_value=None),
        patch("Core.Support.Font.Color.GREEN", ""),
        patch("Core.Support.Font.Color.BLUE", ""),
        patch("Core.Support.Font.Color.WHITE", ""),
        patch("Core.Support.Font.Color.YELLOW", ""),
        patch("Core.Support.Font.Color.RED", ""),
    ]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# TestListClass — kiểm thử cấu trúc class List
# ===========================================================================
class TestListClass:
    """Verify List class structure."""

    def test_class_exists(self):
        with dork_patches():
            from Core.Dork import List
            assert List is not None

    def test_has_static_methods(self):
        with dork_patches():
            from Core.Dork import List
            for name in ("Banner", "Main", "GoogleDorks", "YandexDorks", "entities"):
                assert hasattr(List, name), f"Missing method: {name}"


# ===========================================================================
# TestBanner — List.Banner() dispatch
# ===========================================================================
class TestBanner:
    """Test Banner static method."""

    def test_banner_calls_clear_and_random(self):
        with dork_patches():
            from Core.Dork import List
            with patch("Core.Dork.Clear") as mock_clear, \
                 patch("Core.Dork.banner") as mock_banner:
                List.Banner("Desktop")
                mock_clear.Screen.Clear.assert_called_once()
                mock_banner.Random.Get_Banner.assert_called_once_with(
                    "Banners/Dorks", "Desktop"
                )

    def test_banner_mobile_mode(self):
        with dork_patches():
            from Core.Dork import List
            with patch("Core.Dork.Clear") as mock_clear, \
                 patch("Core.Dork.banner") as mock_banner:
                List.Banner("Mobile")
                mock_banner.Random.Get_Banner.assert_called_once_with(
                    "Banners/Dorks", "Mobile"
                )


# ===========================================================================
# TestGoogleDorks — List.GoogleDorks() dispatch
# ===========================================================================
class TestGoogleDorks:
    """List.GoogleDorks() phải gọi Dorks.Search.Generator() với Type=GOOGLE."""

    def test_google_dorks_type_is_google(self):
        with dork_patches():
            from Core.Dork import List
            with patch("Core.Dork.Dorks") as mock_dorks:
                List.GoogleDorks("report.txt", "phrase", "excl", "data",
                                 "dorks_list", between="None", seconddata="None")
                mock_dorks.Search.Generator.assert_called_once()
                args = mock_dorks.Search.Generator.call_args
                assert args[0][0] == "GOOGLE"

    def test_google_dorks_passes_all_params(self):
        with dork_patches():
            from Core.Dork import List
            with patch("Core.Dork.Dorks") as mock_dorks:
                List.GoogleDorks("r.txt", "user", "excl", "data",
                                 "list.txt", between="None", seconddata="None")
                args = mock_dorks.Search.Generator.call_args[0]
                assert args[0] == "GOOGLE"
                assert args[1] == "list.txt"
                assert args[2] == "r.txt"
                assert args[3] == "user"
                assert args[4] == "excl"
                assert args[5] == "data"


# ===========================================================================
# TestYandexDorks — List.YandexDorks() dispatch
# ===========================================================================
class TestYandexDorks:
    """List.YandexDorks() phải gọi Dorks.Search.Generator() với Type=YANDEX."""

    def test_yandex_dorks_type_is_yandex(self):
        with dork_patches():
            from Core.Dork import List
            with patch("Core.Dork.Dorks") as mock_dorks:
                List.YandexDorks("report.txt", "phrase", "excl", "data",
                                 "dorks_list", between="None", seconddata="None")
                mock_dorks.Search.Generator.assert_called_once()
                args = mock_dorks.Search.Generator.call_args[0]
                assert args[0] == "YANDEX"

    def test_yandex_dorks_replaces_plus_with_encoded(self):
        """YandexDorks phải thay '+' bằng '%2B' trong phrase."""
        with dork_patches():
            from Core.Dork import List
            with patch("Core.Dork.Dorks") as mock_dorks:
                List.YandexDorks("r.txt", "user+test", "excl", "data",
                                 "list.txt", between="None", seconddata="None")
                args = mock_dorks.Search.Generator.call_args[0]
                # phrase is args[3]
                assert "%2B" in args[3]
                assert "+" not in args[3]


# ===========================================================================
# TestMainReportPath — List.Main() report path construction
# ===========================================================================
class TestMainReportPath:
    """List.Main() phải tạo report tại GUI/Reports/Dorks/{username}.txt."""

    def test_main_report_path_format(self):
        """Report path phải là GUI/Reports/Dorks/{username}.txt."""
        with dork_patches():
            from Core.Dork import List
            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks"),
                patch("Core.Dork.List.YandexDorks"),
                patch("builtins.open", mock_open()) as mock_file,
                patch("builtins.input", side_effect=["1", "2", "2", ""]),
            ):
                List.Main("testuser", "Desktop")

            mock_file.assert_any_call("GUI/Reports/Dorks/testuser.txt", "a")

    def test_main_deletes_existing_report(self):
        """Khi report đã tồn tại → xóa file cũ."""
        with dork_patches():
            from Core.Dork import List
            with (
                patch("Core.Dork.os.path.isfile", return_value=True),
                patch("Core.Dork.os.remove") as mock_remove,
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks"),
                patch("Core.Dork.List.YandexDorks"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", side_effect=["1", "2", "2", ""]),
            ):
                List.Main("testuser", "Desktop")

            mock_remove.assert_called_once_with("GUI/Reports/Dorks/testuser.txt")

    def test_main_does_not_delete_when_not_exists(self):
        """Khi report chưa tồn tại → không gọi os.remove."""
        with dork_patches():
            from Core.Dork import List
            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.os.remove") as mock_remove,
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks"),
                patch("Core.Dork.List.YandexDorks"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", side_effect=["1", "2", "2", ""]),
            ):
                List.Main("testuser", "Desktop")

            mock_remove.assert_not_called()


# ===========================================================================
# TestMainDorkFileReading — type1 chọn dork file list
# ===========================================================================
class TestMainDorkFileReading:
    """
    Main() type1 selection:
    - type1 == 1 → Usernames dorks (Google_dorks.txt + Yandex_dorks.txt)
    - type1 == 2 → Phone dorks (+ Fingerprints)
    - type1 == 3 → Websites dorks
    - type1 == 4 → Usernames dorks (same as 1)
    """

    @pytest.mark.parametrize("type1_choice,expected_dork_path", [
        (1, "Site_lists/Dorks/Usernames/Google_dorks.txt"),
        (4, "Site_lists/Dorks/Usernames/Google_dorks.txt"),
        (2, "Site_lists/Dorks/Phone/Google_dorks.txt"),
        (3, "Site_lists/Dorks/Websites/Google_dorks.txt"),
    ])
    def test_main_selects_correct_google_dork_file(self, type1_choice, expected_dork_path):
        """type1 phải chọn đúng Google_dorks.txt path."""
        with dork_patches():
            from Core.Dork import List
            captured = []

            def capture_google(*args, **kwargs):
                captured.append(args[4])  # DorksList is 5th positional arg

            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks", side_effect=capture_google),
                patch("Core.Dork.List.YandexDorks"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", side_effect=[str(type1_choice), "2", "2", ""]),
            ):
                List.Main("testuser", "Desktop")

            assert expected_dork_path in captured, (
                f"type1={type1_choice} should use {expected_dork_path}, got {captured}"
            )

    @pytest.mark.parametrize("type1_choice,expected_yandex_path", [
        (1, "Site_lists/Dorks/Usernames/Yandex_dorks.txt"),
        (3, "Site_lists/Dorks/Websites/Yandex_dorks.txt"),
    ])
    def test_main_selects_correct_yandex_dork_file(self, type1_choice, expected_yandex_path):
        """type1 phải chọn đúng Yandex_dorks.txt path."""
        with dork_patches():
            from Core.Dork import List
            captured = []

            def capture_yandex(*args, **kwargs):
                captured.append(args[4])

            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks"),
                patch("Core.Dork.List.YandexDorks", side_effect=capture_yandex),
                patch("builtins.open", mock_open()),
                patch("builtins.input", side_effect=[str(type1_choice), "2", "2", ""]),
            ):
                List.Main("testuser", "Desktop")

            assert expected_yandex_path in captured, (
                f"type1={type1_choice} should use {expected_yandex_path}, got {captured}"
            )

    def test_phone_type_uses_fingerprints(self):
        """type1 == 2 phải dùng thêm Fingerprints.txt."""
        with dork_patches():
            from Core.Dork import List
            captured = []

            def capture_google(*args, **kwargs):
                captured.append(args[4])

            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks", side_effect=capture_google),
                patch("Core.Dork.List.YandexDorks"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", side_effect=["2", "2", "2", ""]),
            ):
                List.Main("testuser", "Desktop")

            assert "Site_lists/Dorks/Phone/Fingerprints.txt" in captured


# ===========================================================================
# TestMainReportGeneration — List.Main() ghi report
# ===========================================================================
class TestMainReportGeneration:
    """List.Main() phải ghi date header và by-line vào report."""

    def test_main_writes_date_header(self):
        """Main() phải ghi vào report file (date header via format)."""
        with dork_patches():
            from Core.Dork import List
            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks"),
                patch("Core.Dork.List.YandexDorks"),
                patch("builtins.open", mock_open()) as mock_file,
                patch("builtins.input", side_effect=["1", "2", "2", ""]),
            ):
                List.Main("testuser", "Desktop")

            handle = mock_file()
            # Main writes date header and by-line via Translate_Language.format()
            assert handle.write.call_count >= 2

    def test_main_calls_notification(self):
        """Main() phải gọi Notification.Notifier.Start()."""
        with dork_patches():
            from Core.Dork import List
            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks"),
                patch("Core.Dork.List.YandexDorks"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", side_effect=["1", "2", "2", ""]),
            ):
                List.Main("testuser", "Desktop")

            from Core.Support import Notification
            Notification.Notifier.Start.assert_called_once_with("Desktop")

    def test_main_calls_creds_sender(self):
        """Main() phải gọi Creds.Sender.mail()."""
        with dork_patches():
            from Core.Dork import List
            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks"),
                patch("Core.Dork.List.YandexDorks"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", side_effect=["1", "2", "2", ""]),
            ):
                List.Main("testuser", "Desktop")

            from Core.Support import Creds
            Creds.Sender.mail.assert_called_once()

    def test_main_transfer_option_1_calls_filetransfer(self):
        """Khi user chọn transfer = 1 → gọi FileTransfer.Transfer.File()."""
        with dork_patches():
            from Core.Dork import List
            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks"),
                patch("Core.Dork.List.YandexDorks"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", side_effect=["1", "2", "1", ""]),
            ):
                List.Main("testuser", "Desktop")

            from Core.Support import FileTransfer
            FileTransfer.Transfer.File.assert_called_once()

    def test_main_transfer_option_2_skips_filetransfer(self):
        """Khi user chọn transfer = 2 → KHÔNG gọi FileTransfer.Transfer.File()."""
        with dork_patches():
            from Core.Dork import List
            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks"),
                patch("Core.Dork.List.YandexDorks"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", side_effect=["1", "2", "2", ""]),
            ):
                List.Main("testuser", "Desktop")

            from Core.Support import FileTransfer
            FileTransfer.Transfer.File.assert_not_called()


# ===========================================================================
# TestMainAddParameters — Main() add parameters flow
# ===========================================================================
class TestMainAddParameters:
    """Main() với add=1 cho phép thêm parameters (date, entities)."""

    def test_main_add_option_1_calls_entities(self):
        """add=1, number=1, type=4 (custom entity) → gọi List.entities()."""
        with dork_patches():
            from Core.Dork import List
            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks"),
                patch("Core.Dork.List.YandexDorks"),
                patch("Core.Dork.List.entities") as mock_entities,
                patch("builtins.open", mock_open()),
                patch("builtins.input", side_effect=[
                    "1",   # type1 = Usernames
                    "1",   # add = yes
                    "1",   # number of params
                    "4",   # type = custom entity (else branch → entities Include)
                    "3",   # entity = custom
                    "testparam",  # param value
                    "2",   # transfer = no
                    "",
                ]),
            ):
                List.Main("testuser", "Desktop")

            mock_entities.assert_called_once()

    def test_main_add_option_0_skips_entities(self):
        """add=0 (hoặc 2) → KHÔNG gọi List.entities(), phrase = username."""
        with dork_patches():
            from Core.Dork import List
            with (
                patch("Core.Dork.os.path.isfile", return_value=False),
                patch("Core.Dork.List.Banner"),
                patch("Core.Dork.List.GoogleDorks") as mock_google,
                patch("Core.Dork.List.YandexDorks"),
                patch("Core.Dork.List.entities") as mock_entities,
                patch("builtins.open", mock_open()),
                patch("builtins.input", side_effect=["1", "2", "2", ""]),
            ):
                List.Main("testuser", "Desktop")

            mock_entities.assert_not_called()
            # GoogleDorks called with phrase = username (no params added)
            # GoogleDorks(report, phrase, exclusion, data, DorksList, ...)
            args = mock_google.call_args[0]
            assert args[1] == "testuser"
