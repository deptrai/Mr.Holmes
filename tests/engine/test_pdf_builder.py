"""
tests/engine/test_pdf_builder.py

Unit tests cho Core/engine/pdf_builder.py — PDFBuilder class.

Test coverage:
    - TEMPLATES constant
    - get_template_name() for known and unknown numbers
    - get_template_css() for known and unknown numbers
    - generate_html() produces valid HTML with content
"""
from __future__ import annotations

import importlib
from unittest import mock

import pytest


@pytest.fixture
def pdf_builder_mod():
    """Import PDFBuilder với patches active (no I/O side effects)."""
    with mock.patch("Core.engine.pdf_builder.DateFormat"):
        mod = importlib.import_module("Core.engine.pdf_builder")
        importlib.reload(mod)
        yield mod


class TestPDFBuilderClass:
    """Verify PDFBuilder class structure."""

    def test_class_exists(self, pdf_builder_mod):
        assert hasattr(pdf_builder_mod, "PDFBuilder")

    def test_has_static_methods(self, pdf_builder_mod):
        cls = pdf_builder_mod.PDFBuilder
        for name in ("generate_html", "get_template_name", "get_template_css"):
            assert hasattr(cls, name), f"Missing method: {name}"

    def test_templates_constant(self, pdf_builder_mod):
        templates = pdf_builder_mod.PDFBuilder.TEMPLATES
        assert isinstance(templates, dict)
        assert 1 in templates
        assert 2 in templates
        assert 3 in templates

    def test_templates_have_name_and_css(self, pdf_builder_mod):
        for num, tpl in pdf_builder_mod.PDFBuilder.TEMPLATES.items():
            assert "name" in tpl
            assert "css" in tpl


class TestGetTemplateName:
    """Test get_template_name static method."""

    def test_light_template(self, pdf_builder_mod):
        assert pdf_builder_mod.PDFBuilder.get_template_name(1) == "LIGHT"

    def test_dark_template(self, pdf_builder_mod):
        assert pdf_builder_mod.PDFBuilder.get_template_name(2) == "DARK"

    def test_high_contrast_template(self, pdf_builder_mod):
        assert pdf_builder_mod.PDFBuilder.get_template_name(3) == "HIGH-CONTRAST"

    def test_unknown_template_defaults_to_light(self, pdf_builder_mod):
        assert pdf_builder_mod.PDFBuilder.get_template_name(99) == "LIGHT"

    def test_zero_template_defaults_to_light(self, pdf_builder_mod):
        assert pdf_builder_mod.PDFBuilder.get_template_name(0) == "LIGHT"


class TestGetTemplateCss:
    """Test get_template_css static method."""

    def test_light_css(self, pdf_builder_mod):
        assert "Light" in pdf_builder_mod.PDFBuilder.get_template_css(1)

    def test_dark_css(self, pdf_builder_mod):
        assert "Dark" in pdf_builder_mod.PDFBuilder.get_template_css(2)

    def test_high_contrast_css(self, pdf_builder_mod):
        assert "High-Contrast" in pdf_builder_mod.PDFBuilder.get_template_css(3)

    def test_unknown_css_defaults_to_light(self, pdf_builder_mod):
        assert "Light" in pdf_builder_mod.PDFBuilder.get_template_css(99)


class TestGenerateHtml:
    """Test generate_html static method."""

    def test_generate_html_contains_username(self, pdf_builder_mod):
        html = pdf_builder_mod.PDFBuilder.generate_html("testuser", "content")
        assert "testuser" in html

    def test_generate_html_contains_content(self, pdf_builder_mod):
        html = pdf_builder_mod.PDFBuilder.generate_html("testuser", "MY REPORT DATA")
        assert "MY REPORT DATA" in html

    def test_generate_html_is_html_document(self, pdf_builder_mod):
        html = pdf_builder_mod.PDFBuilder.generate_html("testuser", "content")
        assert html.startswith("<html>")
        assert "</html>" in html
        assert "<body>" in html
        assert "</body>" in html

    def test_generate_html_default_template_is_light(self, pdf_builder_mod):
        html = pdf_builder_mod.PDFBuilder.generate_html("testuser", "content")
        assert "Light/Pdf.css" in html

    def test_generate_html_dark_template(self, pdf_builder_mod):
        html = pdf_builder_mod.PDFBuilder.generate_html(
            "testuser", "content", template=2)
        assert "Dark/Pdf.css" in html

    def test_generate_html_high_contrast_template(self, pdf_builder_mod):
        html = pdf_builder_mod.PDFBuilder.generate_html(
            "testuser", "content", template=3)
        assert "High-Contrast/Pdf.css" in html

    def test_generate_html_contains_metadata(self, pdf_builder_mod):
        html = pdf_builder_mod.PDFBuilder.generate_html("testuser", "content")
        assert "METADATA" in html
        assert "MR.HOLMES" in html

    def test_generate_html_normalizes_report_paths(self, pdf_builder_mod):
        html = pdf_builder_mod.PDFBuilder.generate_html(
            "testuser", "../Reports/foo")
        assert "GUI/Reports/foo" in html
        assert "../Reports" not in html
