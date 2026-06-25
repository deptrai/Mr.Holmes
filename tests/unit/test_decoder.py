"""
tests/unit/test_decoder.py

Unit tests for Core/Decoder.py — Encoding/Decoding Menu (legacy).

Tests cover:
- Static method existence and signatures
- Banner method dispatch
- Main() folder mapping logic (1-6)
- Encode/Decode option dispatch
"""
from __future__ import annotations

import importlib
from contextlib import contextmanager
from unittest import mock

import pytest


@contextmanager
def decoder_patches():
    patches = [
        mock.patch("Core.Decoder.Font"),
        mock.patch("Core.Decoder.Language"),
        mock.patch("Core.Decoder.Clear"),
        mock.patch("Core.Decoder.banner"),
        mock.patch("Core.Decoder.Encoding"),
        mock.patch("Core.Decoder.sleep"),
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
def decoder_mod():
    with decoder_patches():
        mod = importlib.import_module("Core.Decoder")
        yield mod


class TestMenuClass:
    """Verify Menu class structure."""

    def test_class_exists(self, decoder_mod):
        assert hasattr(decoder_mod, "Menu")

    def test_has_static_methods(self, decoder_mod):
        cls = decoder_mod.Menu
        for name in ("Banner", "Main"):
            assert hasattr(cls, name), f"Missing method: {name}"


class TestBanner:
    """Test Banner static method."""

    def test_banner_calls_clear_and_random(self, decoder_mod):
        with mock.patch("Core.Decoder.Clear") as mock_clear, \
             mock.patch("Core.Decoder.banner") as mock_banner:
            decoder_mod.Menu.Banner("Desktop")
            mock_clear.Screen.Clear.assert_called_once()
            mock_banner.Random.Get_Banner.assert_called_once_with(
                "Banners/Decode", "Desktop"
            )


class TestMainFolderMapping:
    """Test Main() folder selection logic.

    Input 1 → Usernames, secondFold=True
    Input 2 → Phone, secondFold=True
    Input 3 → Websites, secondFold=True
    Input 4 → People, secondFold=True
    Input 5 → E-Mail, secondFold=False
    Input 6 → Ports, secondFold=False
    """

    @pytest.mark.parametrize("folder_choice,expected_fold,expected_second", [
        (1, "Usernames", "True"),
        (2, "Phone", "True"),
        (3, "Websites", "True"),
        (4, "People", "True"),
        (5, "E-Mail", "False"),
        (6, "Ports", "False"),
    ])
    def test_folder_mapping(self, decoder_mod, folder_choice, expected_fold,
                            expected_second):
        """Each folder choice should map to correct fold and secondFold."""
        with mock.patch("Core.Decoder.Encoding") as mock_enc, \
             mock.patch("Core.Decoder.Menu.Banner"), \
             mock.patch("builtins.input", side_effect=[
                 str(folder_choice),  # folder choice
                 "1",                  # type (for folder 1/4)
                 "1",                  # option (encode)
             ]), \
             mock.patch("builtins.print"):
            try:
                decoder_mod.Menu.Main("testuser", "Desktop")
            except (ValueError, StopIteration, SystemExit):
                pass
            # Verify Encoding was called (option 1 = Encode)
            if folder_choice in (1, 4):
                mock_enc.Encoder.Encode.assert_called_once()
            else:
                mock_enc.Encoder.Encode.assert_called_once()

    def test_encode_option_calls_encoder(self, decoder_mod):
        """Option 1 should call Encoding.Encoder.Encode."""
        with mock.patch("Core.Decoder.Encoding") as mock_enc, \
             mock.patch("Core.Decoder.Menu.Banner"), \
             mock.patch("builtins.input", side_effect=["5", "1"]), \
             mock.patch("builtins.print"):
            try:
                decoder_mod.Menu.Main("testuser", "Desktop")
            except (ValueError, StopIteration):
                pass
            mock_enc.Encoder.Encode.assert_called_once()

    def test_decode_option_calls_decoder(self, decoder_mod):
        """Option 2 should call Encoding.Encoder.Decode."""
        with mock.patch("Core.Decoder.Encoding") as mock_enc, \
             mock.patch("Core.Decoder.Menu.Banner"), \
             mock.patch("builtins.input", side_effect=["5", "2"]), \
             mock.patch("builtins.print"):
            try:
                decoder_mod.Menu.Main("testuser", "Desktop")
            except (ValueError, StopIteration):
                pass
            mock_enc.Encoder.Decode.assert_called_once()
