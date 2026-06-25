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
    """Test Google_dork static method — delegates to DorkGenerator."""

    def test_google_dork_delegates_to_dork_generator(self, searcher_mod):
        """Google_dork should delegate to DorkGenerator.google_dorks."""
        with mock.patch("Core.engine.dork_generator.DorkGenerator") as mock_gen:
            searcher_mod.MrHolmes.Google_dork("testuser")
            mock_gen.google_dorks.assert_called_once_with("testuser")

    def test_google_dork_calls_dorks_search_via_generator(self, searcher_mod):
        """Google_dork delegates to DorkGenerator which calls Dorks.Search.dork
        with GOOGLE type."""
        with mock.patch("Core.engine.dork_generator.DorkGenerator.google_dorks") as mock_gdork:
            searcher_mod.MrHolmes.Google_dork("testuser")
            mock_gdork.assert_called_once_with("testuser")


class TestYandexDork:
    """Test Yandex_dork static method — delegates to DorkGenerator."""

    def test_yandex_dork_delegates_to_dork_generator(self, searcher_mod):
        """Yandex_dork should delegate to DorkGenerator.yandex_dorks."""
        with mock.patch("Core.engine.dork_generator.DorkGenerator") as mock_gen:
            searcher_mod.MrHolmes.Yandex_dork("testuser")
            mock_gen.yandex_dorks.assert_called_once_with("testuser")


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
    """Test Scraping static method — delegates to ProfileScraper.scrape_all."""

    def test_scraping_delegates_to_profile_scraper(self, searcher_mod):
        """Scraping should delegate to ProfileScraper.scrape_all."""
        with mock.patch("Core.engine.profile_scraper.ProfileScraper") as mock_ps:
            searcher_mod.MrHolmes.Scraping(
                report="/tmp/report.txt",
                username="testuser",
                http_proxy=None,
                InstagramParams=[],
                PostLocations=[],
                PostGpsCoordinates=[],
                TwitterParams=[],
            )
            mock_ps.scrape_all.assert_called_once()
            kwargs = mock_ps.scrape_all.call_args[1]
            assert kwargs["report"] == "/tmp/report.txt"
            assert kwargs["username"] == "testuser"
            assert kwargs["http_proxy"] is None
            assert kwargs["instagram_params"] == []
            assert kwargs["post_locations"] == []
            assert kwargs["post_gps_coordinates"] == []
            assert kwargs["twitter_params"] == []

    def test_scraping_passes_params_correctly(self, searcher_mod):
        """Scraping should pass InstagramParams and TwitterParams correctly."""
        with mock.patch("Core.engine.profile_scraper.ProfileScraper") as mock_ps:
            ig_params = ["private", "100"]
            tw_params = ["active"]
            searcher_mod.MrHolmes.Scraping(
                report="/tmp/report.txt",
                username="myuser",
                http_proxy={"http": "http://proxy:8080"},
                InstagramParams=ig_params,
                PostLocations=["loc1"],
                PostGpsCoordinates=["gps1"],
                TwitterParams=tw_params,
            )
            kwargs = mock_ps.scrape_all.call_args[1]
            assert kwargs["instagram_params"] is ig_params
            assert kwargs["twitter_params"] is tw_params
            assert kwargs["post_locations"] == ["loc1"]
            assert kwargs["post_gps_coordinates"] == ["gps1"]
