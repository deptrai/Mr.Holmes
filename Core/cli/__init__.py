"""Core/cli/__init__.py — CLI package for Mr.Holmes batch mode (Story 5.1)."""
from Core.cli.parser import build_parser, parse_args
from Core.cli.runner import BatchRunner

__all__ = ["build_parser", "parse_args", "BatchRunner"]
