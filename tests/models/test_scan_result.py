"""
tests/models/test_scan_result.py

Unit tests cho ScanResult, ScanStatus, ErrorStrategy, và OSINTError hierarchy.
Story 1.1 — Foundation Refactoring, Epic 1.
"""
import json
import pytest
from Core.models.scan_result import ScanResult, ScanStatus, ErrorStrategy
from Core.models.exceptions import (
    OSINTError,
    TargetSiteTimeout,
    ProxyDeadError,
    RateLimitExceeded,
    ScraperError,
    ConfigurationError,
)


class TestScanResult:
    """Tests cho ScanResult dataclass."""

    def test_create_minimal(self):
        """ScanResult tạo được với chỉ site_name và url."""
        result = ScanResult(site_name="GitHub", url="https://github.com/user")
        assert result.site_name == "GitHub"
        assert result.url == "https://github.com/user"
        assert result.status == ScanStatus.NOT_FOUND
        assert result.found is False
        assert result.is_scrapable is False
        assert result.tags == []

    def test_found_property_true(self):
        """found property trả True khi status là FOUND."""
        result = ScanResult(
            site_name="Instagram",
            url="https://instagram.com/user",
            status=ScanStatus.FOUND,
        )
        assert result.found is True

    def test_found_property_false_for_other_statuses(self):
        """found property trả False cho mọi status khác FOUND."""
        for status in [
            ScanStatus.NOT_FOUND,
            ScanStatus.BLOCKED,
            ScanStatus.RATE_LIMITED,
            ScanStatus.CAPTCHA,
            ScanStatus.ERROR,
            ScanStatus.TIMEOUT,
        ]:
            result = ScanResult(site_name="test", url="http://example.com", status=status)
            assert result.found is False, f"Expected found=False for {status}"

    def test_to_json_returns_valid_json(self):
        """to_json() trả về valid JSON string."""
        result = ScanResult(
            site_name="Twitter",
            url="https://twitter.com/user",
            status=ScanStatus.FOUND,
            tags=["Social", "Microblogging"],
            is_scrapable=True,
        )
        json_str = result.to_json()
        parsed = json.loads(json_str)
        assert parsed["site_name"] == "Twitter"
        assert parsed["url"] == "https://twitter.com/user"
        assert parsed["status"] == "found"
        assert "Social" in parsed["tags"]
        assert parsed["is_scrapable"] is True

    def test_to_json_not_found(self):
        """to_json() cho site không tìm thấy."""
        result = ScanResult(site_name="Facebook", url="https://facebook.com/user")
        parsed = json.loads(result.to_json())
        assert parsed["status"] == "not_found"

    def test_to_dict(self):
        """to_dict() trả về dict với tất cả fields."""
        result = ScanResult(
            site_name="GitHub",
            url="https://github.com/user",
            status=ScanStatus.FOUND,
            tags=["Developer"],
            is_scrapable=True,
            main_identifier="user",
        )
        d = result.to_dict()
        assert d["site"] == "https://github.com/user"
        assert d["name"] == "GitHub"
        assert d["status"] == "found"
        assert "Developer" in d["tags"]
        assert d["is_scrapable"] is True
        assert d["main_identifier"] == "user"
        assert d["error_message"] is None

    def test_tags_are_independent_per_instance(self):
        """Mỗi ScanResult có list tags riêng — không share giữa instances."""
        r1 = ScanResult(site_name="A", url="http://a.com")
        r2 = ScanResult(site_name="B", url="http://b.com")
        r1.tags.append("Social")
        assert "Social" not in r2.tags

    def test_error_message_optional(self):
        """error_message có thể là None hoặc string."""
        r1 = ScanResult(site_name="A", url="http://a.com")
        assert r1.error_message is None
        r2 = ScanResult(site_name="B", url="http://b.com", error_message="Connection refused")
        assert r2.error_message == "Connection refused"

    def test_scan_status_values(self):
        """ScanStatus enum values khớp với string values dùng trong JSON output."""
        assert ScanStatus.FOUND.value == "found"
        assert ScanStatus.NOT_FOUND.value == "not_found"
        assert ScanStatus.BLOCKED.value == "blocked"
        assert ScanStatus.RATE_LIMITED.value == "rate_limited"
        assert ScanStatus.CAPTCHA.value == "captcha"
        assert ScanStatus.ERROR.value == "error"
        assert ScanStatus.TIMEOUT.value == "timeout"

    def test_error_strategy_values(self):
        """ErrorStrategy enum values khớp với string values trong site_list.json."""
        assert ErrorStrategy.STATUS_CODE.value == "Status-Code"
        assert ErrorStrategy.MESSAGE.value == "Message"
        assert ErrorStrategy.RESPONSE_URL.value == "Response-Url"


class TestOSINTExceptions:
    """Tests cho OSINTError exception hierarchy."""

    def test_osint_error_base(self):
        """OSINTError là base exception."""
        err = OSINTError("Something failed")
        assert isinstance(err, Exception)
        assert err.message == "Something failed"

    def test_osint_error_with_context(self):
        """OSINTError chứa site_name và url."""
        err = OSINTError("Failed", site_name="GitHub", url="https://github.com")
        assert err.site_name == "GitHub"
        assert err.url == "https://github.com"
        assert "GitHub" in str(err)
        assert "https://github.com" in str(err)

    def test_target_site_timeout_inheritance(self):
        """TargetSiteTimeout là subclass của OSINTError."""
        err = TargetSiteTimeout(site_name="Twitter", url="https://twitter.com", timeout_seconds=10.0)
        assert isinstance(err, OSINTError)
        assert err.site_name == "Twitter"
        assert err.timeout_seconds == 10.0
        assert "10.0" in str(err)

    def test_proxy_dead_error_inheritance(self):
        """ProxyDeadError là subclass của OSINTError."""
        err = ProxyDeadError(proxy_url="http://dead-proxy:8080", site_name="Instagram")
        assert isinstance(err, OSINTError)
        assert err.proxy_url == "http://dead-proxy:8080"
        assert "dead-proxy" in str(err)

    def test_rate_limit_exceeded(self):
        """RateLimitExceeded chứa status_code và retry_after."""
        err = RateLimitExceeded(
            site_name="Facebook",
            url="https://facebook.com",
            status_code=429,
            retry_after=60,
        )
        assert isinstance(err, OSINTError)
        assert err.status_code == 429
        assert err.retry_after == 60
        assert "429" in str(err)
        assert "60" in str(err)

    def test_rate_limit_no_retry_after(self):
        """RateLimitExceeded hoạt động khi không có retry_after."""
        err = RateLimitExceeded(site_name="FB", url="http://fb.com", status_code=403)
        assert err.retry_after is None
        assert "403" in str(err)

    def test_scraper_error(self):
        """ScraperError chứa scraper_name và original_error."""
        original = ConnectionError("Network unreachable")
        err = ScraperError(
            scraper_name="Instagram",
            site_name="Instagram",
            original_error=original,
        )
        assert isinstance(err, OSINTError)
        assert err.scraper_name == "Instagram"
        assert err.original_error is original
        assert "Instagram" in str(err)
        assert "ConnectionError" in str(err)

    def test_configuration_error(self):
        """ConfigurationError chứa field_name."""
        err = ConfigurationError(message="API key missing", field_name="HIBP_API_KEY")
        assert isinstance(err, OSINTError)
        assert err.field_name == "HIBP_API_KEY"
        assert "HIBP_API_KEY" in str(err)

    def test_catch_all_as_osint_error(self):
        """Tất cả exceptions đều bị catch bởi `except OSINTError`."""
        errors_to_test = [
            TargetSiteTimeout(site_name="A", url="http://a.com"),
            ProxyDeadError(proxy_url="http://proxy", site_name="A"),
            RateLimitExceeded(site_name="A", url="http://a.com", status_code=429),
            ScraperError(scraper_name="Instagram", site_name="A"),
            ConfigurationError("Missing config"),
        ]
        for err in errors_to_test:
            assert isinstance(err, OSINTError), f"{type(err).__name__} should be OSINTError"

    def test_specific_catch_not_confused(self):
        """Các exception types khác nhau không confuse nhau."""
        timeout_err = TargetSiteTimeout(site_name="A", url="http://a.com")
        proxy_err = ProxyDeadError(proxy_url="http://proxy", site_name="A")

        assert not isinstance(timeout_err, ProxyDeadError)
        assert not isinstance(proxy_err, TargetSiteTimeout)
