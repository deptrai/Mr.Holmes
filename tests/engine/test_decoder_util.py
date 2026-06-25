"""
tests/engine/test_decoder_util.py

Unit tests cho Core/engine/decoder_util.py — DecoderUtil class.

Test coverage:
    - base64_encode / base64_decode round-trip
    - md5_hash known vectors
    - sha256_hash known vectors
    - encode_file_content / decode_file_content
"""
from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def decoder_util_mod():
    """Import DecoderUtil (no I/O side effects at module level)."""
    mod = importlib.import_module("Core.engine.decoder_util")
    importlib.reload(mod)
    yield mod


class TestDecoderUtilClass:
    """Verify DecoderUtil class structure."""

    def test_class_exists(self, decoder_util_mod):
        assert hasattr(decoder_util_mod, "DecoderUtil")

    def test_has_static_methods(self, decoder_util_mod):
        cls = decoder_util_mod.DecoderUtil
        for name in ("base64_encode", "base64_decode", "md5_hash",
                     "sha256_hash", "encode_file_content",
                     "decode_file_content"):
            assert hasattr(cls, name), f"Missing method: {name}"


class TestBase64:
    """Test base64 encode/decode."""

    def test_base64_encode_simple(self, decoder_util_mod):
        assert decoder_util_mod.DecoderUtil.base64_encode("hello") == "aGVsbG8="

    def test_base64_encode_empty(self, decoder_util_mod):
        assert decoder_util_mod.DecoderUtil.base64_encode("") == ""

    def test_base64_decode_simple(self, decoder_util_mod):
        assert decoder_util_mod.DecoderUtil.base64_decode("aGVsbG8=") == "hello"

    def test_base64_round_trip(self, decoder_util_mod):
        original = "Mr.Holmes OSINT tool 123 !@#"
        encoded = decoder_util_mod.DecoderUtil.base64_encode(original)
        decoded = decoder_util_mod.DecoderUtil.base64_decode(encoded)
        assert decoded == original

    def test_base64_encode_unicode(self, decoder_util_mod):
        encoded = decoder_util_mod.DecoderUtil.base64_encode("héllo")
        assert decoder_util_mod.DecoderUtil.base64_decode(encoded) == "héllo"


class TestHashing:
    """Test md5 and sha256 hashing."""

    def test_md5_known_vector(self, decoder_util_mod):
        # md5("hello") = 5d41402abc4b2a76b9719d911017c592
        assert decoder_util_mod.DecoderUtil.md5_hash("hello") == \
            "5d41402abc4b2a76b9719d911017c592"

    def test_md5_empty(self, decoder_util_mod):
        # md5("") = d41d8cd98f00b204e9800998ecf8427e
        assert decoder_util_mod.DecoderUtil.md5_hash("") == \
            "d41d8cd98f00b204e9800998ecf8427e"

    def test_sha256_known_vector(self, decoder_util_mod):
        # sha256("hello") = 2cf24dba5fb0a30e26e83b2ac5b9e29e...
        assert decoder_util_mod.DecoderUtil.sha256_hash("hello") == \
            "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_sha256_empty(self, decoder_util_mod):
        # sha256("") = e3b0c44298fc1c149afbf4c8996fb924...
        assert decoder_util_mod.DecoderUtil.sha256_hash("") == \
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_md5_deterministic(self, decoder_util_mod):
        a = decoder_util_mod.DecoderUtil.md5_hash("test")
        b = decoder_util_mod.DecoderUtil.md5_hash("test")
        assert a == b

    def test_sha256_deterministic(self, decoder_util_mod):
        a = decoder_util_mod.DecoderUtil.sha256_hash("test")
        b = decoder_util_mod.DecoderUtil.sha256_hash("test")
        assert a == b


class TestFileContent:
    """Test encode_file_content / decode_file_content."""

    def test_encode_file_content(self, decoder_util_mod):
        assert decoder_util_mod.DecoderUtil.encode_file_content("hello") == "aGVsbG8="

    def test_decode_file_content(self, decoder_util_mod):
        assert decoder_util_mod.DecoderUtil.decode_file_content("aGVsbG8=") == "hello"

    def test_file_content_round_trip(self, decoder_util_mod):
        original = "REPORT CONTENT\nLine 2\nLine 3"
        encoded = decoder_util_mod.DecoderUtil.encode_file_content(original)
        decoded = decoder_util_mod.DecoderUtil.decode_file_content(encoded)
        assert decoded == original
