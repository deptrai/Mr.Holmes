"""Core/cli/__init__.py — CLI package for Mr.Holmes batch mode (Story 5.1+)."""
from Core.cli.parser import build_parser, parse_args
from Core.cli.runner import BatchRunner
from Core.cli.output import OutputHandler, ConsoleOutput, SilentOutput
from Core.cli.rich_output import RichOutput, make_output_handler

__all__ = [
    "build_parser", "parse_args", "BatchRunner",
    "OutputHandler", "ConsoleOutput", "SilentOutput",
    "RichOutput", "make_output_handler",
]
