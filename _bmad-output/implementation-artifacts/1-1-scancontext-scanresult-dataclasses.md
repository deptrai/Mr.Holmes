# Story 1.1: Tạo ScanContext và ScanResult Dataclasses

Status: done

## Story

As a developer,
I want to replace the 19-parameter method signature trong `Requests_Search.Search.search()` bằng typed dataclasses,
so that code trở nên readable, maintainable, và type-safe — mở đường cho async refactoring.

## Acceptance Criteria

1. **AC1:** `ScanContext` dataclass chứa tất cả input configuration cho 1 scan session
2. **AC2:** `ScanResult` dataclass thu thập kết quả từng site check — thay thế shared mutable lists
3. **AC3:** `ScanConfig` dataclass chứa runtime settings (proxy, tags behavior, writable mode)
4. **AC4:** `OSINTError` exception hierarchy được tạo với ≥ 5 exception types
5. **AC5:** File mới nằm đúng vị trí: `Core/models/scan_context.py`, `Core/models/scan_result.py`, `Core/models/exceptions.py`
6. **AC6:** `__init__.py` exports tất cả public classes
7. **AC7:** Unit tests cover creation, defaults, và edge cases cho mỗi dataclass
8. **AC8:** Existing code KHÔNG bị thay đổi — chỉ tạo files mới (backward compatible)

## Tasks / Subtasks

- [x] Task 1 — Create `Core/models/` package (AC: #5, #6)
  - [x] Tạo `Core/models/__init__.py` với public exports
  - [x] Verify directory structure matches architecture doc

- [x] Task 2 — Implement `ScanContext` dataclass (AC: #1)
  - [x] Map 19 params từ `Requests_Search.Search.search()` vào typed fields
  - [x] Add `@dataclass` decorator với proper defaults
  - [x] Add docstring giải thích purpose và usage

- [x] Task 3 — Implement `ScanResult` dataclass (AC: #2)
  - [x] Fields: site_name, url, found (bool), error_type, tags, scraper_name
  - [x] Replace pattern: `successfull.append()` + `successfullName.append()` → `ScanResult` objects
  - [x] Add `to_json()` method cho report serialization

- [x] Task 4 — Implement `ScanConfig` dataclass (AC: #3)
  - [x] Fields: proxy_enabled, proxy_dict, nsfw_enabled, writable, subject_type
  - [x] Separate runtime config từ per-site context

- [x] Task 5 — Implement `OSINTError` hierarchy (AC: #4)
  - [x] Base: `OSINTError(Exception)`
  - [x] `TargetSiteTimeout`, `ProxyDeadError`, `RateLimitExceeded`, `ScraperError`, `ConfigurationError`
  - [x] Each exception stores structured context (site_name, url, status_code)

- [x] Task 6 — Write unit tests (AC: #7)
  - [x] `tests/models/test_scan_context.py`
  - [x] `tests/models/test_scan_result.py`
  - [x] Tests: creation with defaults, field validation, to_json serialization

## Dev Notes

### Existing Code Analysis — Critical Context

**`Requests_Search.Search.search()` — 19 parameters (line 19 of `Core/Support/Requests_Search.py`):**

```python
def search(error, report, site1, site2, http_proxy, sites, data1, username,
           subject, successfull, name, successfullName, is_scrapable,
           ScraperSites, Writable, main, json_file, json_file2, Tag, Tags, MostTags):
```

**Parameter → Dataclass Field Mapping:**

| Current Param | Type | → Dataclass | Field Name |
|---------------|------|-------------|------------|
| `username` | str | ScanContext | `target` |
| `subject` | str | ScanContext | `subject_type` ("USERNAME"/"PHONE-NUMBER") |
| `report` | str (filepath) | ScanConfig | `report_path` |
| `http_proxy` | dict/None | ScanConfig | `proxy_dict` |
| `Writable` | bool | ScanConfig | `writable` |
| `json_file` | str (filepath) | ScanConfig | `json_output_path` |
| `json_file2` | str (filepath) | ScanConfig | `json_names_path` |
| `site1` | str (display URL) | Per-site | → ScanResult.url |
| `site2` | str (request URL) | Per-site | → passed at call time |
| `sites` | dict | Per-site | → site data dict |
| `data1` | key | Per-site | → site key |
| `name` | str | Per-site | → ScanResult.site_name |
| `main` | str | Per-site | → ScanResult.main_identifier |
| `error` | str | Per-site | → error detection strategy |
| `is_scrapable` | str("True"/"False") | Per-site | → ScanResult.is_scrapable |
| `Tag` | list[str] | Per-site | → ScanResult.tags |
| `successfull` | list (MUTABLE!) | ELIMINATE | → `list[ScanResult]` |
| `successfullName` | list (MUTABLE!) | ELIMINATE | → `list[ScanResult]` |
| `ScraperSites` | list (MUTABLE!) | ELIMINATE | → filter ScanResult.is_scrapable |
| `Tags` | list (MUTABLE!) | ELIMINATE | → aggregate from ScanResult.tags |
| `MostTags` | list (MUTABLE!) | ELIMINATE | → compute from ScanResult.tags |

**3 Error Detection Strategies (critical pattern):**
1. `"Status-Code"` — Check `response.status_code == 200`
2. `"Message"` — Check if error text NOT in response body
3. `"Response-Url"` — Check if response URL differs from expected redirect

### Architecture Compliance

- [Source: `architecture.md`#Core Architectural Decisions] Pipeline + Registry pattern
- [Source: `architecture.md`#Implementation Patterns] `@dataclass`, `snake_case`, `typing.Protocol`
- [Source: `architecture.md`#Module Structure] `Core/models/` directory
- [Source: `architecture.md`#Enforcement] Mỗi function < 50 LOC, mỗi file < 200 LOC

### File Structure Requirements

```
Core/
└── models/
    ├── __init__.py          # NEW — exports ScanContext, ScanResult, ScanConfig, OSINTError, etc.
    ├── scan_context.py      # NEW — ScanContext, ScanConfig dataclasses
    ├── scan_result.py       # NEW — ScanResult dataclass
    └── exceptions.py        # NEW — OSINTError hierarchy

tests/
└── models/
    ├── __init__.py          # NEW
    ├── test_scan_context.py # NEW
    └── test_scan_result.py  # NEW
```

### Testing Requirements

- Framework: `pytest`
- Test creation với defaults
- Test field types (str, bool, list, Optional)
- Test `ScanResult.to_json()` serialization
- Test exception hierarchy (`isinstance` checks)
- NO integration tests yet — only unit tests cho dataclasses

### Library/Framework Requirements

- Python 3.9+ (`from __future__ import annotations` for `list[str]` syntax)
- `dataclasses` (stdlib)
- `typing` (stdlib — `Optional`, `Protocol`)
- `enum` (stdlib — for `ErrorType` enum)
- `json` (stdlib — for `to_json()`)
- **NO external dependencies** cho story này

### Anti-Patterns — TUYỆT ĐỐI KHÔNG

- ❌ KHÔNG modify `Requests_Search.py` hay `Searcher.py` — đó là Story 1.2 và 1.3
- ❌ KHÔNG dùng `dict` thay cho `dataclass`
- ❌ KHÔNG dùng `Any` type
- ❌ KHÔNG hardcode paths — dùng `pathlib.Path`
- ❌ KHÔNG quên `__init__.py` exports

## Dev Agent Record

### Agent Model Used

Gemini 2.5 Pro

### Completion Notes List

- ✅ Tạo `Core/models/` package đầy đủ (4 files)
- ✅ `ScanContext` dataclass: 7 fields, map hoàn chỉnh 19 params thành typed structure
- ✅ `ScanConfig` dataclass: 5 fields, tách proxy settings và runtime config
- ✅ `ScanResult` dataclass: 7 fields + `found` property + `to_json()` + `to_dict()`
- ✅ `ScanStatus` enum: 7 states (FOUND, NOT_FOUND, BLOCKED, RATE_LIMITED, CAPTCHA, ERROR, TIMEOUT)
- ✅ `ErrorStrategy` enum: 3 values matching site_list.json ("Status-Code", "Message", "Response-Url")
- ✅ `OSINTError` hierarchy: 5 typed exceptions (TargetSiteTimeout, ProxyDeadError, RateLimitExceeded, ScraperError, ConfigurationError)
- ✅ `Core/models/__init__.py`: exports 12 public names
- ✅ Unit tests: 31/31 PASSED (Python 3.9.6, pytest 8.4.2, 0.15s)
- ✅ Backward compatible: KHÔNG sửa bất kỳ file hiện có nào
- ✅ Không dùng external dependencies (chỉ stdlib: dataclasses, typing, enum, json)

### File List

- `Core/models/__init__.py` [NEW]
- `Core/models/scan_context.py` [NEW]
- `Core/models/scan_result.py` [NEW]
- `Core/models/exceptions.py` [NEW]
- `tests/__init__.py` [NEW]
- `tests/models/__init__.py` [NEW]
- `tests/models/test_scan_context.py` [NEW]
- `tests/models/test_scan_result.py` [NEW]
