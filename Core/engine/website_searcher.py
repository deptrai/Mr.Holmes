"""Core/engine/website_searcher.py — Modern website/domain OSINT."""
from __future__ import annotations
import os
import platform

class WebsiteSearcher:
    @staticmethod
    def get_report_path(domain: str) -> str:
        """Get report directory path for domain."""
        clean = domain.replace("https://", "").replace("http://", "").replace("/", "_")
        return os.path.join("GUI", "Reports", "Websites", clean)
    
    @staticmethod
    def traceroute_command(domain: str) -> list[str]:
        """Get traceroute command for the platform."""
        cmd = "tracert" if platform.system() == "Windows" else "traceroute"
        return [cmd, domain]
    
    @staticmethod
    def google_dorks(domain: str, report_dir: str = "GUI/Reports/Websites/Dorks") -> str:
        """Generate Google dorks for domain. Returns report path."""
        clean = domain.replace("https://", "").replace("http://", "").replace("/", "_")
        report = os.path.join(report_dir, f"{clean}.txt")
        os.makedirs(report_dir, exist_ok=True)
        if os.path.exists(report):
            os.remove(report)
        return report
    
    @staticmethod
    def yandex_dorks(domain: str, report_dir: str = "GUI/Reports/Websites/Dorks") -> str:
        """Generate Yandex dorks for domain. Returns report path."""
        clean = domain.replace("https://", "").replace("http://", "").replace("/", "_")
        report = os.path.join(report_dir, f"{clean}_yandex.txt")
        os.makedirs(report_dir, exist_ok=True)
        if os.path.exists(report):
            os.remove(report)
        return report
