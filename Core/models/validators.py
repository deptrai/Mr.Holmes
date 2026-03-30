"""
Core/models/validators.py

Input validation utilities cho Mr.Holmes OSINT engine.
Story 1.7 — Input Validation & Sanitization, Epic 1.

Provides:
  - sanitize_username()  : chống path traversal attack
  - safe_int_input()     : chống crash khi user nhập non-integer
  - validate_target()    : dispatcher to type-specific validator
"""
from __future__ import annotations

import re
from typing import Optional

from Core.models.exceptions import ConfigurationError

# --- Dangerous characters / patterns for username/target ---
_PATH_TRAVERSAL_PATTERNS = re.compile(
    r"\.\."           # double-dot traversal
    r"|[\\/]"         # forward or back slash
    r"|\x00"          # null byte
    r"|[<>|:\"*?]"    # filesystem special chars
    r"|[;`$&~]"       # shell metacharacters
)

MAX_USERNAME_LENGTH = 255


def sanitize_username(username: str) -> str:
    """
    Làm sạch username trước khi dùng trong file paths và URLs.

    Reject nếu:
      - Chứa `..`, `/`, `\\`, `\\x00`, `<`, `>`, `|`, `:`, `"`, `*`, `?`
      - Vượt quá 255 ký tự
      - Rỗng sau khi strip

    Args:
        username: Raw username input từ user.

    Returns:
        Stripped username nếu hợp lệ.

    Raises:
        ConfigurationError: Nếu username chứa path traversal characters.
    """
    stripped = username.strip()

    if not stripped:
        raise ConfigurationError(
            "Username không được rỗng.",
            field_name="username",
        )

    if len(stripped) > MAX_USERNAME_LENGTH:
        raise ConfigurationError(
            f"Username vượt quá {MAX_USERNAME_LENGTH} ký tự "
            f"(nhận được {len(stripped)}).",
            field_name="username",
        )

    if _PATH_TRAVERSAL_PATTERNS.search(stripped):
        raise ConfigurationError(
            f"Username chứa ký tự không hợp lệ: '{stripped}'. "
            "Không được dùng: .., /, \\, null byte, <, >, |, :, \", *, ?",
            field_name="username",
        )

    return stripped


def safe_int_input(
    prompt: str,
    valid_range: Optional[range] = None,
    error_message: str = "[!] Nhập sai — vui lòng nhập một số nguyên hợp lệ.",
) -> int:
    """
    Thay thế `int(input(...))` với retry loop thay vì crash.

    Không bao giờ raise ValueError — luôn retry cho đến khi
    user nhập đúng.

    Args:
        prompt:        Chuỗi hiển thị cho user.
        valid_range:   Nếu cung cấp, reject số ngoài range.
        error_message: Thông báo lỗi khi input không hợp lệ.

    Returns:
        Integer hợp lệ từ user input.
    """
    while True:
        try:
            raw = input(prompt)
            value = int(raw)
            if valid_range is not None and value not in valid_range:
                print(
                    f"{error_message} "
                    f"(hợp lệ: {valid_range.start}–{valid_range.stop - 1})"
                )
                continue
            return value
        except ValueError:
            print(error_message)


def validate_target(target: str, subject_type: str) -> str:
    """
    Dispatcher — validate target tùy theo subject_type.

    Hiện tại chỉ USERNAME cần sanitization đặc biệt.
    Phone, Email, Website được pass-through (validation riêng theo module).

    Args:
        target:       Raw input string từ user.
        subject_type: "USERNAME" | "PHONE-NUMBER" | "EMAIL" | "WEBSITE" | "PERSON"

    Returns:
        Validated/sanitized target string.

    Raises:
        ConfigurationError: Nếu target không hợp lệ.
    """
    if subject_type == "USERNAME":
        return sanitize_username(target)

    # Phone/Email/Website: basic not-empty check
    stripped = target.strip()
    if not stripped:
        raise ConfigurationError(
            f"{subject_type} target không được rỗng.",
            field_name="target",
        )
    return stripped
