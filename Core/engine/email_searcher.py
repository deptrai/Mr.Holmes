"""
Core/engine/email_searcher.py

Modern email OSINT — extracted from legacy Core/E_Mail.py.
Validates email addresses and generates Google/Yandex dork queries for
email-based investigations.

Phase-out Phase 1 — EmailSearcher replaces Core.E_Mail.Mail_search.
"""
from __future__ import annotations

import os
import re

from Core.Support import Dorks
from Core.Support import Font
from Core.Support import Language
from Core.Support.Mail import Mail_Validator

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


class EmailSearcher:
    """
    Email OSINT utilities.

    Replaces legacy Core.E_Mail.Mail_search.
    """

    EMAIL_REGEX = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'

    @staticmethod
    def validate(email: str) -> bool:
        """Validate email format.

        Args:
            email: Email address to validate.

        Returns:
            True if the email matches the standard email regex.
        """
        return bool(re.fullmatch(EmailSearcher.EMAIL_REGEX, email))

    @staticmethod
    def search(email: str, mode: str = "Desktop") -> str:
        """Search for email across sources. Returns report path.

        Args:
            email: Target email address.
            mode: Display mode (Desktop/Mobile).

        Returns:
            Đường dẫn file report.
        """
        report = "GUI/Reports/E-Mail/{}/{}.txt".format(email, email)
        isvalid = Mail_Validator.Validator.Mail(email, report)
        if isvalid:
            EmailSearcher.google_dorks(email)
            EmailSearcher.yandex_dorks(email)
        return report

    @staticmethod
    def google_dorks(
        email: str,
        report_dir: str = "GUI/Reports/E-Mails/Dorks",
    ) -> str:
        """Generate Google dorks for email. Returns report path.

        Args:
            email: Target email address.
            report_dir: Thư mục lưu dork report.

        Returns:
            Đường dẫn file report dork.
        """
        report = "{}/{}_Dorks.txt".format(report_dir, email)
        nomefile = "Site_lists/E-Mail/Google_dorks.txt"
        dork_type = "GOOGLE"
        if os.path.isfile(report):
            os.remove(report)
            print(Font.Color.BLUE + "\n[I]" + Font.Color.WHITE +
                  Language.Translation.Translate_Language(
                      filename, "Dorks", "Remove", "None").format(email))
        else:
            pass
        Dorks.Search.dork(email, report, nomefile, dork_type)
        return report

    @staticmethod
    def yandex_dorks(
        email: str,
        report_dir: str = "GUI/Reports/E-Mails/Dorks",
    ) -> str:
        """Generate Yandex dorks for email. Returns report path.

        Args:
            email: Target email address.
            report_dir: Thư mục lưu dork report.

        Returns:
            Đường dẫn file report dork.
        """
        report = "{}/{}_Dorks.txt".format(report_dir, email)
        nomefile = "Site_lists/E-Mail/Yandex_dorks.txt"
        dork_type = "YANDEX"
        Dorks.Search.dork(email, report, nomefile, dork_type)
        return report
