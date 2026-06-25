"""
Core/engine/decoder_util.py

Modern encode/decode utilities — extracted from legacy Core/Decoder.py and
Core/Support/Encoding.py. Provides pure functions for base64 and hashing
operations without interactive prompts.

Phase-out Phase 1 — DecoderUtil replaces Core.Decoder.Menu.
"""
from __future__ import annotations

import base64
import hashlib
from typing import Optional

_logger = None


def _logger():
    """Lazy logger để tránh module-level I/O side effects."""
    global _logger
    if _logger is None:
        from Core.config.logging_config import get_logger
        _logger = get_logger(__name__)
    return _logger


class DecoderUtil:
    """
    Encode/decode utilities.

    Replaces legacy Core.Decoder.Menu and Core.Support.Encoding.Encoder.
    """

    @staticmethod
    def base64_encode(text: str) -> str:
        """Encode a string to base64.

        Args:
            text: Plain text string.

        Returns:
            Base64-encoded string.
        """
        return base64.b64encode(text.encode()).decode()

    @staticmethod
    def base64_decode(text: str) -> str:
        """Decode a base64 string.

        Args:
            text: Base64-encoded string.

        Returns:
            Decoded plain text string.
        """
        return base64.b64decode(text.encode()).decode()

    @staticmethod
    def md5_hash(text: str) -> str:
        """Compute MD5 hash of a string.

        Args:
            text: Plain text string.

        Returns:
            Hexadecimal MD5 digest.
        """
        return hashlib.md5(text.encode()).hexdigest()

    @staticmethod
    def sha256_hash(text: str) -> str:
        """Compute SHA-256 hash of a string.

        Args:
            text: Plain text string.

        Returns:
            Hexadecimal SHA-256 digest.
        """
        return hashlib.sha256(text.encode()).hexdigest()

    @staticmethod
    def encode_file_content(content: str) -> str:
        """Encode file content to base64 (replaces Encoding.Encoder.Encode).

        Args:
            content: File content as string.

        Returns:
            Base64-encoded content.
        """
        return DecoderUtil.base64_encode(content)

    @staticmethod
    def decode_file_content(content: str) -> str:
        """Decode base64 file content (replaces Encoding.Encoder.Decode).

        Args:
            content: Base64-encoded content.

        Returns:
            Decoded plain text content.
        """
        return DecoderUtil.base64_decode(content)
