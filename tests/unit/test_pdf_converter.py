"""
tests/unit/test_pdf_converter.py

Unit tests for Core/PDF_Converter.py — PDF Graph Converter (legacy).

Tests cover:
- Static method existence and signatures
- Banner method dispatch
- CreateTemplate() template selection (Light/Dark/High-Contrast)
- CreateTemplate() HTML file generation
- Main() Windows guard (os.name == 'nt')
"""
from __future__ import annotations

import importlib
import os
from contextlib import contextmanager
from unittest import mock

import pytest


@contextmanager
def pdf_patches():
    """Patch I/O side effects but NOT builtins.open (would break configparser)."""
    patches = [
        mock.patch("Core.PDF_Converter.pdfkit"),
        mock.patch("Core.PDF_Converter.Font"),
        mock.patch("Core.PDF_Converter.Language"),
        mock.patch("Core.PDF_Converter.DateFormat.Get.Format", return_value="%d/%m/%Y %H:%M"),
        mock.patch("Core.PDF_Converter.Clear"),
        mock.patch("Core.PDF_Converter.Creds"),
        mock.patch("Core.PDF_Converter.FileTransfer"),
        mock.patch("Core.PDF_Converter.banner"),
        mock.patch("Core.PDF_Converter.sleep"),
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
def pdf_mod():
    with pdf_patches():
        mod = importlib.import_module("Core.PDF_Converter")
        yield mod


class TestMenuClass:
    """Verify Menu class structure."""

    def test_class_exists(self, pdf_mod):
        assert hasattr(pdf_mod, "Menu")

    def test_has_static_methods(self, pdf_mod):
        cls = pdf_mod.Menu
        for name in ("Banner", "CreateTemplate", "Main"):
            assert hasattr(cls, name), f"Missing method: {name}"


class TestBanner:
    """Test Banner static method."""

    def test_banner_calls_clear_and_random(self, pdf_mod):
        with mock.patch("Core.PDF_Converter.Clear") as mock_clear, \
             mock.patch("Core.PDF_Converter.banner") as mock_banner:
            pdf_mod.Menu.Banner("Desktop")
            mock_clear.Screen.Clear.assert_called_once()
            mock_banner.Random.Get_Banner.assert_called_once_with(
                "Banners/Pdf", "Desktop"
            )


class TestCreateTemplate:
    """Test CreateTemplate static method — uses real tmp files for open()."""

    @pytest.mark.parametrize("template_num,expected_theme", [
        (1, "LIGHT"),
        (2, "DARK"),
        (3, "HIGH-CONTRAST"),
    ])
    def test_template_selection(self, pdf_mod, template_num, expected_theme,
                                tmp_path):
        """Each template number should select correct CSS theme and call pdfkit."""
        filename = str(tmp_path / "test.html")

        with mock.patch("Core.PDF_Converter.pdfkit") as mock_pdfkit, \
             mock.patch("Core.PDF_Converter.Creds"), \
             mock.patch("Core.PDF_Converter.FileTransfer"), \
             mock.patch("Core.PDF_Converter.os.remove"), \
             mock.patch("builtins.input", return_value="2"), \
             mock.patch("builtins.print"):
            pdf_mod.Menu.CreateTemplate(
                Template=template_num,
                Content="<div>test</div>",
                filename=filename,
                htmlcontent="",
                username="testuser",
            )
            # Verify pdfkit.from_file was called
            mock_pdfkit.from_file.assert_called_once()
            # Verify HTML file was created (before os.remove at end)
            html_file = filename.replace(".mh", ".html")
            assert os.path.exists(html_file)

    def test_createtemplate_light_includes_light_css(self, pdf_mod, tmp_path):
        """Template 1 (LIGHT) should include Light/Pdf.css in HTML."""
        filename = str(tmp_path / "test.html")
        with mock.patch("Core.PDF_Converter.pdfkit"), \
             mock.patch("Core.PDF_Converter.Creds"), \
             mock.patch("Core.PDF_Converter.FileTransfer"), \
             mock.patch("Core.PDF_Converter.os.remove"), \
             mock.patch("builtins.input", return_value="2"), \
             mock.patch("builtins.print"):
            pdf_mod.Menu.CreateTemplate(
                Template=1,
                Content="<div>test</div>",
                filename=filename,
                htmlcontent="",
                username="testuser",
            )
            html_file = filename.replace(".mh", ".html")
            with open(html_file, "r") as f:
                content = f.read()
            assert "Light/Pdf.css" in content

    def test_createtemplate_dark_includes_dark_css(self, pdf_mod, tmp_path):
        """Template 2 (DARK) should include Dark/Pdf.css in HTML."""
        filename = str(tmp_path / "test.html")
        with mock.patch("Core.PDF_Converter.pdfkit"), \
             mock.patch("Core.PDF_Converter.Creds"), \
             mock.patch("Core.PDF_Converter.FileTransfer"), \
             mock.patch("Core.PDF_Converter.os.remove"), \
             mock.patch("builtins.input", return_value="2"), \
             mock.patch("builtins.print"):
            pdf_mod.Menu.CreateTemplate(
                Template=2,
                Content="<div>test</div>",
                filename=filename,
                htmlcontent="",
                username="testuser",
            )
            html_file = filename.replace(".mh", ".html")
            with open(html_file, "r") as f:
                content = f.read()
            assert "Dark/Pdf.css" in content

    def test_createtemplate_high_contrast_includes_hc_css(self, pdf_mod, tmp_path):
        """Template 3 (HIGH-CONTRAST) should include High-Contrast/Pdf.css."""
        filename = str(tmp_path / "test.html")
        with mock.patch("Core.PDF_Converter.pdfkit"), \
             mock.patch("Core.PDF_Converter.Creds"), \
             mock.patch("Core.PDF_Converter.FileTransfer"), \
             mock.patch("Core.PDF_Converter.os.remove"), \
             mock.patch("builtins.input", return_value="2"), \
             mock.patch("builtins.print"):
            pdf_mod.Menu.CreateTemplate(
                Template=3,
                Content="<div>test</div>",
                filename=filename,
                htmlcontent="",
                username="testuser",
            )
            html_file = filename.replace(".mh", ".html")
            with open(html_file, "r") as f:
                content = f.read()
            assert "High-Contrast/Pdf.css" in content

    def test_createtemplate_includes_username(self, pdf_mod, tmp_path):
        """CreateTemplate should include username in HTML metadata."""
        filename = str(tmp_path / "test.html")
        with mock.patch("Core.PDF_Converter.pdfkit"), \
             mock.patch("Core.PDF_Converter.Creds"), \
             mock.patch("Core.PDF_Converter.FileTransfer"), \
             mock.patch("Core.PDF_Converter.os.remove"), \
             mock.patch("builtins.input", return_value="2"), \
             mock.patch("builtins.print"):
            pdf_mod.Menu.CreateTemplate(
                Template=1,
                Content="<div>test</div>",
                filename=filename,
                htmlcontent="",
                username="specialuser",
            )
            html_file = filename.replace(".mh", ".html")
            with open(html_file, "r") as f:
                content = f.read()
            assert "specialuser" in content


class TestMainWindowsGuard:
    """Test Main() Windows guard."""

    def test_main_skips_on_windows(self, pdf_mod):
        """On Windows (os.name == 'nt'), Main should print error and skip
        without calling Banner."""
        with mock.patch("Core.PDF_Converter.os.name", "nt"), \
             mock.patch("Core.PDF_Converter.Menu.Banner") as mock_banner, \
             mock.patch("builtins.input", return_value=""):
            pdf_mod.Menu.Main("testuser", "Desktop")
            # Banner should NOT be called on Windows
            mock_banner.assert_not_called()
