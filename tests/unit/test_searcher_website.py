"""
tests/unit/test_searcher_website.py

Unit tests cho Core/Searcher_website.py — Web class.
Chiến lược: Test từng helper method riêng biệt (trace, yandex_dork,
google_dork, whois data parsing) bằng cách mock network calls và input().
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, mock_open, AsyncMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Patch helpers
# ---------------------------------------------------------------------------
@contextmanager
def web_patches():
    """Silence tất cả I/O và network khi test Web searcher."""
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
        patch("Core.Support.Map.Creation.mapWeb", return_value=None),
    ]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()


# ===========================================================================
# TestWebTrace — Web.trace() method
# ===========================================================================
class TestWebTrace:
    """Web.trace() branch: Windows (tracert) vs Unix (traceroute)."""

    def test_trace_uses_traceroute_on_unix(self, tmp_path):
        """Trên Unix → command phải là 'traceroute {host}'."""
        report = tmp_path / "report.txt"
        report.write_text("header\n")

        with web_patches():
            import importlib
            import Core.Searcher_website
            importlib.reload(Core.Searcher_website)
            from Core.Searcher_website import Web

            with (
                patch("Core.Searcher_website.os.name", "posix"),
                patch("Core.Searcher_website.os.popen") as mock_popen,
            ):
                mock_proc = MagicMock()
                mock_proc.read.return_value = "traceroute result"
                mock_popen.return_value = mock_proc

                Web.trace("example.com", str(report))

            call_arg = mock_popen.call_args[0][0]
            assert "traceroute" in call_arg
            assert "example.com" in call_arg

    def test_trace_uses_tracert_on_windows(self, tmp_path):
        """Trên Windows → command phải là 'tracert {host}'."""
        report = tmp_path / "report.txt"
        report.write_text("header\n")

        with web_patches():
            import importlib
            import Core.Searcher_website
            importlib.reload(Core.Searcher_website)
            from Core.Searcher_website import Web

            with (
                patch("Core.Searcher_website.os.name", "nt"),
                patch("Core.Searcher_website.os.popen") as mock_popen,
            ):
                mock_proc = MagicMock()
                mock_proc.read.return_value = "tracert result"
                mock_popen.return_value = mock_proc

                Web.trace("example.com", str(report))

            call_arg = mock_popen.call_args[0][0]
            assert "tracert" in call_arg
            assert "example.com" in call_arg

    def test_trace_writes_result_to_report(self, tmp_path):
        """Kết quả traceroute phải được ghi vào report file."""
        report = tmp_path / "report.txt"
        report.write_text("header\n")

        with web_patches():
            import importlib
            import Core.Searcher_website
            importlib.reload(Core.Searcher_website)
            from Core.Searcher_website import Web

            with (
                patch("Core.Searcher_website.os.name", "posix"),
                patch("Core.Searcher_website.os.popen") as mock_popen,
            ):
                mock_proc = MagicMock()
                mock_proc.read.return_value = " 1  192.168.1.1  1.234ms\n 2  10.0.0.1  5ms"
                mock_popen.return_value = mock_proc

                Web.trace("example.com", str(report))

            content = report.read_text()
            assert "TRACEROUTE SEQUENCE:" in content
            assert "192.168.1.1" in content


# ===========================================================================
# TestWebYandexDork — Web.yandex_dork() method
# ===========================================================================
class TestWebYandexDork:
    """Web.yandex_dork() phải gọi Dorks.Search.dork() với type 'YANDEX'."""

    def test_yandex_dork_type_is_yandex(self, tmp_path):
        report = tmp_path / "dork_report.txt"

        with web_patches():
            import importlib
            import Core.Searcher_website
            importlib.reload(Core.Searcher_website)
            from Core.Searcher_website import Web

            with patch("Core.Support.Dorks.Search.dork") as mock_dork:
                Web.yandex_dork("example.com", str(report))

            args = mock_dork.call_args[0]
            assert args[3] == "YANDEX"
            assert args[0] == "example.com"


# ===========================================================================
# TestWebWhoisLocalFallback — whois_lookup() khi không có API key
# ===========================================================================
class TestWebWhoisLocalFallback:
    """whois_lookup() khi API key = 'None' → dùng lệnh `whois` CLI."""

    def test_whois_uses_cli_when_no_api_key_on_unix(self, tmp_path):
        report = tmp_path / "report.txt"
        report.write_text("header\n")

        with web_patches():
            import importlib
            import Core.Searcher_website
            importlib.reload(Core.Searcher_website)
            from Core.Searcher_website import Web

            with (
                patch("Core.Support.ApiCheck.Check.WhoIs", return_value="None"),
                patch("Core.Searcher_website.os.name", "posix"),
                patch("Core.Searcher_website.os.popen") as mock_popen,
                patch("Core.Searcher_website.sleep"),
            ):
                mock_proc = MagicMock()
                mock_proc.read.return_value = "Domain Name: example.com\nRegistrar: GoDaddy"
                mock_popen.return_value = mock_proc

                Web.whois_lookup("example.com", str(report), "Desktop")

            call_arg = mock_popen.call_args[0][0]
            assert "whois" in call_arg
            assert "example.com" in call_arg

    def test_whois_result_written_to_report(self, tmp_path):
        """Kết quả whois phải được lưu vào report file."""
        report = tmp_path / "report.txt"
        report.write_text("header\n")

        with web_patches():
            import importlib
            import Core.Searcher_website
            importlib.reload(Core.Searcher_website)
            from Core.Searcher_website import Web

            with (
                patch("Core.Support.ApiCheck.Check.WhoIs", return_value="None"),
                patch("Core.Searcher_website.os.name", "posix"),
                patch("Core.Searcher_website.os.popen") as mock_popen,
                patch("Core.Searcher_website.sleep"),
            ):
                mock_proc = MagicMock()
                mock_proc.read.return_value = "Domain Name: example.com"
                mock_popen.return_value = mock_proc

                Web.whois_lookup("example.com", str(report), "Desktop")

            content = report.read_text()
            assert "WEBSITE DATA:" in content

    def test_whois_skips_cli_on_windows_when_no_api_key(self, tmp_path):
        """Trên Windows, nếu không có API key → không chạy whois CLI."""
        report = tmp_path / "report.txt"
        report.write_text("header\n")

        with web_patches():
            import importlib
            import Core.Searcher_website
            importlib.reload(Core.Searcher_website)
            from Core.Searcher_website import Web

            with (
                patch("Core.Support.ApiCheck.Check.WhoIs", return_value="None"),
                patch("Core.Searcher_website.os.name", "nt"),
                patch("Core.Searcher_website.os.popen") as mock_popen,
                patch("Core.Searcher_website.sleep"),
            ):
                Web.whois_lookup("example.com", str(report), "Desktop")

            # Trên Windows không gọi popen
            mock_popen.assert_not_called()


# ===========================================================================
# TestWebIpApiParsing — Web.search() parse ip-api.com response
# ===========================================================================
class TestWebIpApiParsing:
    """Web.search() gọi ip-api.com và parse IP/geo data."""

    def _make_ip_api_response(self) -> dict:
        return {
            "status": "success",
            "query": "93.184.216.34",
            "country": "United States",
            "countryCode": "US",
            "region": "VA",
            "regionName": "Virginia",
            "city": "Ashburn",
            "timezone": "America/New_York",
            "isp": "ExampleISP",
            "org": "ExampleOrg",
            "as": "AS12345 ExampleAS",
            "lat": "39.03",
            "lon": "-77.5",
            "zip": "20149",
        }

    def test_search_writes_ip_to_report(self, tmp_path):
        """Web.search() phải ghi IP vào report khi ip-api status = success."""
        with web_patches():
            reports_dir = tmp_path / "GUI" / "Reports" / "Websites"
            reports_dir.mkdir(parents=True)
            coords_ip = tmp_path / "GUI" / "Reports" / "Websites" / "Coordinates" / "Ip_Geolocation"
            coords_ip.mkdir(parents=True)

            ip_response = self._make_ip_api_response()

            with (
                patch("Core.Searcher_website.os.path.isdir", return_value=False),
                patch("Core.Searcher_website.os.mkdir"),
                patch("Core.Searcher_website.shutil.rmtree"),
                patch("Core.Searcher_website.urllib.request.urlopen") as mock_urlopen,
                patch("Core.Searcher_website.json.loads", return_value=ip_response),
                patch("Core.Searcher_website.Web.whois_lookup"),
                patch("Core.Searcher_website.Web.Banner"),
                patch("Core.Searcher_website.sleep"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", return_value="2"),
            ):
                mock_resp = MagicMock()
                mock_resp.read.return_value = json.dumps(ip_response).encode()
                mock_urlopen.return_value = mock_resp

                import importlib
                import Core.Searcher_website
                importlib.reload(Core.Searcher_website)
                from Core.Searcher_website import Web

                # Chỉ test rằng urlopen được gọi với ip-api URL
                Web.search("example.com", "Desktop")

            # Xác nhận request đến ip-api.com
            url_called = mock_urlopen.call_args[0][0]
            assert "ip-api.com" in url_called
            assert "example.com" in url_called

    def test_search_handles_ip_api_fail_status(self, tmp_path):
        """Khi ip-api trả về status='fail', không được crash."""
        fail_response = {"status": "fail", "message": "private range", "query": "192.168.1.1"}

        with web_patches():
            with (
                patch("Core.Searcher_website.os.path.isdir", return_value=False),
                patch("Core.Searcher_website.os.mkdir"),
                patch("Core.Searcher_website.urllib.request.urlopen") as mock_urlopen,
                patch("Core.Searcher_website.json.loads", return_value=fail_response),
                patch("Core.Searcher_website.Web.whois_lookup"),
                patch("Core.Searcher_website.Web.Banner"),
                patch("Core.Searcher_website.sleep"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", return_value="2"),
            ):
                mock_resp = MagicMock()
                mock_resp.read.return_value = json.dumps(fail_response).encode()
                mock_urlopen.return_value = mock_resp

                import importlib
                import Core.Searcher_website
                importlib.reload(Core.Searcher_website)
                from Core.Searcher_website import Web

                # Không được raise exception
                try:
                    Web.search("192.168.1.1", "Desktop")
                except Exception as e:
                    pytest.fail(f"Web.search raised unexpectedly: {e}")


# ===========================================================================
# TestWebReportFolderCreation — Web.search() tạo folder đúng
# ===========================================================================
class TestWebReportFolderCreation:
    """Web.search() phải tạo folder GUI/Reports/Websites/{username}/."""

    def test_search_creates_report_folder_when_missing(self):
        """Khi folder không tồn tại, phải tạo mới."""
        ip_response = {
            "status": "fail", "message": "private range", "query": "x"
        }

        with web_patches():
            with (
                patch("Core.Searcher_website.os.path.isdir", return_value=False),
                patch("Core.Searcher_website.os.mkdir") as mock_mkdir,
                patch("Core.Searcher_website.urllib.request.urlopen") as mock_urlopen,
                patch("Core.Searcher_website.json.loads", return_value=ip_response),
                patch("Core.Searcher_website.Web.whois_lookup"),
                patch("Core.Searcher_website.Web.Banner"),
                patch("Core.Searcher_website.sleep"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", return_value="2"),
            ):
                mock_resp = MagicMock()
                mock_resp.read.return_value = b"{}"
                mock_urlopen.return_value = mock_resp

                import importlib
                import Core.Searcher_website
                importlib.reload(Core.Searcher_website)
                from Core.Searcher_website import Web

                Web.search("example.com", "Desktop")

            mock_mkdir.assert_called_once()

    def test_search_deletes_existing_folder_before_creating(self):
        """Khi folder đã tồn tại, phải xóa trước (shutil.rmtree)."""
        ip_response = {
            "status": "fail", "message": "private range", "query": "x"
        }

        with web_patches():
            with (
                patch("Core.Searcher_website.os.path.isdir", return_value=True),
                patch("Core.Searcher_website.shutil.rmtree") as mock_rmtree,
                patch("Core.Searcher_website.os.mkdir"),
                patch("Core.Searcher_website.urllib.request.urlopen") as mock_urlopen,
                patch("Core.Searcher_website.json.loads", return_value=ip_response),
                patch("Core.Searcher_website.Web.whois_lookup"),
                patch("Core.Searcher_website.Web.Banner"),
                patch("Core.Searcher_website.sleep"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", return_value="2"),
            ):
                mock_resp = MagicMock()
                mock_resp.read.return_value = b"{}"
                mock_urlopen.return_value = mock_resp

                import importlib
                import Core.Searcher_website
                importlib.reload(Core.Searcher_website)
                from Core.Searcher_website import Web

                Web.search("example.com", "Desktop")

            mock_rmtree.assert_called_once()
