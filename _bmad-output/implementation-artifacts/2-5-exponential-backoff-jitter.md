# Story 2.5: Exponential Backoff + Jitter cho Retry Logic

Status: done

## Story

As a developer,
I want to implement exponential backoff + jitter cho retry logic trong async search,
so that rate-limited sites được retry một cách thông minh thay vì retry ngay lập tức.

## Acceptance Criteria

1. **AC1:** `RetryPolicy` class tại `Core/engine/retry.py`
2. **AC2:** Exponential backoff: `delay = base_delay * (2 ** attempt)`
3. **AC3:** Jitter: `delay += random.uniform(0, delay * 0.1)` (prevent thundering herd)
4. **AC4:** Max retries configurable (default: 3)
5. **AC5:** Retry chỉ cho specific exceptions: `TargetSiteTimeout`, `RateLimitExceeded`
6. **AC6:** `ProxyDeadError` → switch proxy, không retry cùng proxy

## Tasks / Subtasks

- [x] Task 1 — Implement `RetryPolicy` class
  - [x] `max_retries`, `base_delay`, `max_delay` params
  - [x] `async def execute(coroutine_factory)` — retry wrapper

- [x] Task 2 — Implement backoff calculation
  - [x] `_calculate_delay(attempt) → float`
  - [x] Cap at `max_delay` (default: 30s)

- [x] Task 3 — Integrate into async_search
  - [x] Export RetryPolicy từ `Core/engine/__init__.py`

- [x] Task 4 — Unit tests with time mocking

## Dev Notes

### Backoff Formula

```python
delay = min(base_delay * (2 ** attempt), max_delay)
delay += random.uniform(0, delay * 0.1)  # jitter
```

### Implementation Notes
- `execute(coroutine_factory)` nhận callable (lambda) thay vì coroutine vì coroutine chỉ chạy 1 lần
- `RateLimitExceeded.retry_after` overrides calculated delay nếu lớn hơn (nhưng vẫn cap ở max_delay)
- `ProxyDeadError` re-raise ngay lập tức — proxy switching là Epic 3

### Dependencies

- **REQUIRES Story 2.4** — specific exception types for retry decisions
- **REQUIRES Story 2.1** — async search to wrap

## Dev Agent Record

### Agent Model Used
Gemini 2.5 Pro (Antigravity) — 2026-03-27

### Completion Notes List
- AC6: ProxyDeadError re-raises ngay, không sleep — consistent với Epic 3 (proxy switching)
- RateLimitExceeded: nếu có retry_after header, dùng max(calculated, retry_after) làm delay
- 26 new tests, 213/213 total, 0 regressions

### File List
- `Core/engine/retry.py` [NEW] — RetryPolicy class
- `Core/engine/__init__.py` [MODIFIED] — export RetryPolicy
- `tests/engine/test_retry.py` [NEW] — 26 tests

### Change Log
- 2026-03-27: Story 2.5 implemented — RetryPolicy với exponential backoff + jitter
