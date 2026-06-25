"""
tests/engine/test_dork_generator.py

Unit tests cho Core/engine/dork_generator.py — DorkGenerator class.

Test coverage:
    - google_dorks() gọi Dorks.Search.dork với GOOGLE type
    - yandex_dorks() gọi Dorks.Search.dork với YANDEX type
    - Report path construction
    - Existing report removal
"""
from __future__ import annotations

import importlib
from unittest import mock

import pytest


@pytest.fixture
def dork_generator_mod():
    """Import DorkGenerator với patches active (no I/O side effects)."""
    with mock.patch("Core.engine.dork_generator.Dorks"), \
         mock.patch("Core.engine.dork_generator.Font"), \
         mock.patch("Core.engine.dork_generator.Language"):
        mod = importlib.import_module("Core.engine.dork_generator")
        importlib.reload(mod)
        yield mod


class TestDorkGeneratorClass:
    """Verify DorkGenerator class structure."""

    def test_class_exists(self, dork_generator_mod):
        assert hasattr(dork_generator_mod, "DorkGenerator")

    def test_has_static_methods(self, dork_generator_mod):
        cls = dork_generator_mod.DorkGenerator
        for name in ("google_dorks", "yandex_dorks"):
            assert hasattr(cls, name), f"Missing method: {name}"


class TestGoogleDorks:
    """Test google_dorks static method."""

    def test_google_dorks_calls_dorks_search(self, dork_generator_mod):
        """google_dorks should call Dorks.Search.dork with GOOGLE type."""
        with mock.patch.object(dork_generator_mod, "Dorks") as mock_dorks, \
             mock.patch.object(dork_generator_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            result = dork_generator_mod.DorkGenerator.google_dorks("testuser")
            mock_dorks.Search.dork.assert_called_once()
            args = mock_dorks.Search.dork.call_args[0]
            assert args[0] == "testuser"  # username
            assert "testuser_Dorks.txt" in args[1]  # report path
            assert "Google_dorks.txt" in args[2]  # site list file
            assert args[3] == "GOOGLE"  # Type
            assert "testuser_Dorks.txt" in result

    def test_google_dorks_default_report_dir(self, dork_generator_mod):
        """google_dorks should use default report dir."""
        with mock.patch.object(dork_generator_mod, "Dorks"), \
             mock.patch.object(dork_generator_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            result = dork_generator_mod.DorkGenerator.google_dorks("myuser")
            assert result == "GUI/Reports/Usernames/Dorks/myuser_Dorks.txt"

    def test_google_dorks_custom_report_dir(self, dork_generator_mod):
        """google_dorks should accept custom report dir."""
        with mock.patch.object(dork_generator_mod, "Dorks"), \
             mock.patch.object(dork_generator_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            result = dork_generator_mod.DorkGenerator.google_dorks(
                "myuser", report_dir="/tmp/dorks")
            assert result == "/tmp/dorks/myuser_Dorks.txt"

    def test_google_dorks_removes_existing_report(self, dork_generator_mod):
        """If report file exists, google_dorks should remove it first."""
        with mock.patch.object(dork_generator_mod, "Dorks"), \
             mock.patch.object(dork_generator_mod.os, "path") as mock_path, \
             mock.patch.object(dork_generator_mod.os, "remove") as mock_remove, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = True
            dork_generator_mod.DorkGenerator.google_dorks("existing_user")
            mock_remove.assert_called_once()

    def test_google_dorks_no_remove_if_not_exists(self, dork_generator_mod):
        """If report file does not exist, google_dorks should not remove."""
        with mock.patch.object(dork_generator_mod, "Dorks"), \
             mock.patch.object(dork_generator_mod.os, "path") as mock_path, \
             mock.patch.object(dork_generator_mod.os, "remove") as mock_remove, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            dork_generator_mod.DorkGenerator.google_dorks("new_user")
            mock_remove.assert_not_called()


class TestYandexDorks:
    """Test yandex_dorks static method."""

    def test_yandex_dorks_calls_dorks_search(self, dork_generator_mod):
        """yandex_dorks should call Dorks.Search.dork with YANDEX type."""
        with mock.patch.object(dork_generator_mod, "Dorks") as mock_dorks, \
             mock.patch.object(dork_generator_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            result = dork_generator_mod.DorkGenerator.yandex_dorks("testuser")
            mock_dorks.Search.dork.assert_called_once()
            args = mock_dorks.Search.dork.call_args[0]
            assert args[0] == "testuser"
            assert "testuser_Dorks.txt" in args[1]
            assert "Yandex_dorks.txt" in args[2]
            assert args[3] == "YANDEX"
            assert "testuser_Dorks.txt" in result

    def test_yandex_dorks_default_report_dir(self, dork_generator_mod):
        """yandex_dorks should use default report dir."""
        with mock.patch.object(dork_generator_mod, "Dorks"), \
             mock.patch.object(dork_generator_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            result = dork_generator_mod.DorkGenerator.yandex_dorks("myuser")
            assert result == "GUI/Reports/Usernames/Dorks/myuser_Dorks.txt"

    def test_yandex_dorks_custom_report_dir(self, dork_generator_mod):
        """yandex_dorks should accept custom report dir."""
        with mock.patch.object(dork_generator_mod, "Dorks"), \
             mock.patch.object(dork_generator_mod.os, "path") as mock_path, \
             mock.patch("builtins.print"):
            mock_path.isfile.return_value = False
            result = dork_generator_mod.DorkGenerator.yandex_dorks(
                "myuser", report_dir="/tmp/dorks")
            assert result == "/tmp/dorks/myuser_Dorks.txt"
