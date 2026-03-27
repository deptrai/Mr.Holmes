# Story 4.1: Setup pytest + aioresponses Framework

Status: done

## Story

As a developer,
I want to setup pytest framework với aioresponses cho async HTTP mocking,
so that unit tests có thể chạy cho tất cả core modules mà không cần real HTTP requests.

## Acceptance Criteria

1. **AC1:** `pytest` configured với `conftest.py` tại project root
2. **AC2:** `pytest-asyncio` cho async test support
3. **AC3:** `aioresponses` fixtures cho HTTP mocking
4. **AC4:** Test directory structure: `tests/` mirror `Core/` structure
5. **AC5:** ≥ 3 test cases cho 3 error strategies (Status-Code, Message, Response-Url)
6. **AC6:** `pytest` runs cleanly: `python -m pytest tests/`

## Tasks / Subtasks

- [x] Task 1 — Create test infrastructure
  - [x] `tests/conftest.py` — shared fixtures
  - [x] `pytest.ini` — pytest config
  - [x] `tests/__init__.py`

- [x] Task 2 — Create aioresponses fixtures
  - [x] `site_config_factory` fixture
  - [x] `mock_aiohttp` fixture (aioresponses)
  - [x] `status_code_site`, `message_site`, `response_url_site` fixtures

- [x] Task 3 — Write tests cho 3 error strategies
  - [x] `test_status_code_found()`, `test_status_code_not_found()`
  - [x] `test_message_found()`, `test_message_not_found()`
  - [x] `test_response_url_found()`, `test_response_url_not_found()`

- [x] Task 4 — Verify: `python -m pytest tests/ -v`

## Dev Notes

### Dependencies
- **REQUIRES Story 2.6** — pytest, aioresponses in requirements
- **BENEFITS FROM Story 2.1** — async search to test

### Architecture Compliance
- [Source: `architecture.md`#Testing] pytest + aioresponses
- [Source: `prd.md`#NFR3] 60% coverage target

### File Structure
```
tests/
├── conftest.py          # NEW — shared fixtures
├── __init__.py          # NEW
├── models/              # mirror Core/models/
├── engine/              # mirror Core/engine/
├── proxy/               # mirror Core/proxy/
└── support/             # mirror Core/Support/
pytest.ini               # NEW (or pyproject.toml section)
```

## Dev Agent Record
### Agent Model Used
Gemini 2.5 Pro
### Completion Notes List
- Tạo `pytest.ini` với `asyncio_mode=strict`, `testpaths=tests`, filter warnings.
- Tạo `tests/conftest.py` với: `mock_aiohttp` (aioresponses fixture), `site_config_factory`, và 3 preconfigured site fixtures.
- Tạo `tests/engine/test_search_strategies.py` với 8 tests cho 3 strategies (AC5).
- Tests/ directory và `__init__.py` đã có sẵn từ trước (AC4).
- 293 tests PASS (AC6).
### File List
- `[NEW] pytest.ini` — pytest configuration
- `[NEW] tests/conftest.py` — shared fixtures (aioresponses, SiteConfig factory)
- `[NEW] tests/engine/test_search_strategies.py` — 8 tests cho 3 error strategies
