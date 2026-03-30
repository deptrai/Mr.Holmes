"""
tests/cli/test_runner.py

Integration tests for Core.cli.runner.BatchRunner — Story 5.1

Verifies:
    - AC1: BatchRunner dispatches to correct scan module
    - AC3: no target → ValueError (caller handles interactive fallthrough)
    - AC5: output formatted as json / txt / csv
    - Scan errors return exit code 1
"""
from __future__ import annotations

import json
import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from Core.cli.parser import parse_args
from Core.cli.runner import BatchRunner, ScanResult


class TestBatchRunnerDispatch:
    """AC1: correct dispatch to scan handlers."""

    def test_username_dispatches_to_scan_pipeline(self) -> None:
        args = parse_args(["--username", "johndoe"])
        runner = BatchRunner(args)

        mock_pipeline = MagicMock()
        mock_pipeline.username = "johndoe"
        mock_pipeline.found = 3

        with patch("Core.cli.runner.BatchRunner._run_username_scan", return_value=ScanResult("username", "johndoe", found=3)) as mock_scan:
            runner.run()
            mock_scan.assert_called_once_with("johndoe")

    def test_phone_dispatches_correctly(self) -> None:
        args = parse_args(["--phone", "+1234567890"])
        runner = BatchRunner(args)

        with patch("Core.cli.runner.BatchRunner._run_phone_scan", return_value=ScanResult("phone", "+1234567890")) as mock_scan:
            runner.run()
            mock_scan.assert_called_once_with("+1234567890")

    def test_email_dispatches_correctly(self) -> None:
        args = parse_args(["--email", "user@example.com"])
        runner = BatchRunner(args)

        with patch("Core.cli.runner.BatchRunner._run_email_scan", return_value=ScanResult("email", "user@example.com")) as mock_scan:
            runner.run()
            mock_scan.assert_called_once_with("user@example.com")

    def test_website_dispatches_correctly(self) -> None:
        args = parse_args(["--website", "example.com"])
        runner = BatchRunner(args)

        with patch("Core.cli.runner.BatchRunner._run_website_scan", return_value=ScanResult("website", "example.com")) as mock_scan:
            runner.run()
            mock_scan.assert_called_once_with("example.com")

    def test_no_target_raises_value_error(self) -> None:
        """AC3: When no target, _dispatch raises ValueError."""
        args = parse_args([])
        runner = BatchRunner(args)
        with pytest.raises(ValueError, match="No scan target"):
            runner._dispatch()

    def test_run_returns_zero_on_success(self) -> None:
        args = parse_args(["--username", "johndoe"])
        runner = BatchRunner(args)

        with patch("Core.cli.runner.BatchRunner._dispatch", return_value=ScanResult("username", "johndoe")):
            code = runner.run()
        assert code == 0

    def test_run_returns_one_on_failure(self) -> None:
        args = parse_args(["--username", "johndoe"])
        runner = BatchRunner(args)

        with patch("Core.cli.runner.BatchRunner._dispatch", side_effect=RuntimeError("scan exploded")):
            code = runner.run()
        assert code == 1


class TestBatchRunnerOutputFormats:
    """AC5: output formatting."""

    def _run_with_output(self, argv: list, capture_output: bool = True) -> str:
        """Helper: run BatchRunner and capture stdout."""
        args = parse_args(argv)
        runner = BatchRunner(args)
        fake_result = ScanResult("username", "johndoe", found=5, output_file="/tmp/johndoe.txt")

        captured = StringIO()
        with patch("Core.cli.runner.BatchRunner._dispatch", return_value=fake_result):
            with patch("sys.stdout", captured):
                runner.run()
        return captured.getvalue()

    def test_txt_output_contains_scan_type(self) -> None:
        out = self._run_with_output(["--username", "johndoe", "--output", "txt"])
        assert "username" in out.lower() or "johndoe" in out

    def test_json_output_is_valid_json(self) -> None:
        out = self._run_with_output(["--username", "johndoe", "--output", "json"])
        data = json.loads(out)
        assert data["scan_type"] == "username"
        assert data["target"] == "johndoe"
        assert data["found"] == 5

    def test_csv_output_has_header_and_row(self) -> None:
        out = self._run_with_output(["--username", "johndoe", "--output", "csv"])
        lines = [ln for ln in out.strip().splitlines() if ln]
        assert len(lines) == 2  # header + values row
        assert "scan_type" in lines[0]

    def test_default_output_is_txt(self) -> None:
        args = parse_args(["--username", "johndoe"])
        assert args.output == "txt"


class TestScanResult:
    """ScanResult container tests."""

    def test_as_dict_keys(self) -> None:
        result = ScanResult("username", "johndoe", found=3, output_file="report.txt")
        d = result.as_dict()
        assert set(d.keys()) == {"scan_type", "target", "found", "output_file", "data"}

    def test_as_dict_values(self) -> None:
        result = ScanResult("phone", "+1234567890")
        d = result.as_dict()
        assert d["scan_type"] == "phone"
        assert d["target"] == "+1234567890"
        assert d["found"] == 0
