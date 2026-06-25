"""
tests/engine/test_profile_scraper.py

Unit tests cho Core/engine/profile_scraper.py — ProfileScraper class.

Test coverage:
    - scrape_all() gọi tất cả scrapers (Instagram, Twitter, TikTok, ...)
    - Profile_pics directory creation
    - Exception handling — một scraper fail không chặn các scraper khác
"""
from __future__ import annotations

import importlib
from unittest import mock

import pytest


@pytest.fixture
def profile_scraper_mod():
    """Import ProfileScraper với patches active (no I/O side effects)."""
    with mock.patch("Core.engine.profile_scraper.Scraper"):
        mod = importlib.import_module("Core.engine.profile_scraper")
        importlib.reload(mod)
        yield mod


class TestProfileScraperClass:
    """Verify ProfileScraper class structure."""

    def test_class_exists(self, profile_scraper_mod):
        assert hasattr(profile_scraper_mod, "ProfileScraper")

    def test_has_scrape_all(self, profile_scraper_mod):
        assert hasattr(profile_scraper_mod.ProfileScraper, "scrape_all")


class TestScrapeAllDirectory:
    """Test Profile_pics directory creation."""

    def test_creates_profile_pics_dir(self, profile_scraper_mod):
        """scrape_all should chdir to report dir and create Profile_pics if missing."""
        with mock.patch.object(profile_scraper_mod.os, "chdir") as mock_chdir, \
             mock.patch.object(profile_scraper_mod.os.path, "isdir", return_value=False), \
             mock.patch.object(profile_scraper_mod.os, "mkdir") as mock_mkdir, \
             mock.patch.object(profile_scraper_mod, "Scraper"):
            profile_scraper_mod.ProfileScraper.scrape_all(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
            )
            chdir_calls = mock_chdir.call_args_list
            assert any("testuser" in str(c) for c in chdir_calls)
            mock_mkdir.assert_called_once_with("Profile_pics")

    def test_skips_mkdir_if_exists(self, profile_scraper_mod):
        """If Profile_pics exists, mkdir should not be called."""
        with mock.patch.object(profile_scraper_mod.os, "chdir"), \
             mock.patch.object(profile_scraper_mod.os.path, "isdir", return_value=True), \
             mock.patch.object(profile_scraper_mod.os, "mkdir") as mock_mkdir, \
             mock.patch.object(profile_scraper_mod, "Scraper"):
            profile_scraper_mod.ProfileScraper.scrape_all(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
            )
            mock_mkdir.assert_not_called()

    def test_chdir_back_to_root(self, profile_scraper_mod):
        """scrape_all should chdir back to ../../../../ after creating dir."""
        with mock.patch.object(profile_scraper_mod.os, "chdir") as mock_chdir, \
             mock.patch.object(profile_scraper_mod.os.path, "isdir", return_value=True), \
             mock.patch.object(profile_scraper_mod.os, "mkdir"), \
             mock.patch.object(profile_scraper_mod, "Scraper"):
            profile_scraper_mod.ProfileScraper.scrape_all(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
            )
            chdir_calls = [str(c) for c in mock_chdir.call_args_list]
            assert any("../../../../" in c for c in chdir_calls)


class TestScrapeAllCallsScrapers:
    """Test that scrape_all calls all scrapers."""

    def test_calls_all_scrapers(self, profile_scraper_mod):
        """scrape_all should call Instagram, Twitter, TikTok, Github, GitLab,
        Ngl, Tellonym, Gravatar, Joinroll, Chess scrapers."""
        with mock.patch.object(profile_scraper_mod.os, "chdir"), \
             mock.patch.object(profile_scraper_mod.os.path, "isdir", return_value=True), \
             mock.patch.object(profile_scraper_mod.os, "mkdir"), \
             mock.patch.object(profile_scraper_mod, "Scraper") as mock_scraper:
            profile_scraper_mod.ProfileScraper.scrape_all(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
            )
            scraper_info = mock_scraper.info
            scraper_info.Instagram.assert_called_once()
            scraper_info.Twitter.assert_called_once()
            scraper_info.TikTok.assert_called_once()
            scraper_info.Github.assert_called_once()
            scraper_info.GitLab.assert_called_once()
            scraper_info.Ngl.assert_called_once()
            scraper_info.Tellonym.assert_called_once()
            scraper_info.Gravatar.assert_called_once()
            scraper_info.Joinroll.assert_called_once()
            scraper_info.Chess.assert_called_once()

    def test_instagram_called_with_correct_args(self, profile_scraper_mod):
        """Instagram scraper should receive report, username, proxy, params."""
        with mock.patch.object(profile_scraper_mod.os, "chdir"), \
             mock.patch.object(profile_scraper_mod.os.path, "isdir", return_value=True), \
             mock.patch.object(profile_scraper_mod.os, "mkdir"), \
             mock.patch.object(profile_scraper_mod, "Scraper") as mock_scraper:
            ig_params = []
            post_loc = []
            post_gps = []
            tw_params = []
            profile_scraper_mod.ProfileScraper.scrape_all(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy={"http": "http://proxy:8080"},
                instagram_params=ig_params,
                post_locations=post_loc,
                post_gps_coordinates=post_gps,
                twitter_params=tw_params,
            )
            call_args = mock_scraper.info.Instagram.call_args
            assert call_args[0][0] == "/tmp/report.txt"  # report
            assert call_args[0][1] == "testuser"  # username
            assert call_args[0][2] == {"http": "http://proxy:8080"}  # proxy
            assert call_args[0][3] is ig_params  # instagram_params
            assert call_args[0][4] is post_loc  # post_locations
            assert call_args[0][5] is post_gps  # post_gps_coordinates
            assert call_args[0][6] == "Usernames"
            assert call_args[0][7] == "testuser"

    def test_default_none_lists_initialized(self, profile_scraper_mod):
        """If list params are None, scrape_all should initialize empty lists."""
        with mock.patch.object(profile_scraper_mod.os, "chdir"), \
             mock.patch.object(profile_scraper_mod.os.path, "isdir", return_value=True), \
             mock.patch.object(profile_scraper_mod.os, "mkdir"), \
             mock.patch.object(profile_scraper_mod, "Scraper") as mock_scraper:
            profile_scraper_mod.ProfileScraper.scrape_all(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
                # all list params default to None
            )
            # Should still call scrapers with initialized lists
            mock_scraper.info.Instagram.assert_called_once()
            ig_call = mock_scraper.info.Instagram.call_args[0]
            assert ig_call[3] == []  # instagram_params initialized
            assert ig_call[4] == []  # post_locations initialized
            assert ig_call[5] == []  # post_gps initialized
            tw_call = mock_scraper.info.Twitter.call_args[0]
            assert tw_call[3] == []  # twitter_params initialized


class TestScrapeAllExceptionHandling:
    """Test exception isolation — one scraper failing doesn't block others."""

    def test_instagram_failure_does_not_block_twitter(self, profile_scraper_mod):
        """If Instagram raises, Twitter should still be called."""
        with mock.patch.object(profile_scraper_mod.os, "chdir"), \
             mock.patch.object(profile_scraper_mod.os.path, "isdir", return_value=True), \
             mock.patch.object(profile_scraper_mod.os, "mkdir"), \
             mock.patch.object(profile_scraper_mod, "Scraper") as mock_scraper:
            mock_scraper.info.Instagram.side_effect = Exception("IG down")
            profile_scraper_mod.ProfileScraper.scrape_all(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
            )
            mock_scraper.info.Instagram.assert_called_once()
            mock_scraper.info.Twitter.assert_called_once()
            mock_scraper.info.TikTok.assert_called_once()
            mock_scraper.info.Github.assert_called_once()

    def test_all_scrapers_called_even_if_some_fail(self, profile_scraper_mod):
        """All scrapers should be called even if multiple fail."""
        with mock.patch.object(profile_scraper_mod.os, "chdir"), \
             mock.patch.object(profile_scraper_mod.os.path, "isdir", return_value=True), \
             mock.patch.object(profile_scraper_mod.os, "mkdir"), \
             mock.patch.object(profile_scraper_mod, "Scraper") as mock_scraper:
            mock_scraper.info.Instagram.side_effect = Exception("fail")
            mock_scraper.info.Twitter.side_effect = Exception("fail")
            mock_scraper.info.TikTok.side_effect = Exception("fail")
            profile_scraper_mod.ProfileScraper.scrape_all(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
            )
            # All should still be attempted
            mock_scraper.info.Instagram.assert_called_once()
            mock_scraper.info.Twitter.assert_called_once()
            mock_scraper.info.TikTok.assert_called_once()
            mock_scraper.info.Github.assert_called_once()
            mock_scraper.info.GitLab.assert_called_once()
            mock_scraper.info.Ngl.assert_called_once()
            mock_scraper.info.Tellonym.assert_called_once()
            mock_scraper.info.Gravatar.assert_called_once()
            mock_scraper.info.Joinroll.assert_called_once()
            mock_scraper.info.Chess.assert_called_once()

    def test_no_exception_propagates(self, profile_scraper_mod):
        """scrape_all should not raise even if all scrapers fail."""
        with mock.patch.object(profile_scraper_mod.os, "chdir"), \
             mock.patch.object(profile_scraper_mod.os.path, "isdir", return_value=True), \
             mock.patch.object(profile_scraper_mod.os, "mkdir"), \
             mock.patch.object(profile_scraper_mod, "Scraper") as mock_scraper:
            mock_scraper.info.Instagram.side_effect = Exception("fail")
            mock_scraper.info.Twitter.side_effect = Exception("fail")
            mock_scraper.info.TikTok.side_effect = Exception("fail")
            mock_scraper.info.Github.side_effect = Exception("fail")
            mock_scraper.info.GitLab.side_effect = Exception("fail")
            mock_scraper.info.Ngl.side_effect = Exception("fail")
            mock_scraper.info.Tellonym.side_effect = Exception("fail")
            mock_scraper.info.Gravatar.side_effect = Exception("fail")
            mock_scraper.info.Joinroll.side_effect = Exception("fail")
            mock_scraper.info.Chess.side_effect = Exception("fail")
            # Should not raise
            profile_scraper_mod.ProfileScraper.scrape_all(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
            )
