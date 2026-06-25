"""
tests/unit/test_searcher_person.py

Unit tests for Core/Searcher_person.py — Person OSINT Agent (legacy).

Tests cover:
- Static method existence and signatures
- Google_dork / Yandex_dork report path construction
- Banner method dispatch
- Search() username normalization (space → underscore)
- Report folder path construction
"""
from __future__ import annotations

import importlib
from contextlib import contextmanager
from unittest import mock

import pytest


@contextmanager
def person_patches():
    patches = [
        mock.patch("Core.Searcher_person.Font"),
        mock.patch("Core.Searcher_person.Creds"),
        mock.patch("Core.Searcher_person.Proxies"),
        mock.patch("Core.Searcher_person.ProxyManager"),
        mock.patch("Core.Searcher_person.Scraper"),
        mock.patch("Core.Searcher_person.Clear"),
        mock.patch("Core.Searcher_person.Dorks"),
        mock.patch("Core.Searcher_person.Logs"),
        mock.patch("Core.Searcher_person.banner"),
        mock.patch("Core.Searcher_person.Language"),
        mock.patch("Core.Searcher_person.DateFormat.Get.Format", return_value="%d/%m/%Y %H:%M"),
        mock.patch("Core.Searcher_person.Notification"),
        mock.patch("Core.Searcher_person.Recap"),
        mock.patch("Core.Searcher_person.FileTransfer"),
        mock.patch("Core.Searcher_person.Encoding"),
        mock.patch("Core.Searcher_person.sleep"),
        mock.patch("builtins.input", return_value="0"),
        mock.patch("builtins.print"),
        mock.patch("os.remove"),
        mock.patch("os.mkdir"),
        mock.patch("os.path.exists", return_value=False),
    ]
    mocks = [p.start() for p in patches]
    try:
        yield mocks
    finally:
        for p in patches:
            p.stop()


@pytest.fixture
def person_mod():
    with person_patches():
        mod = importlib.import_module("Core.Searcher_person")
        yield mod


class TestInfoClass:
    """Verify info class structure."""

    def test_class_exists(self, person_mod):
        assert hasattr(person_mod, "info")

    def test_has_static_methods(self, person_mod):
        cls = person_mod.info
        for name in ("Google_dork", "Yandex_dork", "Banner", "Search"):
            assert hasattr(cls, name), f"Missing method: {name}"


class TestGoogleDork:
    """Test Google_dork static method."""

    def test_google_dork_calls_dorks_search(self, person_mod):
        with mock.patch("Core.Searcher_person.Dorks") as mock_dorks, \
             mock.patch("Core.Searcher_person.os.path.isfile", return_value=False), \
             mock.patch("builtins.print"):
            person_mod.info.Google_dork("john_doe")
            mock_dorks.Search.dork.assert_called_once()
            args = mock_dorks.Search.dork.call_args[0]
            assert args[0] == "john_doe"
            assert "People" in args[1]  # People folder
            assert "john_doe_Dorks.txt" in args[1]
            assert args[3] == "GOOGLE"

    def test_google_dork_removes_existing(self, person_mod):
        with mock.patch("Core.Searcher_person.Dorks"), \
             mock.patch("Core.Searcher_person.os.path.isfile", return_value=True), \
             mock.patch("Core.Searcher_person.os.remove") as mock_remove, \
             mock.patch("builtins.print"):
            person_mod.info.Google_dork("existing_person")
            mock_remove.assert_called_once()


class TestYandexDork:
    """Test Yandex_dork static method."""

    def test_yandex_dork_calls_dorks_search(self, person_mod):
        with mock.patch("Core.Searcher_person.Dorks") as mock_dorks, \
             mock.patch("Core.Searcher_person.os.path.isfile", return_value=False), \
             mock.patch("builtins.print"):
            person_mod.info.Yandex_dork("jane_doe")
            mock_dorks.Search.dork.assert_called_once()
            args = mock_dorks.Search.dork.call_args[0]
            assert args[0] == "jane_doe"
            assert "People" in args[1]
            assert args[3] == "YANDEX"


class TestBanner:
    """Test Banner static method."""

    def test_banner_calls_clear_and_random(self, person_mod):
        with mock.patch("Core.Searcher_person.Clear") as mock_clear, \
             mock.patch("Core.Searcher_person.banner") as mock_banner:
            person_mod.info.Banner("Mobile")
            mock_clear.Screen.Clear.assert_called_once()
            mock_banner.Random.Get_Banner.assert_called_once_with(
                "Banners/Person", "Mobile"
            )


class TestSearch:
    """Test Search static method — username normalization and folder creation."""

    def test_search_normalizes_username_spaces(self, person_mod):
        """Search should replace spaces with underscores in folder path."""
        with mock.patch("Core.Searcher_person.os.path.exists", return_value=False), \
             mock.patch("Core.Searcher_person.os.mkdir") as mock_mkdir, \
             mock.patch("Core.Searcher_person.os.path.isfile", return_value=False), \
             mock.patch("Core.Searcher_person.info.Banner"), \
             mock.patch("Core.Searcher_person.Logs"), \
             mock.patch("Core.Searcher_person.Scraper"), \
             mock.patch("Core.Searcher_person.Notification"), \
             mock.patch("Core.Searcher_person.Creds"), \
             mock.patch("Core.Searcher_person.Encoding"), \
             mock.patch("Core.Searcher_person.FileTransfer"), \
             mock.patch("Core.Searcher_person.Recap"), \
             mock.patch("Core.Searcher_person.open", mock.mock_open(), create=True), \
             mock.patch("builtins.input", side_effect=["2", "2", "2", "2"]), \
             mock.patch("builtins.print"):
            try:
                person_mod.info.Search("John Doe", "Desktop")
            except (ValueError, StopIteration):
                pass  # input exhaustion is fine
            mkdir_args = mock_mkdir.call_args[0][0]
            assert "John_Doe" in mkdir_args  # space → underscore

    def test_search_uses_people_folder(self, person_mod):
        """Search should create folder under GUI/Reports/People/."""
        with mock.patch("Core.Searcher_person.os.path.exists", return_value=False), \
             mock.patch("Core.Searcher_person.os.mkdir") as mock_mkdir, \
             mock.patch("Core.Searcher_person.os.path.isfile", return_value=False), \
             mock.patch("Core.Searcher_person.info.Banner"), \
             mock.patch("Core.Searcher_person.Logs"), \
             mock.patch("Core.Searcher_person.Scraper"), \
             mock.patch("Core.Searcher_person.Notification"), \
             mock.patch("Core.Searcher_person.Creds"), \
             mock.patch("Core.Searcher_person.Encoding"), \
             mock.patch("Core.Searcher_person.FileTransfer"), \
             mock.patch("Core.Searcher_person.Recap"), \
             mock.patch("Core.Searcher_person.open", mock.mock_open(), create=True), \
             mock.patch("builtins.input", side_effect=["2", "2", "2", "2"]), \
             mock.patch("builtins.print"):
            try:
                person_mod.info.Search("testperson", "Desktop")
            except (ValueError, StopIteration):
                pass
            mkdir_args = mock_mkdir.call_args[0][0]
            assert "People" in mkdir_args
