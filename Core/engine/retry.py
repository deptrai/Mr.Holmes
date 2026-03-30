"""
Core/engine/retry.py

Exponential backoff + jitter retry policy cho Mr.Holmes async OSINT scanner.
Story 2.5 — Exponential Backoff + Jitter, Epic 2.

Provides:
    RetryPolicy — configurable retry wrapper cho coroutine factories.

Formula (AC2 + AC3):
    delay = min(base_delay * (2 ** attempt), max_delay)
    delay += random.uniform(0, delay * 0.1)   # jitter — prevent thundering herd

Retry conditions (AC5 + AC6):
    TargetSiteTimeout   → retry với backoff
    RateLimitExceeded   → retry, override delay với retry_after nếu lớn hơn
    ProxyDeadError      → re-raise ngay (proxy switching là Epic 3)
    Mọi exception khác  → re-raise ngay (không retry)
"""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Callable, Coroutine, Optional, TypeVar

from Core.models.exceptions import (
    OSINTError,
    ProxyDeadError,
    RateLimitExceeded,
    TargetSiteTimeout,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default config (AC4)
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0   # seconds
DEFAULT_MAX_DELAY = 30.0   # seconds


class RetryPolicy:
    """
    Configurable exponential backoff + jitter retry wrapper (AC1).

    Usage:
        policy = RetryPolicy(max_retries=3, base_delay=1.0, max_delay=30.0)
        result = await policy.execute(lambda: search_site(session, site, username))

    Args:
        max_retries: Số lần retry tối đa sau lần đầu fail (default: 3).
        base_delay:  Delay cơ sở (giây) cho lần retry đầu (default: 1.0).
        max_delay:   Delay tối đa (giây) — cap exponential growth (default: 30.0).
    """

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_BASE_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
    ) -> None:
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries}")
        if base_delay <= 0:
            raise ValueError(f"base_delay must be > 0, got {base_delay}")
        if max_delay < base_delay:
            raise ValueError(f"max_delay ({max_delay}) must be >= base_delay ({base_delay})")

        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    async def execute(
        self,
        coroutine_factory: Callable[[], Coroutine[Any, Any, T]],
    ) -> T:
        """
        Thực thi coroutine với retry policy.

        Args:
            coroutine_factory: Callable trả về coroutine mới mỗi lần gọi.
                               Dùng lambda: để wrap call có arguments.
                               Ví dụ: lambda: search_site(session, site, username)

        Returns:
            Kết quả của coroutine khi thành công.

        Raises:
            ProxyDeadError:    Ngay lập tức, không retry (AC6).
            OSINTError:        Sau khi hết max_retries.
            Exception:         Re-raise nếu không phải OSINTError.
        """
        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):  # +1: attempt 0 = lần chạy đầu
            try:
                return await coroutine_factory()

            except ProxyDeadError:
                # AC6: ProxyDeadError → switch proxy, không retry cùng proxy
                logger.warning(
                    "ProxyDeadError on attempt %d/%d — escalating immediately",
                    attempt + 1, self.max_retries + 1,
                )
                raise

            except (TargetSiteTimeout, RateLimitExceeded) as exc:
                last_exception = exc
                if attempt >= self.max_retries:
                    logger.warning(
                        "%s after %d attempts — giving up",
                        type(exc).__name__, attempt + 1,
                    )
                    break

                delay = self._calculate_delay(attempt, exc)
                logger.warning(
                    "%s on attempt %d/%d — retrying in %.2fs",
                    type(exc).__name__,
                    attempt + 1,
                    self.max_retries + 1,
                    delay,
                )
                await asyncio.sleep(delay)

        raise last_exception  # type: ignore[misc]

    def _calculate_delay(
        self,
        attempt: int,
        exc: Optional[OSINTError] = None,
    ) -> float:
        """
        Tính delay cho lần retry tiếp theo (AC2 + AC3).

        Formula:
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay += random.uniform(0, delay * 0.1)   # 10% jitter

        Nếu exception là RateLimitExceeded và retry_after > calculated delay,
        dùng retry_after thay thế (nhưng vẫn apply jitter).

        Args:
            attempt: Attempt index hiện tại (0-based).
            exc:     Exception đang xử lý (dùng retry_after nếu có).

        Returns:
            Delay tính bằng giây (float).
        """
        # Exponential backoff (AC2)
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)

        # Honour Retry-After header nếu > calculated delay (AC5 + RateLimitExceeded)
        if isinstance(exc, RateLimitExceeded) and exc.retry_after is not None:
            delay = max(delay, float(exc.retry_after))
            delay = min(delay, self.max_delay)  # still cap at max_delay

        # Jitter — 10% của delay, prevent thundering herd (AC3)
        delay += random.uniform(0, delay * 0.1)
        return delay
