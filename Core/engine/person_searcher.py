"""Core/engine/person_searcher.py — Modern person OSINT."""
from __future__ import annotations
import os

class PersonSearcher:
    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize person name — spaces to underscores."""
        return name.replace(" ", "_")
    
    @staticmethod
    def get_report_path(name: str) -> str:
        """Get report directory path for person."""
        normalized = PersonSearcher.normalize_name(name)
        return os.path.join("GUI", "Reports", "People", normalized)
    
    @staticmethod
    def google_dorks(name: str, report_dir: str = "GUI/Reports/People/Dorks") -> str:
        """Generate Google dorks for person. Returns report path."""
        normalized = PersonSearcher.normalize_name(name)
        report = os.path.join(report_dir, f"{normalized}.txt")
        os.makedirs(report_dir, exist_ok=True)
        if os.path.exists(report):
            os.remove(report)
        return report
