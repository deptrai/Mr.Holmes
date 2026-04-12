"""
tests/engine/test_retry.py

Unit tests cho Story 2.5 — Exponential Backoff + Jitter.

Test coverage:
    - AC1: RetryPolicy class instantiation + validation
    - AC2: Exponential backoff formula
    - AC3: Jitter applied (delay > pure exponential)
    - AC4: max_retries configurable (default 3)
    - AC5: Retry chỉ cho TargetSiteTimeout + RateLimitExceeded
    - AC6: ProxyDeadError → re-raise ngay, không retry

asyncio.sleep bị mock → tests không bị slow.
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call

from Core.engine.retry import RetryPolicy, DEFAULT_MAX_RETRIES, DEFAULT_BASE_DELAY, DEFAULT_MAX_DELAY
from Core.models.exceptions import (
    TargetSiteTimeout,
    RateLimitExceeded,
    ProxyDeadError,
    SiteCheckError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_timeout_exc() -> TargetSiteTimeout:
    return TargetSiteTimeout(site_name="TestSite", url="https://test.com", timeout_seconds=10)


def _make_rate_limit_exc(retry_after: int | None = None) -> RateLimitExceeded:
    return RateLimitExceeded(site_name="TestSite", url="https://test.com", status_code=429, retry_after=retry_after)


def _make_proxy_exc() -> ProxyDeadError:
    return ProxyDeadError(proxy_url="http://p:8080", site_name="TestSite")


# ---------------------------------------------------------------------------
# AC1 — RetryPolicy instantiation + validation
# ---------------------------------------------------------------------------

class TestRetryPolicyInit:
    def test_default_params(self):
        policy = RetryPolicy()
        assert policy.max_retries == DEFAULT_MAX_RETRIES
        assert policy.base_delay == DEFAULT_BASE_DELAY
        assert policy.max_delay == DEFAULT_MAX_DELAY

    def test_custom_params(self):
        policy = RetryPolicy(max_retries=5, base_delay=2.0, max_delay=60.0)
        assert policy.max_retries == 5
        assert policy.base_delay == 2.0
        assert policy.max_delay == 60.0

    def test_zero_max_retries_is_valid(self):
        policy = RetryPolicy(max_retries=0)
        assert policy.max_retries == 0

    def test_negative_max_retries_raises(self):
        with pytest.raises(ValueError, match="max_retries"):
            RetryPolicy(max_retries=-1)

    def test_zero_base_delay_raises(self):
        with pytest.raises(ValueError, match="base_delay"):
            RetryPolicy(base_delay=0.0)

    def test_max_delay_less_than_base_raises(self):
        with pytest.raises(ValueError, match="max_delay"):
            RetryPolicy(base_delay=10.0, max_delay=5.0)


# ---------------------------------------------------------------------------
# AC2 — Exponential backoff formula
# ---------------------------------------------------------------------------

class TestBackoffCalculation:
    def test_attempt_0(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=100.0)
        with patch("random.uniform", return_value=0.0):  # no jitter
            delay = policy._calculate_delay(attempt=0)
        assert delay == pytest.approx(1.0)  # 1 * 2^0

    def test_attempt_1(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=100.0)
        with patch("random.uniform", return_value=0.0):
            delay = policy._calculate_delay(attempt=1)
        assert delay == pytest.approx(2.0)  # 1 * 2^1

    def test_attempt_2(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=100.0)
        with patch("random.uniform", return_value=0.0):
            delay = policy._calculate_delay(attempt=2)
        assert delay == pytest.approx(4.0)  # 1 * 2^2

    def test_capped_at_max_delay(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=5.0)
        with patch("random.uniform", return_value=0.0):
            delay = policy._calculate_delay(attempt=10)  # would be 1024s
        assert delay == pytest.approx(5.0)

    def test_base_delay_multiplier(self):
        policy = RetryPolicy(base_delay=2.0, max_delay=100.0)
        with patch("random.uniform", return_value=0.0):
            delay = policy._calculate_delay(attempt=1)
        assert delay == pytest.approx(4.0)  # 2 * 2^1


# ---------------------------------------------------------------------------
# AC3 — Jitter applied
# ---------------------------------------------------------------------------

class TestJitter:
    def test_jitter_added(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=100.0)
        # jitter = uniform(0, delay*0.1) → jitter range [0, 0.1]
        with patch("random.uniform", return_value=0.05):
            delay = policy._calculate_delay(attempt=0)
        assert delay == pytest.approx(1.05)  # 1.0 + 0.05

    def test_jitter_zero_is_possible(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=100.0)
        with patch("random.uniform", return_value=0.0):
            delay = policy._calculate_delay(attempt=0)
        assert delay == pytest.approx(1.0)

    def test_jitter_range_correct(self):
        policy = RetryPolicy(base_delay=1.0, max_delay=100.0)
        # Random.uniform gọi với args (0, delay*0.1)
        with patch("random.uniform") as mock_uniform:
            mock_uniform.return_value = 0.0
            policy._calculate_delay(attempt=0)
            mock_uniform.assert_called_once_with(0, pytest.approx(0.1))


# ---------------------------------------------------------------------------
# AC4 — max_retries configurable
# ---------------------------------------------------------------------------

class TestMaxRetries:
    def test_no_retry_success(self):
        """max_retries=0 → 0 retries, success on first attempt."""
        policy = RetryPolicy(max_retries=0, base_delay=0.01, max_delay=1.0)
        calls = 0

        async def factory():
            nonlocal calls
            calls += 1
            return "ok"

        result = asyncio.get_event_loop().run_until_complete(policy.execute(factory))
        assert result == "ok"
        assert calls == 1

    def test_zero_retries_raises_after_one_fail(self):
        """max_retries=0 → fail immediately on first exception."""
        policy = RetryPolicy(max_retries=0, base_delay=0.01)

        async def factory():
            raise _make_timeout_exc()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(TargetSiteTimeout):
                asyncio.get_event_loop().run_until_complete(policy.execute(factory))

    def test_retries_3_times_then_raises(self):
        """Default: 3 retries → 4 total attempts, then raises."""
        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            raise _make_timeout_exc()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(TargetSiteTimeout):
                asyncio.get_event_loop().run_until_complete(policy.execute(factory))

        assert call_count == 4  # 1 original + 3 retries

    def test_succeeds_on_second_attempt(self):
        """Fail once, succeed on second attempt."""
        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        attempts = [False, True]  # first fail, then succeed

        async def factory():
            if attempts:
                should_succeed = attempts.pop(0)
                if not should_succeed:
                    raise _make_timeout_exc()
            return "success"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = asyncio.get_event_loop().run_until_complete(policy.execute(factory))
        assert result == "success"


# ---------------------------------------------------------------------------
# AC5 — Retry chỉ cho TargetSiteTimeout + RateLimitExceeded
# ---------------------------------------------------------------------------

class TestRetryConditions:
    def test_timeout_triggers_retry(self):
        policy = RetryPolicy(max_retries=2, base_delay=0.01)
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            raise _make_timeout_exc()

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(TargetSiteTimeout):
                asyncio.get_event_loop().run_until_complete(policy.execute(factory))

        assert call_count == 3      # 1 + 2 retries
        assert mock_sleep.call_count == 2

    def test_rate_limit_triggers_retry(self):
        policy = RetryPolicy(max_retries=2, base_delay=0.01)
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            raise _make_rate_limit_exc()

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RateLimitExceeded):
                asyncio.get_event_loop().run_until_complete(policy.execute(factory))

        assert call_count == 3

    def test_rate_limit_retry_after_overrides_delay(self):
        """RateLimitExceeded với retry_after=20 → delay >= 20 (max với calculated)."""
        policy = RetryPolicy(max_retries=1, base_delay=1.0, max_delay=60.0)

        async def factory():
            raise _make_rate_limit_exc(retry_after=20)

        captured_delays = []
        original_sleep = asyncio.sleep

        async def capture_sleep(delay):
            captured_delays.append(delay)

        with patch("asyncio.sleep", side_effect=capture_sleep):
            with pytest.raises(RateLimitExceeded):
                asyncio.get_event_loop().run_until_complete(policy.execute(factory))

        assert len(captured_delays) == 1
        assert captured_delays[0] >= 20.0  # retry_after honoured

    def test_site_check_error_does_not_retry(self):
        """SiteCheckError (non-retryable) → raise ngay, không retry."""
        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            raise SiteCheckError("Site", "https://s.com", error_type="ParseError")

        with pytest.raises(SiteCheckError):
            asyncio.get_event_loop().run_until_complete(policy.execute(factory))

        assert call_count == 1  # không retry

    def test_generic_exception_does_not_retry(self):
        """Generic Exception → raise ngay."""
        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            raise ValueError("unexpected")

        with pytest.raises(ValueError):
            asyncio.get_event_loop().run_until_complete(policy.execute(factory))

        assert call_count == 1


# ---------------------------------------------------------------------------
# AC6 — ProxyDeadError → re-raise ngay, không retry
# ---------------------------------------------------------------------------

class TestProxyDeadErrorHandling:
    def test_proxy_dead_raises_immediately(self):
        """ProxyDeadError → escalate ngay, không retry cùng proxy."""
        policy = RetryPolicy(max_retries=5, base_delay=0.01)
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            raise _make_proxy_exc()

        with pytest.raises(ProxyDeadError):
            asyncio.get_event_loop().run_until_complete(policy.execute(factory))

        assert call_count == 1  # chỉ 1 lần gọi, không retry

    def test_proxy_dead_no_sleep(self):
        """ProxyDeadError → không sleep."""
        policy = RetryPolicy(max_retries=3, base_delay=0.01)

        async def factory():
            raise _make_proxy_exc()

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(ProxyDeadError):
                asyncio.get_event_loop().run_until_complete(policy.execute(factory))

        mock_sleep.assert_not_called()

    def test_success_after_transient_timeout(self):
        """Timeout → retry → success: không raise, trả về kết quả."""
        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        call_count = 0

        async def factory():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise _make_timeout_exc()
            return "found"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = asyncio.get_event_loop().run_until_complete(policy.execute(factory))

        assert result == "found"
        assert call_count == 2
