"""
tests/unit/test_port_scanner.py

Unit tests cho Core/Port_Scanner.py (Ports class) và
Core/Support/Websites/Scanner.py (Port class).
Chiến lược: Mock socket, input(), file I/O.
"""
from __future__ import annotations

import socket
import sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, mock_open, call

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Patch helpers
# ---------------------------------------------------------------------------
@contextmanager
def port_patches():
    """Silence tất cả I/O và network khi test Port scanner."""
    patches = [
        patch("Core.Support.Language.Translation.Get_Language", return_value="English"),
        patch("Core.Support.Language.Translation.Translate_Language",
              side_effect=lambda *a, **kw: "[T]"),
        patch("Core.Support.Clear.Screen.Clear", return_value=None),
        patch("Core.Support.Banner_Selector.Random.Get_Banner", return_value=None),
        patch("Core.Support.DateFormat.Get.Format", return_value="%Y-%m-%d"),

        patch("Core.Support.Logs.Log.Checker", return_value=None),
        patch("Core.Support.Notification.Notifier.Start", return_value=None),
        patch("Core.Support.Creds.Sender.mail", return_value=None),
        patch("Core.Support.Encoding.Encoder.Encode", return_value=None),
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
# TestPortGetPort — Port.Get_Port() tại tầng Scanner.py
# ===========================================================================
class TestPortGetPort:
    """
    Port.Get_Port() kiểm tra 1 port cụ thể:
    - connect_ex() = 0 → OPEN → append to list, write report
    - connect_ex() != 0 → CLOSED → không append
    """

    def test_open_port_appends_to_list_and_writes_report(self, tmp_path):
        """Port mở → thêm vào Open_Ports list và ghi vào report."""
        report = tmp_path / "ports_report.txt"
        report.write_text("")

        with port_patches():
            import importlib
            import Core.Support.Websites.Scanner
            importlib.reload(Core.Support.Websites.Scanner)
            from Core.Support.Websites.Scanner import Port

            open_ports = []
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0  # OPEN

            with patch("Core.Support.Websites.Scanner.socket.socket",
                       return_value=mock_socket):
                Port.Get_Port("example.com", str(report), 80, open_ports)

        assert 80 in open_ports
        content = report.read_text()
        assert "Port: 80" in content

    def test_closed_port_not_appended_to_list(self, tmp_path):
        """Port đóng → KHÔNG thêm vào Open_Ports list."""
        report = tmp_path / "ports_report.txt"
        report.write_text("")

        with port_patches():
            import importlib
            import Core.Support.Websites.Scanner
            importlib.reload(Core.Support.Websites.Scanner)
            from Core.Support.Websites.Scanner import Port

            open_ports = []
            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 111  # CLOSED

            with patch("Core.Support.Websites.Scanner.socket.socket",
                       return_value=mock_socket):
                Port.Get_Port("example.com", str(report), 443, open_ports)

        assert 443 not in open_ports
        content = report.read_text()
        assert "Port: 443" not in content

    def test_closed_port_does_not_write_to_report(self, tmp_path):
        """Port đóng → report file không bị thay đổi."""
        report = tmp_path / "ports_report.txt"
        report.write_text("header\n")
        original_content = report.read_text()

        with port_patches():
            import importlib
            import Core.Support.Websites.Scanner
            importlib.reload(Core.Support.Websites.Scanner)
            from Core.Support.Websites.Scanner import Port

            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 1  # CLOSED

            with patch("Core.Support.Websites.Scanner.socket.socket",
                       return_value=mock_socket):
                Port.Get_Port("example.com", str(report), 22, [])

        assert report.read_text() == original_content

    def test_multiple_ports_some_open_some_closed(self, tmp_path):
        """Nhiều port: chỉ port open mới vào list và report."""
        report = tmp_path / "ports_report.txt"
        report.write_text("")

        port_states = {80: 0, 443: 0, 22: 1, 3306: 1}  # 80,443 open; 22,3306 closed

        with port_patches():
            import importlib
            import Core.Support.Websites.Scanner
            importlib.reload(Core.Support.Websites.Scanner)
            from Core.Support.Websites.Scanner import Port

            open_ports = []
            for port_num, state in port_states.items():
                mock_socket = MagicMock()
                mock_socket.connect_ex.return_value = state
                with patch("Core.Support.Websites.Scanner.socket.socket",
                           return_value=mock_socket):
                    Port.Get_Port("example.com", str(report), port_num, open_ports)

        assert 80 in open_ports
        assert 443 in open_ports
        assert 22 not in open_ports
        assert 3306 not in open_ports

        content = report.read_text()
        assert "Port: 80" in content
        assert "Port: 443" in content
        assert "Port: 22" not in content
        assert "Port: 3306" not in content

    def test_socket_settimeout_called_with_2_seconds(self, tmp_path):
        """Socket phải có timeout = 2 giây."""
        report = tmp_path / "ports_report.txt"
        report.write_text("")

        with port_patches():
            import importlib
            import Core.Support.Websites.Scanner
            importlib.reload(Core.Support.Websites.Scanner)
            from Core.Support.Websites.Scanner import Port

            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0

            with patch("Core.Support.Websites.Scanner.socket.socket",
                       return_value=mock_socket):
                Port.Get_Port("example.com", str(report), 80, [])

        mock_socket.settimeout.assert_called_once_with(2)

    def test_socket_is_closed_after_check(self, tmp_path):
        """Socket phải được close() sau khi check port (resource leak prevention)."""
        report = tmp_path / "ports_report.txt"
        report.write_text("")

        with port_patches():
            import importlib
            import Core.Support.Websites.Scanner
            importlib.reload(Core.Support.Websites.Scanner)
            from Core.Support.Websites.Scanner import Port

            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 111

            with patch("Core.Support.Websites.Scanner.socket.socket",
                       return_value=mock_socket):
                Port.Get_Port("example.com", str(report), 8080, [])

        mock_socket.close.assert_called_once()


# ===========================================================================
# TestPortScannerMain — Ports.Main() trong Core/Port_Scanner.py
# ===========================================================================
class TestPortScannerMain:
    """
    Ports.Main() điều phối toàn bộ flow scan:
    - Tạo report folder
    - Gọi Scanner.Port.Scan() với đúng target
    - Gọi dorks nếu user chọn
    """

    def test_main_writes_to_report_file(self):
        """Ports.Main() phải ghi vào file GUI/Reports/Ports/{target}.txt."""
        with port_patches():
            with (
                patch("Core.Port_Scanner.os.path.exists", return_value=False),
                patch("Core.Port_Scanner.os.remove") as mock_remove,
                patch("Core.Port_Scanner.Scanner.Port.Scan"),
                patch("Core.Port_Scanner.Ports.Banner"),
                patch("builtins.open", mock_open()) as mock_file,
                patch("builtins.input", return_value="2"),
            ):
                from Core.Port_Scanner import Ports
                Ports.Main("example.com", "Desktop")

            mock_remove.assert_not_called()
            mock_file.assert_any_call("GUI/Reports/Ports/example.com.txt", "a")

    def test_main_deletes_existing_file_first(self):
        """Khi file đã tồn tại → xóa (rmtree) rồi tạo lại."""
        with port_patches():
            with (
                patch("Core.Port_Scanner.os.path.exists", return_value=True),
                patch("Core.Port_Scanner.os.remove") as mock_remove,
                patch("Core.Port_Scanner.Scanner.Port.Scan"),
                patch("Core.Port_Scanner.Ports.Banner"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", return_value="2"),
            ):
                from Core.Port_Scanner import Ports
                Ports.Main("example.com", "Desktop")

            mock_remove.assert_called_once()

    def test_main_calls_scanner_scan_with_target(self):
        """Scanner.Port.Scan() phải được gọi với đúng target."""
        with port_patches():
            with (
                patch("Core.Port_Scanner.os.path.exists", return_value=False),
                patch("Core.Port_Scanner.os.remove"),
                patch("Core.Port_Scanner.Scanner.Port.Scan") as mock_scan,
                patch("Core.Port_Scanner.Ports.Banner"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", return_value="2"),
            ):
                from Core.Port_Scanner import Ports
                Ports.Main("scanme.nmap.org", "Desktop")

            mock_scan.assert_called_once()
            args = mock_scan.call_args[0]
            assert args[0] == "scanme.nmap.org"

    def test_main_passes_report_path_to_scanner(self, tmp_path):
        """Scanner.Scan() nhận report path đúng format."""
        captured_args = []

        with port_patches():
            def capture_scan(target, report_path):
                captured_args.append((target, report_path))

            with (
                patch("Core.Port_Scanner.os.path.exists", return_value=False),
                patch("Core.Port_Scanner.os.remove"),
                patch("Core.Port_Scanner.Scanner.Port.Scan", side_effect=capture_scan),
                patch("Core.Port_Scanner.Ports.Banner"),
                patch("builtins.open", mock_open()),
                patch("builtins.input", return_value="2"),
            ):
                from Core.Port_Scanner import Ports

                Ports.Main("target.com", "Desktop")

        assert len(captured_args) == 1
        target, report_path = captured_args[0]
        assert target == "target.com"
        assert "target.com" in report_path


# ===========================================================================
# TestPortSocketEdgeCases — Edge cases cho socket connections
# ===========================================================================
class TestPortSocketEdgeCases:
    """Kiểm thử các edge case của socket trong Get_Port()."""

    def test_socket_connect_ex_called_with_correct_host_and_port(self, tmp_path):
        """connect_ex() phải nhận đúng (host, port) tuple."""
        report = tmp_path / "r.txt"
        report.write_text("")

        with port_patches():
            import importlib
            import Core.Support.Websites.Scanner
            importlib.reload(Core.Support.Websites.Scanner)
            from Core.Support.Websites.Scanner import Port

            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0

            with patch("Core.Support.Websites.Scanner.socket.socket",
                       return_value=mock_socket):
                Port.Get_Port("192.168.1.1", str(report), 22, [])

        mock_socket.connect_ex.assert_called_once_with(("192.168.1.1", 22))

    def test_socket_uses_tcp_protocol(self, tmp_path):
        """Socket phải dùng AF_INET và SOCK_STREAM (TCP)."""
        report = tmp_path / "r.txt"
        report.write_text("")

        with port_patches():
            import importlib
            import Core.Support.Websites.Scanner
            importlib.reload(Core.Support.Websites.Scanner)
            from Core.Support.Websites.Scanner import Port

            with patch("Core.Support.Websites.Scanner.socket.socket") as mock_socket_cls:
                mock_socket_cls.return_value = MagicMock()
                mock_socket_cls.return_value.connect_ex.return_value = 1
                Port.Get_Port("example.com", str(report), 80, [])

            mock_socket_cls.assert_called_once_with(
                socket.AF_INET, socket.SOCK_STREAM
            )

    def test_port_zero_closed_not_appended(self, tmp_path):
        """Port 0 nếu closed → không append."""
        report = tmp_path / "r.txt"
        report.write_text("")

        with port_patches():
            import importlib
            import Core.Support.Websites.Scanner
            importlib.reload(Core.Support.Websites.Scanner)
            from Core.Support.Websites.Scanner import Port

            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 111

            open_ports = []
            with patch("Core.Support.Websites.Scanner.socket.socket",
                       return_value=mock_socket):
                Port.Get_Port("example.com", str(report), 0, open_ports)

        assert 0 not in open_ports

    def test_high_port_number_works(self, tmp_path):
        """Port số cao (65535) vẫn hoạt động bình thường."""
        report = tmp_path / "r.txt"
        report.write_text("")

        with port_patches():
            import importlib
            import Core.Support.Websites.Scanner
            importlib.reload(Core.Support.Websites.Scanner)
            from Core.Support.Websites.Scanner import Port

            mock_socket = MagicMock()
            mock_socket.connect_ex.return_value = 0  # OPEN

            open_ports = []
            with patch("Core.Support.Websites.Scanner.socket.socket",
                       return_value=mock_socket):
                Port.Get_Port("example.com", str(report), 65535, open_ports)

        assert 65535 in open_ports



