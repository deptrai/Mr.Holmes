"""
Core/engine/dork_generator.py

Modern dork generation — extracted from legacy Core/Searcher.py.
Generates Google and Yandex dork queries for OSINT investigations.

Phase-out Phase 1 — DorkGenerator replaces MrHolmes.Google_dork / Yandex_dork.
"""
from __future__ import annotations

import os

from Core.Support import Dorks
from Core.Support import Font
from Core.Support import Language

filename = Language.Translation.Get_Language()
filename

_logger = None


def _logger():
    """Lazy logger để tránh module-level I/O side effects."""
    global _logger
    if _logger is None:
        from Core.config.logging_config import get_logger
        _logger = get_logger(__name__)
    return _logger


class DorkGenerator:
    """
    Sinh Google/Yandex dork queries cho username OSINT.

    Replaces legacy MrHolmes.Google_dork() và MrHolmes.Yandex_dork().
    """

    @staticmethod
    def google_dorks(
        username: str,
        report_dir: str = "GUI/Reports/Usernames/Dorks",
    ) -> str:
        """Generate Google dorks for username. Returns report path.

        Args:
            username: Target username.
            report_dir: Thư mục lưu dork report.

        Returns:
            Đường dẫn file report dork.
        """
        report = "{}/{}_Dorks.txt".format(report_dir, username)
        nomefile = "Site_lists/Username/Google_dorks.txt"
        dork_type = "GOOGLE"
        if os.path.isfile(report):
            os.remove(report)
            print(Font.Color.BLUE + "\n[I]" + Font.Color.WHITE +
                  Language.Translation.Translate_Language(
                      filename, "Dorks", "Remove", "None").format(username))
        else:
            pass
        Dorks.Search.dork(username, report, nomefile, dork_type)
        return report

    @staticmethod
    def yandex_dorks(
        username: str,
        report_dir: str = "GUI/Reports/Usernames/Dorks",
    ) -> str:
        """Generate Yandex dorks for username. Returns report path.

        Args:
            username: Target username.
            report_dir: Thư mục lưu dork report.

        Returns:
            Đường dẫn file report dork.
        """
        report = "{}/{}_Dorks.txt".format(report_dir, username)
        nomefile = "Site_lists/Username/Yandex_dorks.txt"
        dork_type = "YANDEX"
        Dorks.Search.dork(username, report, nomefile, dork_type)
        return report
