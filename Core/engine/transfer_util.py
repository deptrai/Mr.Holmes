"""
Core/engine/transfer_util.py

Modern file transfer utility — extracted from legacy Core/Transfer.py.
Maps report categories to folder names and copies report files without
interactive prompts or PHP server spawning.

Phase-out Phase 1 — TransferUtil replaces Core.Transfer.Menu.
"""
from __future__ import annotations

import os
import shutil
from typing import Optional

_logger = None


def _logger():
    """Lazy logger để tránh module-level I/O side effects."""
    global _logger
    if _logger is None:
        from Core.config.logging_config import get_logger
        _logger = get_logger(__name__)
    return _logger


class TransferUtil:
    """
    File transfer utilities.

    Replaces legacy Core.Transfer.Menu and Core.Support.FileTransfer.Transfer.
    """

    FOLDER_MAP = {
        1: "Usernames",
        2: "Phone",
        3: "Websites",
        4: "People",
        5: "E-Mail",
        6: "Ports",
        7: "PDF",
        8: "Maps",
        9: "Graphs",
    }

    @staticmethod
    def get_folder_name(option: int) -> str:
        """Get folder name by option number.

        Args:
            option: Option number (1-9).

        Returns:
            Folder name string, or ``"Unknown"`` if not found.
        """
        return TransferUtil.FOLDER_MAP.get(option, "Unknown")

    @staticmethod
    def build_report_path(
        option: int,
        username: str,
        fmt: str = "txt",
    ) -> str:
        """Build the canonical report path for a category.

        Args:
            option: Folder option number (1-9).
            username: Target username/identifier.
            fmt: File extension without dot (e.g. ``"txt"``, ``"mh"``).

        Returns:
            Report file path string.
        """
        folder = TransferUtil.get_folder_name(option)
        if option == 7:
            return "GUI/PDF/{}.{}".format(username, fmt)
        if option in (1, 2, 3, 4, 8, 9):
            base = "GUI" if option in (8, 9) else "GUI/Reports"
            return "{}/{}/{}/{}.{}".format(base, folder, username, username, fmt)
        return "GUI/Reports/{}/{}.{}".format(folder, username, fmt)

    @staticmethod
    def copy_report(src: str, dst: str, fmt: str = "txt") -> bool:
        """Copy report file to destination.

        Args:
            src: Source file path.
            dst: Destination file path.
            fmt: File format/extension (informational).

        Returns:
            True if copy succeeded, False if source missing or error.
        """
        if not os.path.exists(src):
            return False
        try:
            shutil.copyfile(src, dst)
            return True
        except (OSError, shutil.Error):
            return False
