# Story 2.4: Custom Exception Classes

Status: review

## Story

As a developer,
I want to tạo custom exception classes chuyên biệt cho OSINT operations,
so that error handling có structured context (site_name, url, status_code) thay vì generic `except Exception: pass`.

## Acceptance Criteria

1. **AC1:** Exception hierarchy tại `Core/models/exceptions.py` (extends Story 1.1)
2. **AC2:** Classes: `TargetSiteTimeout`, `ProxyDeadError`, `RateLimitExceeded`, `ScraperError`, `SiteCheckError`
3. **AC3:** Mỗi exception chứa structured context attributes
4. **AC4:** Integrated vào async search — raise specific exceptions thay vì generic
5. **AC5:** Logging integration — exceptions log đầy đủ context

## Tasks / Subtasks

- [x] Task 1 — Extend `Core/models/exceptions.py`
  - [x] `TargetSiteTimeout(OSINTError)` — attrs: site_name, url, timeout_seconds
  - [x] `ProxyDeadError(OSINTError)` — attrs: proxy_url, site_name
  - [x] `RateLimitExceeded(OSINTError)` — attrs: site_name, status_code, retry_after
  - [x] `ScraperError(OSINTError)` — attrs: scraper_name, site_name, original_error
  - [x] `SiteCheckError(OSINTError)` — attrs: site_name, url, error_type, status_code

- [x] Task 2 — Integrate into async_search.py
  - [x] `asyncio.TimeoutError` → `TargetSiteTimeout`
  - [x] `aiohttp.ClientProxyConnectionError` → `ProxyDeadError`
  - [x] HTTP 429 → `RateLimitExceeded`
  - [x] HTTP 403 → `RateLimitExceeded` (possible block)

- [x] Task 3 — Unit tests
  - [x] Test exception creation with context
  - [x] Test `isinstance()` hierarchy checks
  - [x] Test `str()` representation includes context

## Dev Notes

### Dependencies

- **EXTENDS Story 1.1** — OSINTError base class
- **INTEGRATES Story 2.1** — async search raises these exceptions
- **USED BY Story 2.5** — backoff logic catches specific types

### Architecture Compliance

- [Source: `architecture.md`#Decision 5] Custom exception hierarchy
- [Source: `prd.md`#NFR7] Structured error messages

### File Structure

```
Core/models/
└── exceptions.py  # MODIFY — add new exception classes
```

## Dev Agent Record

### Agent Model Used
Gemini 2.5 Pro (Antigravity) — 2026-03-27

### Completion Notes List
- `SiteCheckError(OSINTError)` — attrs: site_name, url, error_type, status_code, original_error
- Integrated exceptions vào `async_search.py`: TargetSiteTimeout, ProxyDeadError, SiteCheckError trong except blocks; RateLimitExceeded cho HTTP 429/403
- Added `_parse_retry_after()` helper xử lý Retry-After header
- Added `logging.getLogger(__name__)` + `logger.warning()` cho mỗi exception path (AC5)
- Fixed 1 regression: `test_timeout_returns_timeout_status` — update assertion từ exact match sang `in` check
- 28 new tests (7 hierarchy + 16 context/str + 2 integration + 3 misc), 187/187 total pass

### File List
- `Core/models/exceptions.py` [MODIFIED] — thêm `SiteCheckError`
- `Core/models/__init__.py` [MODIFIED] — export `SiteCheckError`
- `Core/engine/async_search.py` [MODIFIED] — integrate exceptions + logging + `_parse_retry_after()`
- `tests/models/test_exceptions.py` [NEW] — 28 tests
- `tests/engine/test_async_search.py` [MODIFIED] — fix regression

### Change Log
- 2026-03-27: Story 2.4 implemented — SiteCheckError, async_search exception integration, logging, 28 tests
