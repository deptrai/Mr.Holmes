"""
tests/models/test_validators.py

Unit tests cho sanitize_username và safe_int_input validators.
Story 1.7 — Input Validation & Sanitization, Epic 1.
"""
from __future__ import annotations

from unittest.mock import patch
import pytest

from Core.models.validators import sanitize_username, safe_int_input, validate_target
from Core.models.exceptions import ConfigurationError


# ---------------------------------------------------------------------------
# sanitize_username
# ---------------------------------------------------------------------------
class TestSanitizeUsername:
    """Tests cho sanitize_username()."""

    def test_valid_username_passes(self):
        """Username hợp lệ trả về đúng giá trị."""
        assert sanitize_username("johndoe") == "johndoe"

    def test_username_with_numbers_and_underscore_passes(self):
        """Username có số và underscore là hợp lệ."""
        assert sanitize_username("user_123") == "user_123"

    def test_leading_trailing_whitespace_stripped(self):
        """Whitespace xung quanh được strip, không raise error."""
        assert sanitize_username("  johndoe  ") == "johndoe"

    def test_path_traversal_dotdot_raises(self):
        """Username với ../  → ConfigurationError (path traversal)."""
        with pytest.raises(ConfigurationError):
            sanitize_username("../etc/passwd")

    def test_path_traversal_dotdot_only_raises(self):
        """Username chỉ có .. → ConfigurationError."""
        with pytest.raises(ConfigurationError):
            sanitize_username("..")

    def test_path_traversal_forward_slash_raises(self):
        """Username với / → ConfigurationError."""
        with pytest.raises(ConfigurationError):
            sanitize_username("foo/bar")

    def test_path_traversal_backslash_raises(self):
        """Username với backslash → ConfigurationError."""
        with pytest.raises(ConfigurationError):
            sanitize_username("foo\\bar")

    def test_null_byte_raises(self):
        """Username với null byte → ConfigurationError."""
        with pytest.raises(ConfigurationError):
            sanitize_username("foo\x00bar")

    def test_special_chars_raise(self):
        """Username với <, >, |, :, *, ? → ConfigurationError."""
        for char in ["<", ">", "|", ":", '"', "*", "?"]:
            with pytest.raises(ConfigurationError, match="ký tự không hợp lệ"):
                sanitize_username(f"foo{char}bar")

    def test_shell_metachar_raises(self):
        """Username với shell metachar (;, `, $, &, ~) → ConfigurationError."""
        for char in [";", "`", "$", "&", "~"]:
            with pytest.raises(ConfigurationError):
                sanitize_username(f"foo{char}bar")

    def test_single_dot_username_passes(self):
        """Username với single dot (john.doe) → hợp lệ, không bị reject."""
        assert sanitize_username("john.doe") == "john.doe"

    def test_empty_string_raises(self):
        """Username rỗng → ConfigurationError."""
        with pytest.raises(ConfigurationError):
            sanitize_username("")

    def test_whitespace_only_raises(self):
        """Username chỉ có spaces → ConfigurationError sau strip."""
        with pytest.raises(ConfigurationError):
            sanitize_username("   ")

    def test_username_max_length_accepted(self):
        """Username đúng 255 ký tự → hợp lệ."""
        result = sanitize_username("a" * 255)
        assert len(result) == 255

    def test_username_too_long_raises(self):
        """Username > 255 ký tự → ConfigurationError."""
        with pytest.raises(ConfigurationError, match="vượt quá"):
            sanitize_username("a" * 256)

    def test_error_has_correct_field_name(self):
        """ConfigurationError chứa đúng field_name='username'."""
        with pytest.raises(ConfigurationError) as exc_info:
            sanitize_username("../hack")
        assert exc_info.value.field_name == "username"


# ---------------------------------------------------------------------------
# safe_int_input
# ---------------------------------------------------------------------------
class TestSafeIntInput:
    """Tests cho safe_int_input() với mock input."""

    def test_valid_integer_returned(self):
        """Input hợp lệ → trả về int ngay lần đầu."""
        with patch("builtins.input", return_value="5"):
            result = safe_int_input("prompt: ")
        assert result == 5
        assert isinstance(result, int)

    def test_invalid_then_valid_retries(self):
        """Input sai 1 lần, sau đó đúng → retry và trả về đúng."""
        with patch("builtins.input", side_effect=["abc", "3"]):
            with patch("builtins.print"):  # suppress error message
                result = safe_int_input("prompt: ")
        assert result == 3

    def test_empty_string_retries(self):
        """Input rỗng → retry và trả về đúng sau lần 2."""
        with patch("builtins.input", side_effect=["", "7"]):
            with patch("builtins.print"):
                result = safe_int_input("prompt: ")
        assert result == 7

    def test_valid_range_accepted(self):
        """Số trong range hợp lệ → trả về ngay."""
        with patch("builtins.input", return_value="3"):
            result = safe_int_input("prompt: ", valid_range=range(1, 5))
        assert result == 3

    def test_out_of_range_retries(self):
        """Số ngoài range → retry cho đến khi đúng."""
        with patch("builtins.input", side_effect=["99", "2"]):
            with patch("builtins.print"):
                result = safe_int_input("prompt: ", valid_range=range(1, 5))
        assert result == 2

    def test_negative_out_of_range_retries(self):
        """Số âm ngoài range → retry."""
        with patch("builtins.input", side_effect=["-1", "1"]):
            with patch("builtins.print"):
                result = safe_int_input("prompt: ", valid_range=range(1, 16))
        assert result == 1


# ---------------------------------------------------------------------------
# validate_target dispatcher
# ---------------------------------------------------------------------------
class TestValidateTarget:
    """Tests cho validate_target() dispatcher."""

    def test_username_subject_sanitizes(self):
        """validate_target với 'USERNAME' → gọi sanitize_username."""
        assert validate_target("validuser", "USERNAME") == "validuser"

    def test_username_with_traversal_raises(self):
        """validate_target với USERNAME + path traversal → ConfigurationError."""
        with pytest.raises(ConfigurationError):
            validate_target("../etc", "USERNAME")

    def test_phone_number_passes(self):
        """validate_target với PHONE-NUMBER → pass-through (không strict checking)."""
        assert validate_target("+84912345678", "PHONE-NUMBER") == "+84912345678"

    def test_empty_phone_raises(self):
        """validate_target với PHONE-NUMBER rỗng → ConfigurationError."""
        with pytest.raises(ConfigurationError):
            validate_target("", "PHONE-NUMBER")

    def test_email_passes(self):
        """validate_target với EMAIL → pass-through."""
        assert validate_target("user@example.com", "EMAIL") == "user@example.com"
