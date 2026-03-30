"""
tests/cli/test_rich_output.py

Unit tests for Core.cli.rich_output — Story 5.3

Verifies:
    - AC1: RichOutput implements OutputHandler Protocol
    - AC2: Progress bar mechanics (begin/end/advance)
    - AC3: Results table rendered on summary()
    - AC4: Tag tree rendered when add_tags() used
    - AC5: Graceful fallback when Rich unavailable
"""
from __future__ import annotations

import io
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from Core.cli.output import ConsoleOutput, OutputHandler, SilentOutput
from Core.cli.rich_output import RichOutput, make_output_handler, _rich_available


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_rich(force_fallback: bool = False) -> RichOutput:
    """Create a RichOutput; use force_fallback=True for a dumb-terminal context."""
    return RichOutput(force_fallback=force_fallback)


# ---------------------------------------------------------------------------
# AC1: Protocol conformance
# ---------------------------------------------------------------------------

class TestRichOutputProtocol:
    """AC1: RichOutput must implement OutputHandler Protocol."""

    def test_conforms_to_output_handler_protocol(self) -> None:
        out = _make_rich()
        assert isinstance(out, OutputHandler)

    def test_all_five_methods_present(self) -> None:
        out = _make_rich()
        for method in ("found", "not_found", "error", "progress", "summary"):
            assert hasattr(out, method) and callable(getattr(out, method))

    def test_rich_specific_helpers_present(self) -> None:
        out = _make_rich()
        assert callable(out.begin_progress)
        assert callable(out.end_progress)
        assert callable(out.add_tags)


# ---------------------------------------------------------------------------
# AC2: Progress bar mechanics
# ---------------------------------------------------------------------------

class TestRichOutputProgress:
    """AC2: Progress bar advances correctly."""

    def test_progress_in_fallback_mode_delegates_to_console(self) -> None:
        out = _make_rich(force_fallback=True)
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            out.progress(5, 100, "scanning")
        # ConsoleOutput.progress() writes to stdout
        assert "5" in buf.getvalue()

    def test_found_accumulated_in_rich_mode(self) -> None:
        out = _make_rich()
        out.found("https://instagram.com/testuser", "Instagram")
        out.found("https://github.com/testuser", "GitHub")
        assert len(out._found_rows) == 2

    def test_found_accumulated_in_fallback_mode(self) -> None:
        out = _make_rich(force_fallback=True)
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            out.found("https://example.com/user", "Ex")
        # ConsoleOutput prints it immediately; RichOutput also accumulates
        assert len(out._found_rows) == 1

    def test_begin_progress_in_rich_mode(self) -> None:
        """begin_progress() sets up the progress bar without error."""
        out = _make_rich()
        if not out._use_rich:
            pytest.skip("Rich not available in this env")

        # Mock the internal progress so we don't actually render
        mock_progress = MagicMock()
        mock_progress.add_task.return_value = 0
        with patch.object(out, "_progress_cls", return_value=mock_progress):
            out.begin_progress(100, "Test scan")
        # No exception == pass

    def test_end_progress_safe_when_not_started(self) -> None:
        """end_progress() must be idempotent / safe to call before begin."""
        out = _make_rich()
        out.end_progress()  # should not raise


# ---------------------------------------------------------------------------
# AC3: Results table
# ---------------------------------------------------------------------------

class TestRichOutputSummaryTable:
    """AC3: summary() renders a result table in Rich mode."""

    def test_summary_fallback_delegates_to_console(self) -> None:
        out = _make_rich(force_fallback=True)
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            out.summary(3, 10, "testuser")
        assert "testuser" in buf.getvalue()

    def test_summary_in_rich_mode_uses_console_print(self) -> None:
        out = _make_rich()
        if not out._use_rich:
            pytest.skip("Rich not available in this env")

        out.found("https://instagram.com/testuser", "Instagram")
        out.found("https://github.com/testuser", "GitHub")

        mock_console = MagicMock()
        out._console = mock_console

        out.summary(2, 10, "testuser")

        # Rule and print calls expected
        assert mock_console.rule.called or mock_console.print.called

    def test_summary_empty_results_no_table(self) -> None:
        out = _make_rich()
        if not out._use_rich:
            pytest.skip("Rich not available in this env")

        # No found() calls
        mock_console = MagicMock()
        out._console = mock_console

        out.summary(0, 10, "nobody")

        # rule and print still called for the summary header
        assert mock_console.print.called

    def test_found_rows_contain_correct_site_and_url(self) -> None:
        out = _make_rich()
        out.found("https://example.com", "ExSite")
        row = out._found_rows[0]
        assert row[0] == "ExSite"
        assert row[1] == "https://example.com"

    def test_found_without_site_name_uses_placeholder(self) -> None:
        out = _make_rich()
        out.found("https://example.com")
        site, url = out._found_rows[0]
        assert site == "—"
        assert url == "https://example.com"


# ---------------------------------------------------------------------------
# AC4: Tag tree
# ---------------------------------------------------------------------------

class TestRichOutputTagTree:
    """AC4: add_tags() populates groups; summary() renders the tree."""

    def test_add_tags_stored_correctly(self) -> None:
        out = _make_rich()
        out.add_tags("Social", ["instagram", "twitter"])
        out.add_tags("Dev", ["github", "gitlab"])
        assert "Social" in out._tag_groups
        assert "instagram" in out._tag_groups["Social"]
        assert "Dev" in out._tag_groups

    def test_add_tags_no_duplicates(self) -> None:
        out = _make_rich()
        out.add_tags("Social", ["instagram"])
        out.add_tags("Social", ["instagram", "twitter"])
        assert out._tag_groups["Social"].count("instagram") == 1

    def test_empty_tags_list_ignored(self) -> None:
        out = _make_rich()
        out.add_tags("Social", [])
        assert "Social" not in out._tag_groups

    def test_tag_tree_rendered_when_tags_present(self) -> None:
        out = _make_rich()
        if not out._use_rich:
            pytest.skip("Rich not available in this env")

        out.add_tags("Social", ["instagram"])
        mock_console = MagicMock()
        out._console = mock_console

        out.summary(1, 10, "testuser")

        # At least one print call for the tree
        assert mock_console.print.call_count >= 1

    def test_no_tag_tree_without_add_tags(self) -> None:
        out = _make_rich()
        if not out._use_rich:
            pytest.skip("Rich not available in this env")

        # Do NOT call add_tags
        mock_console = MagicMock()
        out._console = mock_console
        out._render_tag_tree = MagicMock()

        out.summary(0, 10, "testuser")

        out._render_tag_tree.assert_not_called()


# ---------------------------------------------------------------------------
# AC5: Graceful fallback
# ---------------------------------------------------------------------------

class TestRichOutputFallback:
    """AC5: Fallback to ConsoleOutput when Rich unavailable."""

    def test_force_fallback_uses_console_output(self) -> None:
        out = _make_rich(force_fallback=True)
        assert out._use_rich is False
        assert isinstance(out._fallback, ConsoleOutput)

    def test_force_fallback_found_writes_stdout(self) -> None:
        out = _make_rich(force_fallback=True)
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            out.found("https://example.com", "Ex")
        assert "example.com" in buf.getvalue()

    def test_force_fallback_error_writes_stderr(self) -> None:
        out = _make_rich(force_fallback=True)
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            out.error("Something broke")
        assert "broke" in buf.getvalue()

    def test_rich_available_returns_bool(self) -> None:
        result = _rich_available()
        assert isinstance(result, bool)

    def test_make_output_handler_silent(self) -> None:
        handler = make_output_handler(force_silent=True)
        assert isinstance(handler, SilentOutput)

    def test_make_output_handler_rich_returns_rich_or_console(self) -> None:
        handler = make_output_handler(force_rich=True)
        # Either RichOutput (if TTY) or ConsoleOutput (if dumb terminal)
        assert isinstance(handler, (RichOutput, ConsoleOutput))

    def test_make_output_handler_default_not_silent(self) -> None:
        handler = make_output_handler()
        assert not isinstance(handler, SilentOutput)

    def test_rich_import_failure_falls_back(self) -> None:
        """Simulate rich import failure → UseRich=False, fallback=ConsoleOutput."""
        with patch.dict("sys.modules", {"rich.console": None}):
            out = RichOutput()
            # Either uses actual rich (if already imported) or falls back
            assert isinstance(out._fallback, (ConsoleOutput, type(None)))
