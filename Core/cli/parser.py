"""
Core/cli/parser.py

Argparse definition for Mr.Holmes non-interactive (batch) mode.

Story 5.1 — Argparse CLI Interface
AC2: flags --username, --phone, --email, --website, --proxy, --nsfw, --output
AC4: --help
AC5: --output json|txt|csv
"""
from __future__ import annotations

import argparse
from typing import List, Optional


def build_parser() -> argparse.ArgumentParser:
    """Build and return the ArgumentParser for Mr.Holmes CLI."""
    parser = argparse.ArgumentParser(
        prog="MrHolmes.py",
        description=(
            "Mr.Holmes — OSINT Investigation Tool\n"
            "Run without arguments to launch interactive mode."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 MrHolmes.py --username johndoe\n"
            "  python3 MrHolmes.py --username johndoe --proxy --nsfw --output json\n"
            "  python3 MrHolmes.py --phone +1234567890 --output txt\n"
            "  python3 MrHolmes.py --email user@example.com\n"
            "  python3 MrHolmes.py --website example.com\n"
        ),
    )

    # --- Scan target (mutually exclusive) -----------------------------------
    target_group = parser.add_mutually_exclusive_group()
    target_group.add_argument(
        "--username", "-u",
        metavar="NAME",
        help="Username to investigate across social platforms.",
    )
    target_group.add_argument(
        "--phone", "-p",
        metavar="NUMBER",
        help="Phone number to investigate (international format recommended).",
    )
    target_group.add_argument(
        "--email", "-e",
        metavar="ADDRESS",
        help="Email address to investigate.",
    )
    target_group.add_argument(
        "--website", "-w",
        metavar="URL",
        help="Website or domain to investigate.",
    )

    # --- Scan options -------------------------------------------------------
    parser.add_argument(
        "--proxy",
        action="store_true",
        default=False,
        help="Enable proxy for anonymity (reads from Configuration/Configuration.ini).",
    )
    parser.add_argument(
        "--nsfw",
        action="store_true",
        default=False,
        help="Include NSFW site list in username scan.",
    )

    # --- Output format (AC5) -----------------------------------------------
    parser.add_argument(
        "--output", "-o",
        choices=["json", "txt", "csv"],
        default="txt",
        metavar="FORMAT",
        help="Output format: json | txt | csv  (default: txt).",
    )

    return parser


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """
    Parse CLI arguments.

    Args:
        argv: Argument list (defaults to sys.argv[1:] when None).

    Returns:
        Parsed Namespace. If no scan target is provided, all target
        attributes will be None — caller should fall through to
        interactive mode.
    """
    parser = build_parser()
    return parser.parse_args(argv)


def has_batch_target(args: argparse.Namespace) -> bool:
    """Return True if args specify a scan target (batch mode)."""
    return any([args.username, args.phone, args.email, args.website])
