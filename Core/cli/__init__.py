"""Core/cli/__init__.py — CLI package for Mr.Holmes batch mode (Story 5.1)."""
from Core.cli.parser import build_parser, parse_args
from Core.cli.runner import BatchRunner
from Core.cli.output import OutputHandler, ConsoleOutput, SilentOutput

__all__ = [
    "build_parser", "parse_args", "BatchRunner",
    "OutputHandler", "ConsoleOutput", "SilentOutput",
]
