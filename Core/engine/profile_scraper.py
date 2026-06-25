"""
Core/engine/profile_scraper.py

Modern profile scraping — extracted from legacy Core/Searcher.py.
Scrapes social media profiles (Instagram, Twitter, TikTok, GitHub, etc.)

Phase-out Phase 1 — ProfileScraper replaces MrHolmes.Scraping().
"""
from __future__ import annotations

import os
from typing import List, Optional

from Core.Support.Username import Scraper
from Core.config.logging_config import get_logger

logger = get_logger(__name__)


class ProfileScraper:
    """
    Chạy tất cả social media scrapers cho một username.

    Replaces legacy MrHolmes.Scraping().
    Mỗi scraper được bọc trong try/except để một scraper fail
    không chặn các scraper khác.
    """

    @staticmethod
    def scrape_all(
        report: str,
        username: str,
        http_proxy: Optional[object] = None,
        instagram_params: Optional[List] = None,
        post_locations: Optional[List] = None,
        post_gps_coordinates: Optional[List] = None,
        twitter_params: Optional[List] = None,
    ) -> None:
        """Run all social media scrapers for a username.

        Args:
            report: Đường dẫn file report.
            username: Target username.
            http_proxy: Proxy dict hoặc None.
            instagram_params: List accumulator cho Instagram params.
            post_locations: List accumulator cho post locations.
            post_gps_coordinates: List accumulator cho GPS coords.
            twitter_params: List accumulator cho Twitter params.
        """
        if instagram_params is None:
            instagram_params = []
        if post_locations is None:
            post_locations = []
        if post_gps_coordinates is None:
            post_gps_coordinates = []
        if twitter_params is None:
            twitter_params = []

        # Tạo Profile_pics directory nếu chưa tồn tại
        os.chdir("GUI/Reports/Usernames/{}".format(username))
        if os.path.isdir("Profile_pics"):
            pass
        else:
            os.mkdir("Profile_pics")
        os.chdir("../../../../")

        # --- Instagram ---
        try:
            Scraper.info.Instagram(
                report, username, http_proxy, instagram_params,
                post_locations, post_gps_coordinates, "Usernames", username)
        except Exception as e:
            logger.error("Instagram scraper failed: %s", e, exc_info=True)

        # --- Twitter ---
        try:
            Scraper.info.Twitter(
                report, username, http_proxy, twitter_params,
                "Usernames", username)
        except Exception as e:
            logger.error("Twitter scraper failed: %s", e, exc_info=True)

        # --- TikTok ---
        try:
            Scraper.info.TikTok(report, username, http_proxy, "Usernames", username)
        except Exception as e:
            logger.error("TikTok scraper failed: %s", e, exc_info=True)

        # --- GitHub ---
        try:
            Scraper.info.Github(report, username, http_proxy, "Usernames", username)
        except Exception as e:
            logger.error("GitHub scraper failed: %s", e, exc_info=True)

        # --- GitLab ---
        try:
            Scraper.info.GitLab(report, username, http_proxy, "Usernames", username)
        except Exception as e:
            logger.error("GitLab scraper failed: %s", e, exc_info=True)

        # --- Ngl ---
        try:
            Scraper.info.Ngl(report, username, http_proxy, "Usernames", username)
        except Exception as e:
            logger.error("Ngl scraper failed: %s", e, exc_info=True)

        # --- Tellonym ---
        try:
            Scraper.info.Tellonym(report, username, http_proxy, "Usernames", username)
        except Exception as e:
            logger.error("Tellonym scraper failed: %s", e, exc_info=True)

        # --- Gravatar ---
        try:
            Scraper.info.Gravatar(report, username, http_proxy, "Usernames", username)
        except Exception as e:
            logger.error("Gravatar scraper failed: %s", e, exc_info=True)

        # --- Joinroll ---
        try:
            Scraper.info.Joinroll(report, username, http_proxy, "Usernames", username)
        except Exception as e:
            logger.error("Joinroll scraper failed: %s", e, exc_info=True)

        # --- Chess ---
        try:
            Scraper.info.Chess(report, username, http_proxy, "Usernames", username)
        except Exception as e:
            logger.error("Chess scraper failed: %s", e, exc_info=True)
