# Story 1.5: Extract ProxyManager Class

Status: done
Owner: BMad

## Story

As a developer,
I want to extract proxy configuration code (duplicated across 4 files) thành `ProxyManager` class,
so that proxy logic chỉ tồn tại ở 1 nơi và dễ mở rộng cho Epic 3 (auto-rotate, health-check).

## Acceptance Criteria

1. **AC1:** `ProxyManager` class tại `Core/proxy/manager.py`
2. **AC2:** Gom proxy resolution code từ 4 files: `Searcher.py`, `Searcher_phone.py`, `Searcher_website.py`, `Searcher_person.py`
3. **AC3:** Methods: `configure(choice)`, `get_proxy()`, `get_identity()`, `reset()`
4. **AC4:** ip-api.com lookup centralized trong `ProxyManager`
5. **AC5:** 4 searcher files gọi `ProxyManager` thay vì inline proxy code
6. **AC6:** Unit tests mock ip-api response

## Tasks / Subtasks

- [ ] Task 1 — Create `Core/proxy/` package
  - [ ] `Core/proxy/__init__.py`
  - [ ] `Core/proxy/manager.py`

- [ ] Task 2 — Implement ProxyManager class
  - [ ] `configure(choice: int)` — setup proxy or None
  - [ ] `get_proxy() → dict | None`
  - [ ] `get_identity() → str` — ip-api lookup
  - [ ] `reset()` — clear proxy (fallback scenario)

- [ ] Task 3 — Replace proxy code in 4 files
  - [ ] `Searcher.py` lines 250-269, 318-331 (2 occurrences)
  - [ ] `Searcher_phone.py` line 146
  - [ ] `Searcher_website.py` lines 47, 163, 279
  - [ ] `Searcher_person.py` line 117

- [ ] Task 4 — Unit tests
  - [ ] Mock `ip-api.com` response
  - [ ] Test: choice=1 → proxy dict returned
  - [ ] Test: choice=2 → None returned
  - [ ] Test: ip-api failure → graceful fallback

## Dev Notes

### Proxy Code Duplication Map

| File | Lines | Occurrences |
|------|-------|-------------|
| `Searcher.py` | 250-269, 318-331, 148-162 | 3 |
| `Searcher_phone.py` | ~146 | 1 |
| `Searcher_website.py` | ~47, ~163, ~279 | 3 |
| `Searcher_person.py` | ~117 | 1 |
| **Total** | | **8 occurrences** |

### Current Pattern (identical everywhere):

```python
http_proxy = Proxies.proxy.final_proxis
http_proxy2 = Proxies.proxy.choice3
source = "http://ip-api.com/json/" + http_proxy2
access = urllib.request.urlopen(source)
content = access.read()
final = json.loads(content)
identity = "...".format(final["regionName"], final["country"])
```

### Dependencies

- Independent — CAN be done in parallel with Story 1.1-1.4
- Foundation for Epic 3 (auto-rotate, health-check)

### Architecture Compliance

- [Source: `architecture.md`#ProxyManager Pattern]
- [Source: `architecture.md`#Module Structure] `Core/proxy/`

### File Structure

```
Core/
└── proxy/
    ├── __init__.py   # NEW
    └── manager.py    # NEW — ProxyManager class
tests/
└── proxy/
    ├── __init__.py           # NEW
    └── test_proxy_manager.py # NEW
```

## Dev Agent Record

### Agent Model Used
### Completion Notes List
### File List

### Review Findings

- [x] [Review][Decision] **AC5 — 4 legacy searcher files replaced** — Fixed: all 4 files + scan_pipeline now use ProxyManager
- [x] [Review][Decision] **Narrow exception catch in `_resolve_identity()`** — Fixed: `(OSError, json.JSONDecodeError, KeyError, ValueError)`
- [x] [Review][Decision] **scan_pipeline double-read removed** — Fixed: added `proxy_ip` property, removed `Proxies` import
- [x] [Review][Patch] **Unused import `BytesIO` removed** [tests/proxy/test_proxy_manager.py]
- [x] [Review][Patch] **Test cho `configure()` invalid type thêm** — 2 tests (string, None)
- [x] [Review][Patch] **Test verify `timeout=10` thêm** — asserts urlopen called with timeout=10
- [x] [Review][Defer] **ip-api.com rate limiting (45 req/min)** — Pre-existing, chỉ centralized chỗ mới. Cần rate-limit/cache ở Epic 3. — deferred, pre-existing
- [x] [Review][Defer] **Proxies.py class-level side-effects** — random.choice chạy lúc import, không thể refresh proxy. — deferred, pre-existing
- [x] [Review][Defer] **Empty proxy file → IndexError** — `random.choice([])` crash lúc import Proxies. — deferred, pre-existing
