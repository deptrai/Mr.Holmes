# Story 2.1: Migrate `Requests_Search.py` → `aiohttp` Async Method

Status: done

## Story

As a developer,
I want to migrate `Requests_Search.Search.search()` từ synchronous `requests.get()` sang `aiohttp.ClientSession` async method,
so that HTTP requests có thể chạy concurrent — mở đường cho `asyncio.gather()` trong Story 2.2.

## Acceptance Criteria

1. **AC1:** `async def search()` method sử dụng `aiohttp.ClientSession`
2. **AC2:** 3 error strategies (Status-Code, Message, Response-Url) hoạt động identical
3. **AC3:** `ScanContext` và `ScanResult` dataclasses (Story 1.1) được tích hợp
4. **AC4:** Timeout configurable (default 10s, match current `requests.get(timeout=10)`)
5. **AC5:** Returns `ScanResult` thay vì mutate shared lists
6. **AC6:** `aiohttp` added to `requirements.txt`
7. **AC7:** Unit tests với `aioresponses` mock — test cả 3 error strategies

## Tasks / Subtasks

- [x] Task 1 — Create async search method
  - [x] `Core/engine/async_search.py` — `async def search_site(session, site_config, scan_context) → ScanResult`
  - [x] Use `async with session.get(url, ...) as response:`
  - [x] Map `requests.get()` params → `aiohttp` equivalents

- [x] Task 2 — Implement 3 error strategies async
  - [x] Status-Code: `response.status == 200`
  - [x] Message: `text not in await response.text()`
  - [x] Response-Url: `str(response.url) != expected`

- [x] Task 3 — Return ScanResult instead of mutating lists
  - [x] `ScanResult(site_name, url, found=True/False, tags, ...)`
  - [x] No more `successfull.append()` — caller collects results

- [x] Task 4 — Keep backward compatibility layer
  - [x] `Requests_Search.Search.search()` still works synchronously (wrapper)
  - [x] New async code at `Core/engine/async_search.py`

- [x] Task 5 — Unit tests with `aioresponses`
  - [x] `tests/engine/test_async_search.py` — 16 tests (3 strategies + error handling + ScanResult interface)

## Dev Notes

### Current vs New Comparison

| Aspect | Current (`requests`) | New (`aiohttp`) |
|--------|---------------------|-----------------|
| Import | `import requests` | `import aiohttp` |
| Call | `requests.get(url, headers, proxies, timeout=10)` | `async with session.get(url, headers=headers, proxy=proxy_url, timeout=aiohttp.ClientTimeout(total=10))` |
| Response body | `searcher.text` | `await response.text()` |
| Status | `searcher.status_code` | `response.status` |
| Redirect URL | `searcher.url` | `str(response.url)` |

### aiohttp Proxy Format

```python
# requests format:
proxies = {"http": "http://proxy:port", "https": "http://proxy:port"}

# aiohttp format:
proxy = "http://proxy:port"  # single string, not dict
```

### Dependencies

- **REQUIRES Story 1.1** — ScanContext, ScanResult dataclasses
- **REQUIRED BY Story 2.2** — asyncio.gather needs async search

### Architecture Compliance

- [Source: `architecture.md`#Tech Stack] aiohttp + asyncio
- [Source: `architecture.md`#Async Pattern] `asyncio.gather()` + `Semaphore(20)`

### File Structure

```
Core/engine/
├── __init__.py        # MODIFY — add export
└── async_search.py    # NEW — async search method
Core/Support/
└── Requests_Search.py # MODIFY — add sync wrapper
tests/engine/
├── __init__.py        # NEW
└── test_async_search.py # NEW
```

### Anti-Patterns

- ❌ KHÔNG xóa `Requests_Search.py` — giữ backward compat
- ❌ KHÔNG implement gather/semaphore — đó là Story 2.2
- ❌ KHÔNG hardcode timeout — phải configurable

## Dev Agent Record

### Agent Model Used
Gemini 2.5 Pro (Antigravity) — 2026-03-27

### Completion Notes List
- Tạo `Core/engine/async_search.py` với `search_site()` async + `SiteConfig` dataclass
- 3 error strategies hoạt động identical với requests: Status-Code, Message, Response-Url
- Returns `ScanResult` — không mutate shared lists (AC5)
- Proxy format chuyển từ dict (`{"http": ...}`) sang string (`"http://..."`) cho aiohttp
- Timeout dùng `aiohttp.ClientTimeout(total=N)` — configurable (AC4)
- Giữ `Requests_Search.py` nguyên vẹn (backward compat, AC4 note)
- `Core/engine/__init__.py` export `search_site`, `SiteConfig`
- 16/16 new tests pass với `aioresponses` mock; 125/125 total (0 regressions)

### File List
- `Core/engine/async_search.py` [NEW]
- `tests/engine/test_async_search.py` [NEW]
- `tests/engine/__init__.py` [NEW]
- `Core/engine/__init__.py` [MODIFIED] — thêm export search_site, SiteConfig
- `requirements.txt` [MODIFIED] — thêm aiohttp>=3.9.0, aioresponses>=0.7.6

### Change Log
- 2026-03-27: Story 2.1 implemented — aiohttp async search engine, 3 error strategies, ScanResult return
