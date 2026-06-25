"""
tests/unit/test_searcher.py

Unit tests for Core/Searcher.py — Username OSINT Agent (legacy).

Tests cover:
- Static method existence and signatures
- Google_dork / Yandex_dork report path construction
- Banner method dispatch
- search() delegation to ScanPipeline
- Scraping() directory creation logic
"""
from __future__ import annotations

import importlib
import json
import os
from contextlib import contextmanager
from unittest import mock

import pytest


# Reusable patch context — silences all I/O side effects in legacy Searcher
@contextmanager
def searcher_patches():
    patches = [
        mock.patch("Core.Searcher.Font"),
        mock.patch("Core.Searcher.Creds"),
        mock.patch("Core.Searcher.FileTransfer"),
        mock.patch("Core.Searcher.Proxies"),
        mock.patch("Core.Searcher.ProxyManager"),
        mock.patch("Core.Searcher.Requests_Search"),
        mock.patch("Core.Searcher.Scraper"),
        mock.patch("Core.Searcher.Clear"),
        mock.patch("Core.Searcher.Dorks"),
        mock.patch("Core.Searcher.Logs"),
        mock.patch("Core.Searcher.banner"),
        mock.patch("Core.Searcher.Language"),
        mock.patch("Core.Searcher.Notification"),
        mock.patch("Core.Searcher.Recap"),
        mock.patch("Core.Searcher.DateFormat.Get.Format", return_value="%d/%m/%Y %H:%M"),
        mock.patch("Core.Searcher.Encoding"),
        mock.patch("Core.Searcher.CO"),
        mock.patch("Core.Searcher.sleep"),
        mock.patch("builtins.input", return_value="0"),
        mock.patch("builtins.print"),
        mock.patch("os.remove"),
    ]
    mocks = [p.start() for p in patches]
    try:
        yield mocks
    finally:
        for p in patches:
            p.stop()


@pytest.fixture
def searcher_mod():
    """Import Searcher with patches active (no reload to avoid conflicts)."""
    with searcher_patches():
        mod = importlib.import_module("Core.Searcher")
        yield mod


class TestSearcherClass:
    """Verify MrHolmes class structure."""

    def test_class_exists(self, searcher_mod):
        assert hasattr(searcher_mod, "MrHolmes")

    def test_has_static_methods(self, searcher_mod):
        cls = searcher_mod.MrHolmes
        for name in ("Scraping", "Controll", "Banner", "Google_dork",
                     "Yandex_dork", "search"):
            assert hasattr(cls, name), f"Missing method: {name}"


class TestGoogleDork:
    """Test Google_dork static method."""

    def test_google_dork_calls_dorks_search(self, searcher_mod, tmp_path):
        """Google_dork should call Dorks.Search.dork with GOOGLE type."""
        with mock.patch("Core.Searcher.Dorks") as mock_dorks, \
             mock.patch("Core.Searcher.os.path.isfile", return_value=False), \
             mock.patch("builtins.print"):
            searcher_mod.MrHolmes.Google_dork("testuser")
            mock_dorks.Search.dork.assert_called_once()
            args = mock_dorks.Search.dork.call_args[0]
            assert args[0] == "testuser"          # username
            assert "testuser_Dorks.txt" in args[1]  # report path
            assert "Google_dorks.txt" in args[2]    # site list file
            assert args[3] == "GOOGLE"              # Type

    def test_google_dork_removes_existing_report(self, searcher_mod):
        """If report file exists, Google_dork should remove it first."""
        with mock.patch("Core.Searcher.Dorks"), \
             mock.patch("Core.Searcher.os.path.isfile", return_value=True), \
             mock.patch("Core.Searcher.os.remove") as mock_remove, \
             mock.patch("builtins.print"):
            searcher_mod.MrHolmes.Google_dork("existing_user")
            mock_remove.assert_called_once()


class TestYandexDork:
    """Test Yandex_dork static method."""

    def test_yandex_dork_calls_dorks_search(self, searcher_mod):
        """Yandex_dork should call Dorks.Search.dork with YANDEX type."""
        with mock.patch("Core.Searcher.Dorks") as mock_dorks, \
             mock.patch("Core.Searcher.os.path.isfile", return_value=False), \
             mock.patch("builtins.print"):
            searcher_mod.MrHolmes.Yandex_dork("testuser")
            mock_dorks.Search.dork.assert_called_once()
            args = mock_dorks.Search.dork.call_args[0]
            assert args[0] == "testuser"
            assert "testuser_Dorks.txt" in args[1]
            assert "Yandex_dorks.txt" in args[2]
            assert args[3] == "YANDEX"


class TestBanner:
    """Test Banner static method."""

    def test_banner_calls_clear_and_random(self, searcher_mod):
        """Banner should call Clear.Screen.Clear() and banner.Random.Get_Banner."""
        with mock.patch("Core.Searcher.Clear") as mock_clear, \
             mock.patch("Core.Searcher.banner") as mock_banner:
            searcher_mod.MrHolmes.Banner("Desktop")
            mock_clear.Screen.Clear.assert_called_once()
            mock_banner.Random.Get_Banner.assert_called_once_with(
                "Banners/Username", "Desktop"
            )


class TestSearchDelegation:
    """Test search() delegation to ScanPipeline."""

    def test_search_imports_scan_pipeline(self, searcher_mod):
        """search() should import ScanPipeline and call pipeline.run()."""
        with mock.patch("Core.engine.scan_pipeline.ScanPipeline") as mock_pipeline:
            searcher_mod.MrHolmes.search("testuser", "Desktop")
            mock_pipeline.assert_called_once_with("testuser", "Desktop")
            mock_pipeline.return_value.run.assert_called_once()


class TestScraping:
    """Test Scraping static method — profile pic directory creation."""

    def test_scraping_creates_profile_pics_dir(self, searcher_mod):
        """Scraping should chdir to report dir and create Profile_pics if missing."""
        with mock.patch("Core.Searcher.os.chdir") as mock_chdir, \
             mock.patch("Core.Searcher.os.path.isdir", return_value=False), \
             mock.patch("Core.Searcher.os.mkdir") as mock_mkdir, \
             mock.patch("Core.Searcher.Scraper") as mock_scraper:
            searcher_mod.MrHolmes.Scraping(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
                InstagramParams=[],
                PostLocations=[],
                PostGpsCoordinates=[],
                TwitterParams=[],
            )
            # Should chdir to GUI/Reports/Usernames/testuser
            chdir_calls = mock_chdir.call_args_list
            assert any("testuser" in str(c) for c in chdir_calls)
            # Should mkdir Profile_pics
            mock_mkdir.assert_called_once_with("Profile_pics")

    def test_scraping_skips_mkdir_if_exists(self, searcher_mod):
        """If Profile_pics exists, mkdir should not be called."""
        with mock.patch("Core.Searcher.os.chdir"), \
             mock.patch("Core.Searcher.os.path.isdir", return_value=True), \
             mock.patch("Core.Searcher.os.mkdir") as mock_mkdir, \
             mock.patch("Core.Searcher.Scraper"):
            searcher_mod.MrHolmes.Scraping(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
                InstagramParams=[],
                PostLocations=[],
                PostGpsCoordinates=[],
                TwitterParams=[],
            )
            mock_mkdir.assert_not_called()

    def test_scraping_calls_all_scrapers(self, searcher_mod):
        """Scraping should call Instagram, Twitter, TikTok, Github, GitLab,
        Ngl, Tellonym, Gravatar, Joinroll, Chess scrapers."""
        with mock.patch("Core.Searcher.os.chdir"), \
             mock.patch("Core.Searcher.os.path.isdir", return_value=True), \
             mock.patch("Core.Searcher.Scraper") as mock_scraper:
            searcher_mod.MrHolmes.Scraping(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
                InstagramParams=[],
                PostLocations=[],
                PostGpsCoordinates=[],
                TwitterParams=[],
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
