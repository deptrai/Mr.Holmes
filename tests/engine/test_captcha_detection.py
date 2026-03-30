"""
tests/engine/test_captcha_detection.py

Unit tests cho Story 3-3: CAPTCHA/Block Detection.

Test coverage:
  - AC1: HTTP 403 → BLOCKED
  - AC2: HTTP 429 → RATE_LIMITED
  - AC3: CAPTCHA keywords trong HTML body → CAPTCHA status
  - AC4: ScanStatus phân biệt đúng các trạng thái
  - AC5: Summary report từ ScanResultCollector
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from Core.models.scan_result import ScanResult, ScanStatus, ErrorStrategy
from Core.engine.async_search import (
    SiteConfig,
    search_site,
    _detect_captcha,
    CAPTCHA_INDICATORS,
)
from Core.engine.result_collector import ScanResultCollector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_site(name="TestSite", strategy=ErrorStrategy.STATUS_CODE, error_text="Not Found"):
    return SiteConfig(
        name=name,
        url_template="https://testsite.com/{}",
        display_url="https://testsite.com/johndoe",
        error_strategy=strategy,
        error_text=error_text,
        tags=["Social"],
    )


def make_response(status: int, body: str = "", url: str = "https://testsite.com/johndoe"):
    """Helper tạo mock aiohttp.ClientResponse."""
    resp = AsyncMock()
    resp.status = status
    resp.url = MagicMock()
    resp.url.__str__ = MagicMock(return_value=url)
    resp.headers = {}
    resp.text = AsyncMock(return_value=body)
    return resp


# ---------------------------------------------------------------------------
# AC3: _detect_captcha helper
# ---------------------------------------------------------------------------

class TestDetectCaptcha:
    def test_detect_recaptcha(self) -> None:
        """AC3: 'recaptcha' trong body → True."""
        assert _detect_captcha("<div class='recaptcha'>...</div>") is True

    def test_detect_hcaptcha(self) -> None:
        """AC3: 'hcaptcha' → True."""
        assert _detect_captcha("<script src='hcaptcha.js'></script>") is True

    def test_detect_cf_challenge(self) -> None:
        """AC3: 'cf-challenge' (Cloudflare) → True."""
        assert _detect_captcha('<div id="cf-challenge-running">') is True

    def test_detect_turnstile(self) -> None:
        """AC3: 'turnstile' (Cloudflare Turnstile) → True."""
        assert _detect_captcha("turnstile.render()") is True

    def test_detect_challenge_platform(self) -> None:
        """AC3: 'challenge-platform' → True."""
        assert _detect_captcha("<meta name='challenge-platform'>") is True

    def test_detect_captcha_case_insensitive(self) -> None:
        """AC3: case-insensitive matching."""
        assert _detect_captcha("CAPTCHA verification required") is True
        assert _detect_captcha("ReCAPTCHA is loading") is True

    def test_clean_body_returns_false(self) -> None:
        """AC3: body không có keywords → False."""
        assert _detect_captcha("<html><body>Welcome, johndoe!</body></html>") is False

    def test_empty_body_returns_false(self) -> None:
        """AC3: empty body → False."""
        assert _detect_captcha("") is False

    def test_captcha_indicators_has_expected_keywords(self) -> None:
        """AC3: CAPTCHA_INDICATORS chứa các keywords đúng theo spec."""
        assert "captcha" in CAPTCHA_INDICATORS
        assert "recaptcha" in CAPTCHA_INDICATORS
        assert "hcaptcha" in CAPTCHA_INDICATORS
        assert "cf-challenge" in CAPTCHA_INDICATORS


# ---------------------------------------------------------------------------
# AC1: HTTP 403 → BLOCKED (tất cả strategies)
# ---------------------------------------------------------------------------

class TestBlockedDetection:
    @pytest.mark.asyncio
    async def test_status_code_403_blocked(self) -> None:
        """AC1: STATUS_CODE strategy 403 → BLOCKED."""
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        resp = make_response(status=403)

        async with MagicMock() as session:
            session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=resp)))
            result = await search_site(session, site, "johndoe")

        assert result.status == ScanStatus.BLOCKED

    @pytest.mark.asyncio
    async def test_message_strategy_403_blocked(self) -> None:
        """AC1: MESSAGE strategy 403 → BLOCKED (phát hiện trước khi đọc body)."""
        site = make_site(strategy=ErrorStrategy.MESSAGE, error_text="Error")
        resp = make_response(status=403)

        async with MagicMock() as session:
            session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=resp)))
            result = await search_site(session, site, "johndoe")

        assert result.status == ScanStatus.BLOCKED

    @pytest.mark.asyncio
    async def test_response_url_strategy_403_blocked(self) -> None:
        """AC1: RESPONSE_URL strategy 403 → BLOCKED."""
        site = make_site(strategy=ErrorStrategy.RESPONSE_URL)
        resp = make_response(status=403)

        async with MagicMock() as session:
            session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=resp)))
            result = await search_site(session, site, "johndoe")

        assert result.status == ScanStatus.BLOCKED


# ---------------------------------------------------------------------------
# AC2: HTTP 429 → RATE_LIMITED (tất cả strategies)
# ---------------------------------------------------------------------------

class TestRateLimitDetection:
    @pytest.mark.asyncio
    async def test_status_code_429_rate_limited(self) -> None:
        """AC2: STATUS_CODE strategy 429 → RATE_LIMITED."""
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        resp = make_response(status=429)

        async with MagicMock() as session:
            session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=resp)))
            result = await search_site(session, site, "johndoe")

        assert result.status == ScanStatus.RATE_LIMITED

    @pytest.mark.asyncio
    async def test_message_strategy_429_rate_limited(self) -> None:
        """AC2: MESSAGE strategy 429 → RATE_LIMITED."""
        site = make_site(strategy=ErrorStrategy.MESSAGE, error_text="Error")
        resp = make_response(status=429)

        async with MagicMock() as session:
            session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=resp)))
            result = await search_site(session, site, "johndoe")

        assert result.status == ScanStatus.RATE_LIMITED

    @pytest.mark.asyncio
    async def test_response_url_strategy_429_rate_limited(self) -> None:
        """AC2: RESPONSE_URL strategy 429 → RATE_LIMITED (patch #4)."""
        site = make_site(strategy=ErrorStrategy.RESPONSE_URL)
        resp = make_response(status=429)

        async with MagicMock() as session:
            session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=resp)))
            result = await search_site(session, site, "johndoe")

        assert result.status == ScanStatus.RATE_LIMITED


# ---------------------------------------------------------------------------
# AC3: CAPTCHA trong body → CAPTCHA status
# ---------------------------------------------------------------------------

class TestCaptchaBodyDetection:
    @pytest.mark.asyncio
    async def test_200_with_captcha_body_returns_captcha_status(self) -> None:
        """AC3: HTTP 200 nhưng body có 'captcha' → CAPTCHA status."""
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        resp = make_response(status=200, body="<div class='g-recaptcha' data-sitekey='xxx'>")

        async with MagicMock() as session:
            session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=resp)))
            result = await search_site(session, site, "johndoe")

        assert result.status == ScanStatus.CAPTCHA

    @pytest.mark.asyncio
    async def test_message_strategy_captcha_in_body(self) -> None:
        """AC3: MESSAGE strategy body có captcha keywords → CAPTCHA."""
        site = make_site(strategy=ErrorStrategy.MESSAGE, error_text="Profile not found")
        resp = make_response(status=200, body="Please complete the hcaptcha challenge")

        async with MagicMock() as session:
            session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=resp)))
            result = await search_site(session, site, "johndoe")

        assert result.status == ScanStatus.CAPTCHA

    @pytest.mark.asyncio
    async def test_200_clean_body_returns_found(self) -> None:
        """AC3: HTTP 200 body sạch → FOUND, không phải CAPTCHA."""
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        resp = make_response(status=200, body="<html>Welcome johndoe!</html>")

        async with MagicMock() as session:
            session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=resp)))
            result = await search_site(session, site, "johndoe")

        assert result.status == ScanStatus.FOUND


# ---------------------------------------------------------------------------
# AC5: ScanResultCollector — block summary
# ---------------------------------------------------------------------------

class TestBlockSummary:
    def test_blocked_count(self) -> None:
        """AC5: blocked_count đếm đúng số BLOCKED results."""
        collector = ScanResultCollector()
        collector.add(ScanResult("A", "u", ScanStatus.BLOCKED))
        collector.add(ScanResult("B", "u", ScanStatus.BLOCKED))
        collector.add(ScanResult("C", "u", ScanStatus.FOUND))
        assert collector.blocked_count == 2

    def test_rate_limited_count(self) -> None:
        """AC5: rate_limited_count đếm đúng."""
        collector = ScanResultCollector()
        collector.add(ScanResult("A", "u", ScanStatus.RATE_LIMITED))
        collector.add(ScanResult("B", "u", ScanStatus.FOUND))
        assert collector.rate_limited_count == 1

    def test_captcha_count(self) -> None:
        """AC5: captcha_count đếm đúng."""
        collector = ScanResultCollector()
        collector.add(ScanResult("A", "u", ScanStatus.CAPTCHA))
        assert collector.captcha_count == 1

    def test_block_summary_format(self) -> None:
        """AC5: block_summary() trả về string với counts."""
        collector = ScanResultCollector()
        collector.add(ScanResult("A", "u", ScanStatus.BLOCKED))
        collector.add(ScanResult("B", "u", ScanStatus.RATE_LIMITED))
        collector.add(ScanResult("C", "u", ScanStatus.CAPTCHA))
        summary = collector.block_summary()
        assert "1" in summary   # blocked count
        assert "blocked" in summary.lower() or "rate" in summary.lower()

    def test_block_summary_zero_when_clean(self) -> None:
        """AC5: không có block/rate/captcha → summary vẫn trả về string."""
        collector = ScanResultCollector()
        collector.add(ScanResult("A", "u", ScanStatus.FOUND))
        summary = collector.block_summary()
        assert isinstance(summary, str)

    def test_to_dict_includes_block_stats(self) -> None:
        """AC5: to_dict() include blocked/rate_limited/captcha counts."""
        collector = ScanResultCollector()
        collector.add(ScanResult("A", "u", ScanStatus.BLOCKED))
        d = collector.to_dict()
        assert "blocked" in d
        assert "rate_limited" in d
        assert "captcha" in d
