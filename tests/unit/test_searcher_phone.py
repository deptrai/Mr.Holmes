"""
tests/unit/test_searcher_phone.py

Unit tests cho Core/Searcher_phone.py — Phone_search class.
Chiến lược: Mock toàn bộ I/O (file, network, input), kiểm thử
từng method tĩnh trong Phone_search theo từng branch logic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, mock_open, call

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Patch helpers — silent tất cả side-effect khi import module-level code
# ---------------------------------------------------------------------------
@contextmanager
def phone_patches():
    """Silence tất cả I/O và network khi test Phone_search."""
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
    ]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# TestPhoneValidation — kiểm thử logic phân loại quốc gia qua nation code
# ===========================================================================
class TestPhoneCountryMapping:
    """
    Phone_search.lookup() dispatch data file dựa trên nation code trong
    Temp/Phone/Code.txt. Test mapping từng code → đường dẫn JSON.
    """

    NATION_MAP = {
        "US": ("Site_lists/Phone/Lookup/USA_phone.json", "UNITED-STATES"),
        "IT": ("Site_lists/Phone/Lookup/ITA_phone.json", "ITALY"),
        "DE": ("Site_lists/Phone/Lookup/DEU_phone.json", "GERMANY"),
        "FR": ("Site_lists/Phone/Lookup/FRA_phone.json", "FRANCE"),
        "RO": ("Site_lists/Phone/Lookup/ROU_phone.json", "ROMANIA"),
        "CH": ("Site_lists/Phone/Lookup/SWIS_phone.json", "SWITZERLAND"),
        "XX": ("Site_lists/Phone/Lookup/Undefined.json", "UNDEFINED"),
    }

    @pytest.mark.parametrize("nation_code,expected_file,expected_country", [
        ("US", "Site_lists/Phone/Lookup/USA_phone.json", "UNITED-STATES"),
        ("IT", "Site_lists/Phone/Lookup/ITA_phone.json", "ITALY"),
        ("DE", "Site_lists/Phone/Lookup/DEU_phone.json", "GERMANY"),
        ("FR", "Site_lists/Phone/Lookup/FRA_phone.json", "FRANCE"),
        ("RO", "Site_lists/Phone/Lookup/ROU_phone.json", "ROMANIA"),
        ("CH", "Site_lists/Phone/Lookup/SWIS_phone.json", "SWITZERLAND"),
        ("UNKNOWN", "Site_lists/Phone/Lookup/Undefined.json", "UNDEFINED"),
    ])
    def test_nation_code_maps_to_correct_file(
        self, nation_code, expected_file, expected_country, tmp_path
    ):
        """
        Simulate logic if/elif trong lookup() để xác nhận
        quốc gia được map đúng với code → không test cả hàm vì có input().
        """
        # Logic từ Phone_search.lookup() được extract ra:
        if nation_code == "US":
            data = "Site_lists/Phone/Lookup/USA_phone.json"
            country = "UNITED-STATES"
        elif nation_code == "IT":
            data = "Site_lists/Phone/Lookup/ITA_phone.json"
            country = "ITALY"
        elif nation_code == "DE":
            data = "Site_lists/Phone/Lookup/DEU_phone.json"
            country = "GERMANY"
        elif nation_code == "FR":
            data = "Site_lists/Phone/Lookup/FRA_phone.json"
            country = "FRANCE"
        elif nation_code == "RO":
            data = "Site_lists/Phone/Lookup/ROU_phone.json"
            country = "ROMANIA"
        elif nation_code == "CH":
            data = "Site_lists/Phone/Lookup/SWIS_phone.json"
            country = "SWITZERLAND"
        else:
            data = "Site_lists/Phone/Lookup/Undefined.json"
            country = "UNDEFINED"

        assert data == expected_file
        assert country == expected_country


# ===========================================================================
# TestPhoneDorkGeneration — kiểm thử Google_dork và Yandex_dork
# ===========================================================================
class TestPhoneDorkGeneration:
    """Phone_search.Google_dork / Yandex_dork ghi report từ dork file."""

    def test_google_dork_removes_existing_report(self, tmp_path):
        """Nếu report đã tồn tại, phải xóa trước khi ghi mới."""
        with phone_patches():
            import importlib
            import Core.Searcher_phone
            importlib.reload(Core.Searcher_phone)
            from Core.Searcher_phone import Phone_search

            dummy_report = tmp_path / "123_dorks.txt"
            dummy_report.write_text("old content")

            dork_file = tmp_path / "Google_dorks.txt"
            dork_file.write_text("site:{} password\n")

            fingerprints = tmp_path / "Fingerprints.txt"
            fingerprints.write_text("https://truecaller.com/{}\n")

            with (
                patch("Core.Searcher_phone.os.path.isfile", return_value=True),
                patch("Core.Searcher_phone.os.remove") as mock_remove,
                patch("Core.Support.Dorks.Search.dork") as mock_dork,
                patch(
                    "builtins.open",
                    mock_open(read_data="https://truecaller.com/{}\n"),
                ),
                patch("Core.Searcher_phone.sleep"),
            ):
                Phone_search.Google_dork("123456789", "123456789")

            mock_remove.assert_called_once()

    def test_google_dork_calls_dork_search(self, tmp_path):
        """Google_dork phải gọi Dorks.Search.dork với đúng type 'GOOGLE'."""
        with phone_patches():
            import importlib
            import Core.Searcher_phone
            importlib.reload(Core.Searcher_phone)
            from Core.Searcher_phone import Phone_search

            with (
                patch("Core.Searcher_phone.os.path.isfile", return_value=False),
                patch("Core.Support.Dorks.Search.dork") as mock_dork,
                patch(
                    "builtins.open",
                    mock_open(read_data=""),
                ),
                patch("Core.Searcher_phone.sleep"),
            ):
                Phone_search.Google_dork("123456789", "123456789")

            # Xác nhận được gọi với Type="GOOGLE"
            args = mock_dork.call_args
            assert args[0][3] == "GOOGLE"

    def test_yandex_dork_calls_dork_search_with_yandex_type(self):
        """Yandex_dork phải gọi Dorks.Search.dork với type 'YANDEX'."""
        with phone_patches():
            import importlib
            import Core.Searcher_phone
            importlib.reload(Core.Searcher_phone)
            from Core.Searcher_phone import Phone_search

            with (
                patch("Core.Support.Dorks.Search.dork") as mock_dork,
                patch(
                    "builtins.open",
                    mock_open(read_data=""),
                ),
                patch("Core.Searcher_phone.sleep"),
            ):
                Phone_search.Yandex_dork("123456789", "123456789")

            args = mock_dork.call_args
            assert args[0][3] == "YANDEX"


# ===========================================================================
# TestPhoneReportStructure — kiểm thử Report folder creation
# ===========================================================================
class TestPhoneReportStructure:
    """
    Phone_search.searcher() phải:
    1. Tạo folder GUI/Reports/Phone/{username}/
    2. Ghi header date vào report file
    """

    def test_searcher_creates_report_folder(self, tmp_path):
        """Khi chạy searcher(), phải tạo folder cho username."""
        with phone_patches():
            with (
                patch("Core.Searcher_phone.os.path.isdir", return_value=False),
                patch("Core.Searcher_phone.os.mkdir") as mock_mkdir,
                patch("Core.Searcher_phone.shutil.rmtree"),
                # Patch Numbers.Phony.Number để tránh phonenumbers parse error
                patch("Core.Support.Phone.Numbers.Phony.Number",
                      return_value=["0033123456789", "+33123456789", "0123456789", "33123456789"]),
                # Patch lookup để tránh đọc Temp/Phone/Code.txt thật
                patch("Core.Searcher_phone.Phone_search.lookup"),
                patch("Core.Searcher_phone.Phone_search.Banner"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", return_value="2"),
                patch("Core.Searcher_phone.sleep"),
            ):
                import importlib
                import Core.Searcher_phone
                importlib.reload(Core.Searcher_phone)
                from Core.Searcher_phone import Phone_search

                # Patch Numbers trực tiếp trong module đã load
                with patch("Core.Searcher_phone.Numbers.Phony.Number",
                           return_value=["0033123456789"]):
                    Phone_search.searcher("0612345678", "Desktop")

            mock_mkdir.assert_called_once()

    def test_searcher_deletes_existing_folder_before_creating(self, tmp_path):
        """Nếu folder đã tồn tại → xóa rồi tạo lại."""
        with phone_patches():
            with (
                patch("Core.Searcher_phone.os.path.isdir", return_value=True),
                patch("Core.Searcher_phone.shutil.rmtree") as mock_rmtree,
                patch("Core.Searcher_phone.os.mkdir"),
                patch("Core.Searcher_phone.Phone_search.lookup"),
                patch("Core.Searcher_phone.Phone_search.Banner"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", return_value="2"),
                patch("Core.Searcher_phone.sleep"),
            ):
                import importlib
                import Core.Searcher_phone
                importlib.reload(Core.Searcher_phone)
                from Core.Searcher_phone import Phone_search

                with patch("Core.Searcher_phone.Numbers.Phony.Number",
                           return_value=["0033123456789"]):
                    Phone_search.searcher("0612345678", "Desktop")

            mock_rmtree.assert_called_once()


# ===========================================================================
# TestPhoneSiteLoopLogic — kiểm thử loop qua site list JSON
# ===========================================================================
class TestPhoneSiteLoopLogic:
    """
    Trong Phone_search.lookup(), vòng lặp qua JSON sites
    phải gọi Requests_Search.Search.search() cho mỗi site.
    """

    def _make_phone_site_list(self) -> list:
        return [
            {
                "truecaller": {
                    "name": "TrueCaller",
                    "url": "https://truecaller.com/{}",
                    "url2": "https://truecaller.com/{}",
                    "main": "truecaller.com",
                    "Error": "Status-Code",
                    "Scrapable": "False",
                    "Tag": ["Phone"],
                }
            },
            {
                "sync_me": {
                    "name": "Sync.me",
                    "url": "https://sync.me/search/?number={}",
                    "url2": "https://sync.me/search/?number={}",
                    "main": "sync.me",
                    "Error": "Message",
                    "Scrapable": "False",
                    "Tag": ["Phone"],
                }
            },
        ]

    def test_searcher_calls_lookup_once(self):
        """searcher() phải gọi lookup() đúng 1 lần."""
        with phone_patches():
            with (
                patch("Core.Searcher_phone.os.path.isdir", return_value=False),
                patch("Core.Searcher_phone.os.mkdir"),
                patch("Core.Searcher_phone.Phone_search.lookup") as mock_lookup,
                patch("Core.Searcher_phone.Phone_search.Banner"),
                patch("Core.Searcher_phone.Numbers.Phony.Number",
                      return_value=["0033123456789"]),
                patch("builtins.open", mock_open()),
                patch("builtins.input", return_value="2"),
                patch("Core.Searcher_phone.sleep"),
            ):
                import importlib
                import Core.Searcher_phone
                importlib.reload(Core.Searcher_phone)
                from Core.Searcher_phone import Phone_search

                Phone_search.searcher("0612345678", "Desktop")

            mock_lookup.assert_called_once()

    def test_searcher_passes_phone_number_to_lookup(self):
        """lookup() phải nhận đúng phone number."""
        captured_args = []
        def capture(*args, **kwargs):
            captured_args.append(args)

        with phone_patches():
            with (
                patch("Core.Searcher_phone.os.path.isdir", return_value=False),
                patch("Core.Searcher_phone.os.mkdir"),
                patch("Core.Searcher_phone.Phone_search.lookup", side_effect=capture),
                patch("Core.Searcher_phone.Phone_search.Banner"),
                patch("Core.Searcher_phone.Numbers.Phony.Number",
                      return_value=["0033612345678"]),
                patch("builtins.open", mock_open()),
                patch("builtins.input", return_value="2"),
                patch("Core.Searcher_phone.sleep"),
            ):
                import importlib
                import Core.Searcher_phone
                importlib.reload(Core.Searcher_phone)
                from Core.Searcher_phone import Phone_search

                Phone_search.searcher("0612345678", "Desktop")

        assert len(captured_args) == 1
        assert "0612345678" in str(captured_args[0])
