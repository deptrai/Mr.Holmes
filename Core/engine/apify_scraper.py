"""
Core/engine/apify_scraper.py

Hybrid Apify Cloud integration for advanced OSINT scraping.
Epic 6 — bypasses anti-bot protections via Apify Actor API.
"""
from __future__ import annotations
import logging
import os
from configparser import ConfigParser

from apify_client import ApifyClientAsync

logger = logging.getLogger(__name__)

# F12: Actor ID as class constant instead of magic string
DEFAULT_ACTOR_ID = "apify/instagram-profile-scraper"
DEFAULT_TIMEOUT_SECS = 120  # F4: 2 minute timeout


class ApifyScraper:
    def __init__(self, config_path: str | None = None):
        # F5: Resolve config path to absolute based on project root
        if config_path is None:
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            config_path = os.path.join(project_root, "Configuration", "Configuration.ini")
        self.config_path = config_path
        self.token = self._load_token()
        self.client = ApifyClientAsync(self.token) if self.token else None

    def _load_token(self) -> str | None:
        try:
            parser = ConfigParser()
            parser.read(self.config_path)
            token = parser.get("Settings", "apify_token")
            # F9: strip BEFORE lower comparison to handle "none " edge case
            if token and token.strip().lower() != "none" and token.strip() != "":
                return token.strip()
        except Exception as e:
            # F8: Log config read failures instead of swallowing silently
            logger.debug("Could not load apify_token from config: %s", e)
        return None

    def is_enabled(self) -> bool:
        return bool(self.token)

    async def scrape_instagram_profile(self, username: str) -> dict:
        """
        Uses the Apify Instagram Profile Scraper to extract deep insights.
        Actor ID: apify/instagram-profile-scraper
        """
        if not self.is_enabled():
            return {}

        # F7: Use lazy % formatting instead of f-strings
        logger.info("Delegating Instagram scrape for '%s' to Apify API...", username)
        try:
            run_input = {
                "usernames": [username],
            }

            # F4: Add timeout to prevent indefinite blocking
            run = await self.client.actor(DEFAULT_ACTOR_ID).call(
                run_input=run_input,
                timeout_secs=DEFAULT_TIMEOUT_SECS,
            )

            # F10: Use .get() to guard against KeyError on unexpected response
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                logger.warning("Apify returned no dataset ID for %s", username)
                return {}

            items = []
            async for item in self.client.dataset(dataset_id).iterate_items():
                items.append(item)

            if not items:
                logger.warning("Apify returned no data for %s", username)
                return {}

            profile_data = items[0]

            # Map Apify result format back to what Mr.Holmes expects
            # F16: Default profile_pic to "" instead of None
            enriched_data = {
                "bio": profile_data.get("biography", ""),
                "full_name": profile_data.get("fullName", ""),
                "followers": profile_data.get("followersCount", ""),
                "following": profile_data.get("followsCount", ""),
                "posts": profile_data.get("postsCount", ""),
                "profile_pic": profile_data.get("profilePicUrlHD")
                or profile_data.get("profilePicUrl")
                or "",
            }

            return enriched_data

        except Exception as e:
            logger.error("Apify scraping failed for %s: %s", username, e)
            return {}
