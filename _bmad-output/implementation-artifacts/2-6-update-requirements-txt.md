# Story 2.6: Update requirements.txt

Status: review

## Story

As a developer,
I want to update `requirements.txt` với tất cả new dependencies cho async engine,
so that `pip install -r requirements.txt` cài đầy đủ packages.

## Acceptance Criteria

1. **AC1:** `aiohttp>=3.9.0` added
2. **AC2:** `aiofiles>=23.0` added
3. **AC3:** `aioresponses>=0.7.6` added (dev dependency)
4. **AC4:** `python-dotenv>=1.0.0` added (for Story 4.2 prep)
5. **AC5:** `rich>=13.0` added (for Story 5.3 prep)
6. **AC6:** Separate `requirements-dev.txt` cho test dependencies
7. **AC7:** `pip install -r requirements.txt` succeeds cleanly

## Tasks / Subtasks

- [x] Task 1 — Audit current dependencies
  - [x] Read existing `requirements.txt`
  - [x] Check for conflicts or outdated packages

- [x] Task 2 — Update `requirements.txt` (production)
  - [x] `aiohttp>=3.9.0`
  - [x] `aiofiles>=23.0`
  - [x] `python-dotenv>=1.0.0`
  - [x] `rich>=13.0`
  - [x] Keep all existing dependencies

- [x] Task 3 — Create `requirements-dev.txt`
  - [x] `-r requirements.txt` (inherit production deps)
  - [x] `pytest>=8.0`
  - [x] `aioresponses>=0.7.6`
  - [x] `pytest-asyncio>=0.23`

- [x] Task 4 — Verify install
  - [x] `pip install -r requirements.txt` — success (aiofiles 25.1.0, python-dotenv 1.2.1, rich 14.3.3)
  - [x] `pip install -r requirements-dev.txt` — success (pytest-asyncio 1.2.0)

## Dev Notes

### AC3 — aioresponses moved to dev
`aioresponses` đã có trong requirements.txt cũ nhưng là test-only dependency. Di chuyển sang `requirements-dev.txt` — correct classification.

## Dev Agent Record

### Agent Model Used
Gemini 2.5 Pro (Antigravity) — 2026-03-27

### Completion Notes List
- `aioresponses` di chuyển từ production → dev (správné classification)
- `aiofiles 25.1.0`, `python-dotenv 1.2.1`, `rich 14.3.3` installed successfully
- `pytest-asyncio 1.2.0` installed via requirements-dev.txt

### File List
- `requirements.txt` [MODIFIED] — thêm aiofiles, python-dotenv, rich; xóa aioresponses
- `requirements-dev.txt` [NEW] — pytest, pytest-asyncio, aioresponses

### Change Log
- 2026-03-27: Story 2.6 implemented — both requirements files updated and verified
