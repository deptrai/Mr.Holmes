"""
tests/cli/test_output.py

Unit tests for Core.cli.output — Story 5.2

Verifies:
    - AC1: OutputHandler is a runtime_checkable Protocol
    - AC2: All five methods present: found, not_found, error, progress, summary
    - AC3: ConsoleOutput produces stdout/stderr output
    - AC4: SilentOutput produces no stdout output
    - AC5: ScanPipeline accepts output_handler param and calls found/summary
"""
from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from Core.cli.output import ConsoleOutput, OutputHandler, SilentOutput


# ---------------------------------------------------------------------------
# AC1: Protocol conformance
# ---------------------------------------------------------------------------

class TestOutputHandlerProtocol:
    """AC1: OutputHandler is a runtime_checkable Protocol."""

    def test_is_protocol(self) -> None:
        # runtime_checkable means isinstance() works
        assert isinstance(ConsoleOutput(), OutputHandler)

    def test_silent_output_conforms(self) -> None:
        assert isinstance(SilentOutput(), OutputHandler)

    def test_custom_class_conforming_to_protocol(self) -> None:
        class MyOutput:
            def found(self, url, site_name=""): ...
            def not_found(self, site_name): ...
            def error(self, message, exc=None): ...
            def progress(self, current, total, message=""): ...
            def summary(self, found, total, target): ...

        assert isinstance(MyOutput(), OutputHandler)

    def test_class_missing_method_does_not_conform(self) -> None:
        class Incomplete:
            def found(self, url, site_name=""): ...
            # missing: not_found, error, progress, summary

        assert not isinstance(Incomplete(), OutputHandler)


# ---------------------------------------------------------------------------
# AC2: All five methods present
# ---------------------------------------------------------------------------

class TestOutputHandlerMethods:
    """AC2: Protocol defines all five required methods."""

    @pytest.mark.parametrize("method", ["found", "not_found", "error", "progress", "summary"])
    def test_method_exists_on_protocol(self, method: str) -> None:
        assert hasattr(OutputHandler, method)

    @pytest.mark.parametrize("method", ["found", "not_found", "error", "progress", "summary"])
    def test_method_exists_on_console_output(self, method: str) -> None:
        obj = ConsoleOutput()
        assert hasattr(obj, method) and callable(getattr(obj, method))

    @pytest.mark.parametrize("method", ["found", "not_found", "error", "progress", "summary"])
    def test_method_exists_on_silent_output(self, method: str) -> None:
        obj = SilentOutput()
        assert hasattr(obj, method) and callable(getattr(obj, method))


# ---------------------------------------------------------------------------
# AC3: ConsoleOutput produces output
# ---------------------------------------------------------------------------

class TestConsoleOutput:
    """AC3: ConsoleOutput writes to stdout/stderr."""

    def _capture(self) -> StringIO:
        return StringIO()

    def test_found_writes_to_stdout(self) -> None:
        out = ConsoleOutput()
        captured = StringIO()
        with patch("sys.stdout", captured):
            out.found("https://instagram.com/johndoe", "Instagram")
        assert "johndoe" in captured.getvalue()

    def test_found_without_site_name(self) -> None:
        out = ConsoleOutput()
        captured = StringIO()
        with patch("sys.stdout", captured):
            out.found("https://example.com/test")
        assert "example.com" in captured.getvalue()

    def test_error_writes_to_stderr(self) -> None:
        out = ConsoleOutput()
        captured = StringIO()
        with patch("sys.stderr", captured):
            out.error("Connection timeout")
        assert "timeout" in captured.getvalue().lower() or "Connection" in captured.getvalue()

    def test_progress_writes_to_stdout(self) -> None:
        out = ConsoleOutput()
        captured = StringIO()
        with patch("sys.stdout", captured):
            out.progress(5, 10, "scanning")
        result = captured.getvalue()
        assert "5" in result and "10" in result

    def test_progress_percentage(self) -> None:
        out = ConsoleOutput()
        captured = StringIO()
        with patch("sys.stdout", captured):
            out.progress(50, 100)
        assert "50" in captured.getvalue()

    def test_summary_writes_to_stdout(self) -> None:
        out = ConsoleOutput()
        captured = StringIO()
        with patch("sys.stdout", captured):
            out.summary(7, 10, "johndoe")
        result = captured.getvalue()
        assert "7" in result
        assert "johndoe" in result

    def test_not_found_is_silent(self) -> None:
        """ConsoleOutput suppresses not_found to reduce noise."""
        out = ConsoleOutput()
        captured = StringIO()
        with patch("sys.stdout", captured):
            out.not_found("SomeSite")
        assert captured.getvalue() == ""


# ---------------------------------------------------------------------------
# AC4: SilentOutput produces NO output
# ---------------------------------------------------------------------------

class TestSilentOutput:
    """AC4: SilentOutput never writes to stdout or stderr."""

    def _run_all_methods(self, out: SilentOutput) -> str:
        captured_out = StringIO()
        captured_err = StringIO()
        with patch("sys.stdout", captured_out), patch("sys.stderr", captured_err):
            out.found("https://example.com")
            out.not_found("SomeSite")
            out.error("Something failed")
            out.progress(1, 100)
            out.summary(5, 100, "testuser")
        return captured_out.getvalue() + captured_err.getvalue()

    def test_silent_produces_no_stdout(self) -> None:
        out = SilentOutput()
        assert self._run_all_methods(out) == ""

    def test_found_no_output(self) -> None:
        out = SilentOutput()
        buf = StringIO()
        with patch("sys.stdout", buf):
            out.found("https://example.com", "ExampleSite")
        assert buf.getvalue() == ""

    def test_error_no_stderr_output(self) -> None:
        """SilentOutput.error() logs to DEBUG but no stderr."""
        out = SilentOutput()
        buf = StringIO()
        with patch("sys.stderr", buf):
            out.error("silent error")
        assert buf.getvalue() == ""

    def test_summary_no_output(self) -> None:
        out = SilentOutput()
        buf = StringIO()
        with patch("sys.stdout", buf):
            out.summary(10, 50, "target")
        assert buf.getvalue() == ""


# ---------------------------------------------------------------------------
# AC5: ScanPipeline accepts OutputHandler
# ---------------------------------------------------------------------------

class TestScanPipelineOutputInjection:
    """AC5: ScanPipeline honours injected OutputHandler."""

    def test_default_output_is_console(self) -> None:
        from Core.engine.scan_pipeline import ScanPipeline
        p = ScanPipeline("testuser", "Desktop")
        assert isinstance(p.output, ConsoleOutput)

    def test_custom_output_is_stored(self) -> None:
        from Core.engine.scan_pipeline import ScanPipeline
        silent = SilentOutput()
        p = ScanPipeline("testuser", "Desktop", output_handler=silent)
        assert p.output is silent

    def test_silent_output_accepted(self) -> None:
        from Core.engine.scan_pipeline import ScanPipeline
        p = ScanPipeline("testuser", "Desktop", output_handler=SilentOutput())
        assert isinstance(p.output, SilentOutput)

    def test_handle_results_calls_found_on_output(self) -> None:
        """Verify handle_results() routes found URLs through self.output.found()."""
        from Core.engine.scan_pipeline import ScanPipeline

        mock_output = MagicMock(spec=OutputHandler)
        p = ScanPipeline("testuser", "Desktop", output_handler=mock_output)
        # Manually populate pipeline state (no network call)
        p.successfull = ["https://instagram.com/testuser", "https://github.com/testuser"]
        p.count = 10
        p.scraper_sites = []
        from Core.models.scan_context import ScanContext
        p.ctx = ScanContext(
            target="testuser",
            subject_type="USERNAME",
            report_path="/tmp/testuser.txt",
            json_output_path="/tmp/testuser.json",
            json_names_path="/tmp/testuser_names.json",
        )

        # Patch sleep so test is fast
        with patch("Core.engine.scan_pipeline.sleep"):
            p.handle_results()

        # found() must be called once per URL
        assert mock_output.found.call_count == 2
        urls_called = [call.args[0] for call in mock_output.found.call_args_list]
        assert "https://instagram.com/testuser" in urls_called

        # summary() must be called once
        mock_output.summary.assert_called_once_with(2, 10, "testuser")
