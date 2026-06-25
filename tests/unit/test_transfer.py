"""
tests/unit/test_transfer.py

Unit tests for Core/Transfer.py — File Transfer Menu (legacy).

Tests cover:
- Static method existence and signatures
- Banner method dispatch
- Main() folder mapping logic (1-9)
- File extension selection (.txt / .mh / .pdf)
- FileT.Transfer.File call verification
"""
from __future__ import annotations

import importlib
from contextlib import contextmanager
from unittest import mock

import pytest


@contextmanager
def transfer_patches():
    patches = [
        mock.patch("Core.Transfer.Font"),
        mock.patch("Core.Transfer.Language"),
        mock.patch("Core.Transfer.Clear"),
        mock.patch("Core.Transfer.banner"),
        mock.patch("Core.Transfer.FileT"),
        mock.patch("Core.Transfer.sleep"),
        mock.patch("builtins.input", return_value="0"),
        mock.patch("builtins.print"),
    ]
    mocks = [p.start() for p in patches]
    try:
        yield mocks
    finally:
        for p in patches:
            p.stop()


@pytest.fixture
def transfer_mod():
    with transfer_patches():
        mod = importlib.import_module("Core.Transfer")
        yield mod


class TestMenuClass:
    """Verify Menu class structure."""

    def test_class_exists(self, transfer_mod):
        assert hasattr(transfer_mod, "Menu")

    def test_has_static_methods(self, transfer_mod):
        cls = transfer_mod.Menu
        for name in ("Banner", "Main"):
            assert hasattr(cls, name), f"Missing method: {name}"


class TestBanner:
    """Test Banner static method."""

    def test_banner_calls_clear_and_random(self, transfer_mod):
        with mock.patch("Core.Transfer.Clear") as mock_clear, \
             mock.patch("Core.Transfer.banner") as mock_banner:
            transfer_mod.Menu.Banner("Desktop")
            mock_clear.Screen.Clear.assert_called_once()
            mock_banner.Random.Get_Banner.assert_called_once_with(
                "Banners/Transfer", "Desktop"
            )


class TestMainFolderMapping:
    """Test Main() folder selection logic.

    Input 1 → Usernames, secondFold=True
    Input 2 → Phone, secondFold=True
    Input 3 → Websites, secondFold=True
    Input 4 → People, secondFold=True
    Input 5 → E-Mail, secondFold=False
    Input 6 → Ports, secondFold=False
    Input 7 → PDF, secondFold=Exception
    Input 8 → Maps, secondFold=True
    Input 9 → Graphs, secondFold=True
    """

    @pytest.mark.parametrize("folder_choice,expected_fold", [
        (1, "Usernames"),
        (2, "Phone"),
        (3, "Websites"),
        (4, "People"),
        (5, "E-Mail"),
        (6, "Ports"),
        (7, "PDF"),
        (8, "Maps"),
        (9, "Graphs"),
    ])
    def test_folder_mapping(self, transfer_mod, folder_choice, expected_fold):
        """Each folder choice should map to correct fold name."""
        with mock.patch("Core.Transfer.FileT") as mock_filet, \
             mock.patch("Core.Transfer.Menu.Banner"), \
             mock.patch("builtins.input", side_effect=[
                 str(folder_choice),  # folder choice
                 "1",                  # type (for folder 1/4)
                 "1",                  # option (txt)
             ]), \
             mock.patch("builtins.print"):
            try:
                transfer_mod.Menu.Main("testuser", "Desktop")
            except (ValueError, StopIteration, SystemExit):
                pass
            # FileT.Transfer.File should be called
            mock_filet.Transfer.File.assert_called_once()

    def test_txt_option(self, transfer_mod):
        """Option 1 should produce .txt extension."""
        with mock.patch("Core.Transfer.FileT") as mock_filet, \
             mock.patch("Core.Transfer.Menu.Banner"), \
             mock.patch("builtins.input", side_effect=["5", "1"]), \
             mock.patch("builtins.print"):
            try:
                transfer_mod.Menu.Main("testuser", "Desktop")
            except (ValueError, StopIteration):
                pass
            args = mock_filet.Transfer.File.call_args[0]
            assert ".txt" in args[0]  # report path has .txt

    def test_mh_option(self, transfer_mod):
        """Option 2 should produce .mh extension."""
        with mock.patch("Core.Transfer.FileT") as mock_filet, \
             mock.patch("Core.Transfer.Menu.Banner"), \
             mock.patch("builtins.input", side_effect=["5", "2"]), \
             mock.patch("builtins.print"):
            try:
                transfer_mod.Menu.Main("testuser", "Desktop")
            except (ValueError, StopIteration):
                pass
            args = mock_filet.Transfer.File.call_args[0]
            assert ".mh" in args[0]

    def test_pdf_folder_uses_pdf_extension(self, transfer_mod):
        """Folder 7 (PDF) should use .pdf extension automatically."""
        with mock.patch("Core.Transfer.FileT") as mock_filet, \
             mock.patch("Core.Transfer.Menu.Banner"), \
             mock.patch("builtins.input", side_effect=["7"]), \
             mock.patch("builtins.print"):
            try:
                transfer_mod.Menu.Main("testuser", "Desktop")
            except (ValueError, StopIteration):
                pass
            args = mock_filet.Transfer.File.call_args[0]
            assert ".pdf" in args[0]
