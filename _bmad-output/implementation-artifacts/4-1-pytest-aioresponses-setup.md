# Story 4.1: Setup pytest + aioresponses Framework

Status: ready-for-dev

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

- [ ] Task 1 — Create test infrastructure
  - [ ] `tests/conftest.py` — shared fixtures
  - [ ] `pytest.ini` hoặc `pyproject.toml` — pytest config
  - [ ] `tests/__init__.py`

- [ ] Task 2 — Create aioresponses fixtures
  - [ ] `mock_session` fixture
  - [ ] `mock_site_data` fixture

- [ ] Task 3 — Write tests cho 3 error strategies
  - [ ] `test_status_code_found()`, `test_status_code_not_found()`
  - [ ] `test_message_found()`, `test_message_not_found()`
  - [ ] `test_response_url_found()`, `test_response_url_not_found()`

- [ ] Task 4 — Verify: `python -m pytest tests/ -v`

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
### Completion Notes List
### File List
