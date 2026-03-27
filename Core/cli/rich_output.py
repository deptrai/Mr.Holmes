"""
Core/cli/rich_output.py

Rich-powered OutputHandler for professional CLI experience.

Story 5.3 — Rich Library Integration
AC1: RichOutput implements OutputHandler Protocol
AC2: Progress bar for scan (X/N sites)
AC3: Results table instead of plain text list
AC4: Tree layout for tag categories
AC5: Graceful fallback if terminal doesn't support Rich

Design notes:
- RichOutput is stateful: it accumulates found_rows and tag_data
  during scanning, then renders the table/tree in summary().
- progress() drives the Rich Progress bar — caller must call
  begin_progress(total) before the scan loop and end_progress() after.
- Fallback to ConsoleOutput when Rich is unavailable or terminal
  has no colour support (e.g. dumb terminals, piped output).
"""
from __future__ import annotations

import sys
from typing import Any, Dict, List, Optional, Tuple

from Core.config.logging_config import get_logger

_logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Capability detection (AC5)
# ---------------------------------------------------------------------------

def _rich_available() -> bool:
    """Return True if Rich is importable and terminal supports colour."""
    try:
        from rich.console import Console
        # is_terminal=True only when stdout is a real TTY
        c = Console()
        return c.is_terminal or c.color_system is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# RichOutput — AC1
# ---------------------------------------------------------------------------

class RichOutput:
    """
    Rich-powered output adapter implementing the OutputHandler Protocol.

    Renders a live Progress bar during scanning (AC2), collects
    found results and tags, then displays a summary Table (AC3)
    and tag Tree (AC4) when summary() is called.

    Falls back to ConsoleOutput if Rich is unavailable (AC5).
    """

    def __init__(self, force_fallback: bool = False) -> None:
        """
        Args:
            force_fallback: Set True to always use ConsoleOutput regardless
                            of Rich availability (useful for tests).
        """
        self._use_rich = not force_fallback and _rich_available()

        if self._use_rich:
            try:
                from rich.console import Console as _Console
                from rich.progress import (
                    Progress as _Progress,
                    SpinnerColumn,
                    BarColumn,
                    TaskProgressColumn,
                    TextColumn,
                    TimeElapsedColumn,
                )
                from rich.table import Table as _Table
                from rich.tree import Tree as _Tree

                self._console = _Console(highlight=False)
                self._progress_cls = _Progress
                self._SpinnerColumn = SpinnerColumn
                self._BarColumn = BarColumn
                self._TaskProgressColumn = TaskProgressColumn
                self._TextColumn = TextColumn
                self._TimeElapsedColumn = TimeElapsedColumn
                self._Table = _Table
                self._Tree = _Tree
            except Exception as e:
                _logger.warning("Rich import failed, falling back: %s", e)
                self._use_rich = False

        if not self._use_rich:
            from Core.cli.output import ConsoleOutput
            self._fallback = ConsoleOutput()
        else:
            self._fallback = None

        # Accumulated data for Table + Tree at summary time
        self._found_rows: List[Tuple[str, str]] = []  # (site_name, url)
        self._tag_groups: Dict[str, List[str]] = {}    # category → [tags]

        # Live progress state
        self._progress: Any = None
        self._task_id: Any = None

    # ------------------------------------------------------------------
    # OutputHandler Protocol methods
    # ------------------------------------------------------------------

    def found(self, url: str, site_name: str = "") -> None:
        """Collect found result; displayed in Table at summary()."""
        self._found_rows.append((site_name or "—", url))
        if not self._use_rich:
            self._fallback.found(url, site_name)

    def not_found(self, site_name: str) -> None:
        """Silent in Rich mode (noise reduction)."""
        if not self._use_rich:
            self._fallback.not_found(site_name)

    def error(self, message: str, exc: Optional[BaseException] = None) -> None:
        """Display error in Rich markup or plain stderr."""
        if self._use_rich:
            self._console.print(f"[bold red]\\[!][/bold red] {message}")
            if exc:
                _logger.debug("RichOutput.error detail", exc_info=exc)
        else:
            self._fallback.error(message, exc)

    def progress(self, current: int, total: int, message: str = "") -> None:
        """Advance the Rich Progress bar (AC2)."""
        if not self._use_rich:
            self._fallback.progress(current, total, message)
            return

        if self._progress is None:
            self._start_progress(total)

        if self._task_id is not None:
            self._progress.update(self._task_id, completed=current)

    def summary(self, found: int, total: int, target: str) -> None:
        """
        Render scan summary: stop progress bar, show Table + Tree (AC3, AC4).
        """
        if not self._use_rich:
            self._fallback.summary(found, total, target)
            return

        self._stop_progress()
        self._render_summary_table(found, total, target)
        if self._tag_groups:
            self._render_tag_tree(target)

    # ------------------------------------------------------------------
    # Rich-specific helpers
    # ------------------------------------------------------------------

    def begin_progress(self, total: int, description: str = "Scanning") -> None:
        """
        Explicitly start a progress bar before the scan loop.

        This is optional — progress() auto-starts on first call too.
        """
        if self._use_rich:
            self._start_progress(total, description)

    def end_progress(self) -> None:
        """Explicitly stop the progress bar after the scan loop."""
        self._stop_progress()

    def add_tags(self, category: str, tags: List[str]) -> None:
        """
        Register tags under a category for the Tree view (AC4).

        Example:
            rich_output.add_tags("Social", ["instagram", "twitter"])
        """
        if tags:
            existing = self._tag_groups.setdefault(category, [])
            existing.extend(t for t in tags if t not in existing)

    # ------------------------------------------------------------------
    # Internal rendering
    # ------------------------------------------------------------------

    def _start_progress(self, total: int, description: str = "Scanning") -> None:
        """Create and start the Rich Progress bar."""
        if self._progress is not None:
            return  # already running

        self._progress = self._progress_cls(
            self._SpinnerColumn(),
            self._TextColumn("[bold cyan]{task.description}"),
            self._BarColumn(),
            self._TaskProgressColumn(),
            self._TimeElapsedColumn(),
            console=self._console,
            transient=True,   # bar disappears when done (clean output)
        )
        self._progress.start()
        self._task_id = self._progress.add_task(description, total=total)

    def _stop_progress(self) -> None:
        """Stop and remove the progress bar."""
        if self._progress is not None:
            try:
                self._progress.stop()
            except Exception:
                pass
            self._progress = None
            self._task_id = None

    def _render_summary_table(self, found: int, total: int, target: str) -> None:
        """Render a Rich Table of found results (AC3)."""
        pct = round(found / total * 100, 1) if total else 0.0

        self._console.print()
        self._console.rule(f"[bold green]✓ Scan complete — {target}[/bold green]")
        self._console.print(
            f"[green]Found:[/green] [bold]{found}[/bold] / {total} "
            f"([cyan]{pct}%[/cyan])"
        )
        self._console.print()

        if not self._found_rows:
            self._console.print("[yellow]No results found.[/yellow]")
            return

        table = self._Table(
            show_header=True,
            header_style="bold magenta",
            title=f"Results for [bold]{target}[/bold]",
            title_style="bold white",
            expand=False,
        )
        table.add_column("Site", style="cyan", no_wrap=True, min_width=18)
        table.add_column("URL", style="green", overflow="fold")

        for site_name, url in self._found_rows:
            table.add_row(site_name, url)

        self._console.print(table)

    def _render_tag_tree(self, target: str) -> None:
        """Render a Rich Tree of tag categories (AC4)."""
        self._console.print()
        tree = self._Tree(f":label: [bold cyan]Tags — {target}[/bold cyan]")

        for category, tags in sorted(self._tag_groups.items()):
            branch = tree.add(f"[yellow]{category}[/yellow]")
            for tag in sorted(tags):
                branch.add(f"[dim]{tag}[/dim]")

        self._console.print(tree)


# ---------------------------------------------------------------------------
# Factory: pick best available output handler (AC5)
# ---------------------------------------------------------------------------

def make_output_handler(force_rich: bool = False, force_silent: bool = False) -> Any:
    """
    Return the best available OutputHandler for the current environment.

    Priority:
        1. SilentOutput  if force_silent
        2. RichOutput    if force_rich or Rich is available + TTY
        3. ConsoleOutput as fallback
    """
    if force_silent:
        from Core.cli.output import SilentOutput
        return SilentOutput()

    if force_rich or _rich_available():
        handler = RichOutput()
        if handler._use_rich:
            return handler

    from Core.cli.output import ConsoleOutput
    return ConsoleOutput()
