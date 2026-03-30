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
        "--config",
        choices=["api-keys"],
        metavar="SECTION",
        help="Launch interactive configuration wizard for SECTION (e.g., api-keys).",
    )

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

    # --- Export (Story 6.4 AC1 + Story 6.5 AC1) -------------------------
    parser.add_argument(
        "--export",
        choices=["pdf", "csv"],
        metavar="FORMAT",
        help="Export format for an existing investigation: pdf | csv.",
    )
    parser.add_argument(
        "--investigation",
        metavar="ID[,ID...]|all",
        help=(
            "Investigation ID(s) to export (used with --export). "
            "Accepts a single ID, comma-separated IDs (e.g. 1,2,3), "
            "or 'all' to export every investigation (CSV only)."
        ),
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


def has_config_target(args: argparse.Namespace) -> bool:
    """Return True if args specify a config menu (Story 7.4)."""
    return bool(getattr(args, "config", None))


def has_export_target(args: argparse.Namespace) -> bool:
    """Return True if args specify an export operation (Story 6.4/6.5)."""
    return bool(getattr(args, "export", None) and getattr(args, "investigation", None))


def parse_investigation_ids(raw: str) -> Optional[List[int]]:
    """
    Story 6.5 AC4 — parse --investigation value into a list of ints or None.

    Supported formats:
        '1'        → [1]
        '1,2,3'    → [1, 2, 3]
        'all'      → None  (means: all investigations)

    Raises:
        argparse.ArgumentTypeError: If the value is not parseable.
    """
    if raw.strip().lower() == "all":
        return None  # sentinel: export all
    try:
        ids = [int(x.strip()) for x in raw.split(",") if x.strip()]
        ids = list(dict.fromkeys(ids))
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--investigation: expected integer ID(s) or 'all', got {raw!r}"
        )
    if not ids:
        raise argparse.ArgumentTypeError(
            "--investigation: at least one ID is required."
        )
    return ids
