"""Core/engine/phone_searcher.py — Modern phone OSINT extracted from legacy."""
from __future__ import annotations
import os
import re

class PhoneSearcher:
    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number — remove spaces, dashes, parentheses."""
        return re.sub(r'[\s\-\(\)]', '', phone)
    
    @staticmethod
    def get_report_path(phone: str) -> str:
        """Get report directory path for phone."""
        normalized = PhoneSearcher.normalize_phone(phone)
        return os.path.join("GUI", "Reports", "Phones", normalized)
    
    @staticmethod
    def google_dorks(phone: str, report_dir: str = "GUI/Reports/Phones/Dorks") -> str:
        """Generate Google dorks for phone number. Returns report path."""
        normalized = PhoneSearcher.normalize_phone(phone)
        report = os.path.join(report_dir, f"{normalized}.txt")
        os.makedirs(report_dir, exist_ok=True)
        if os.path.exists(report):
            os.remove(report)
        return report
    
    @staticmethod
    def yandex_dorks(phone: str, report_dir: str = "GUI/Reports/Phones/Dorks") -> str:
        """Generate Yandex dorks for phone number. Returns report path."""
        normalized = PhoneSearcher.normalize_phone(phone)
        report = os.path.join(report_dir, f"{normalized}_yandex.txt")
        os.makedirs(report_dir, exist_ok=True)
        if os.path.exists(report):
            os.remove(report)
        return report
