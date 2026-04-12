# Story 1.7: Input Validation — Sanitize Username & Validate Integers

Status: done

## Story

As a developer,
I want to thêm input validation cho username (chống path traversal) và integer inputs (chống crash),
so that Mr.Holmes không bị exploit qua malicious input và không crash với non-integer input.

## Acceptance Criteria

1. **AC1:** Username sanitized — reject `../`, `/`, `\`, null bytes, special path chars
2. **AC2:** Integer inputs wrapped — `int(input(...))` → `safe_int_input()` with retry
3. **AC3:** Validation module tại `Core/models/validators.py`
4. **AC4:** Validators used ở tất cả entry points: `Menu.py`, `Searcher.py`
5. **AC5:** Unit tests cover: valid input, path traversal attempt, non-integer, empty string

## Tasks / Subtasks

- [x] Task 1 — Create `Core/models/validators.py`
  - [x] `sanitize_username(username: str) → str` — strip dangerous chars
  - [x] `safe_int_input(prompt: str, valid_range: range) → int` — retry on invalid
  - [x] `validate_target(target: str, subject_type: str) → str` — dispatch to type-specific validator

- [x] Task 2 — Implement username sanitization
  - [x] Reject: `..`, `/`, `\`, `\x00`, `>`, `<`, `|`, `:`, `"`, `*`, `?`
  - [x] Max length: 255 chars
  - [x] Raise `ConfigurationError` on invalid

- [x] Task 3 — Implement safe integer input
  - [x] Catch `ValueError` on `int()` conversion
  - [x] Retry with message instead of crashing
  - [x] Optional `valid_range` → reject out-of-range

- [x] Task 4 — Apply validators to entry points
  - [x] `Menu.py` — wrap `int(input(...))` calls with `safe_int_input(valid_range=range(1,16))`
  - [x] `scan_pipeline.py` (successor to Searcher.py after Story 1.3 refactor) — 8 `int(input())` calls replaced
  - [x] `scan_pipeline.py` `__init__` — sanitize username before use in file paths

- [x] Task 5 — Unit tests
  - [x] `tests/models/test_validators.py` — 25 tests (14 sanitize_username, 6 safe_int_input, 5 validate_target)

## Dev Notes

### Security Vulnerabilities Found

**Path Traversal via Username:**
```python
# Searcher.py line 209:
folder = "GUI/Reports/Usernames/" + username + "/"
# If username = "../../etc/passwd" → writes to arbitrary path!
```

**Crash on Non-Integer Input:**
```python
# Searcher.py line 248:
choice = int(input("[+] ..."))
# If user types "abc" → ValueError → crash
```

→ `int(input())` appears at lines 248, 282, 287, 312, 316 in `Searcher.py` alone.

### Dependencies

- Uses `ConfigurationError` from Story 1.1 (exceptions.py)
- Otherwise independent

### Architecture Compliance

- [Source: `architecture.md`#Input Validation]
- [Source: `prd.md`#FR18] Input validation requirement

### File Structure

```
Core/
└── models/
    └── validators.py    # NEW
tests/
└── models/
    └── test_validators.py  # NEW
Core/Support/
└── Menu.py              # MODIFY — wrap int(input()) calls
Core/
└── Searcher.py          # MODIFY — sanitize username, wrap int(input())
```

## Dev Agent Record

### Agent Model Used
Gemini 2.5 Pro (Antigravity) — 2026-03-27

### Completion Notes List
- Tạo `Core/models/validators.py` với 3 functions: `sanitize_username`, `safe_int_input`, `validate_target`
- `sanitize_username` dùng regex để reject `..`, `/`, `\`, null byte, shell special chars; max 255 chars; raise `ConfigurationError(field_name='username')`
- `safe_int_input` dùng retry loop thay vì crash; supports `valid_range` param
- Phát hiện: sau Story 1.3 refactor, `int(input())` calls đã chuyển từ `Searcher.py` → `Core/engine/scan_pipeline.py` (8 calls). Apply đúng ở đó
- `ScanPipeline.__init__` sanitize username ngay khi nhận → toàn bộ pipeline protected
- Menu.py: `safe_int_input(valid_range=range(1,16))` để block invalid menu choices
- 25/25 unit tests pass; 107/107 regression tests pass (0 regressions)

### File List
- `Core/models/validators.py` [NEW]
- `tests/models/test_validators.py` [NEW]
- `Core/engine/scan_pipeline.py` [MODIFIED] — import validators, sanitize at __init__, 8 int(input) → safe_int_input
- `Core/Support/Menu.py` [MODIFIED] — import validators, 1 int(input) → safe_int_input, ConfigurationError import

### Change Log
- 2026-03-27: Story 1.7 implemented — input validation & sanitization (path traversal + crash protection)
