# Story 4.4: Remove Silent `except Exception: pass`

Status: ready-for-dev

## Story

As a developer,
I want to loại bỏ tất cả `except Exception: pass` blocks và thay bằng structured error handling,
so that bugs không bị nuốt im và errors được log/report đúng cách.

## Acceptance Criteria

1. **AC1:** Grep `except Exception` → 0 instances còn `pass` hoặc chỉ `print("Something went wrong")`
2. **AC2:** Mỗi catch block hoặc: log error, raise specific exception, hoặc handle gracefully
3. **AC3:** Sử dụng OSINTError hierarchy (Story 2.4) cho specific catches
4. **AC4:** Behavior preservation — user vẫn thấy error messages, không crash

## Tasks / Subtasks

- [ ] Task 1 — Audit: `grep -rn "except Exception" Core/`
- [ ] Task 2 — Classify each: swallow (fix), generic print (improve), valid catch (keep)
- [ ] Task 3 — Replace swallowed exceptions → `logger.error(...)` + specific exception
- [ ] Task 4 — Replace `print("Something went wrong")` → `logger.error(str(e), exc_info=True)`
- [ ] Task 5 — Test that previously-hidden errors now surface

## Dev Notes

### Known Silent Catches (from audit)
- `Searcher.py` lines 45, 50, 55, etc. — `except Exception as e: print("Something went wrong")`
- `Searcher.py` lines 138, 145, 158 — connection fallback catches
- Pattern repeats across `Searcher_phone.py`, `Searcher_website.py`, `Searcher_person.py`

### Dependencies
- **REQUIRES Story 2.4** — OSINTError hierarchy
- **REQUIRES Story 4.3** — logging module

### File Structure
```
Core/
├── Searcher.py           # MODIFY
├── Searcher_phone.py     # MODIFY
├── Searcher_website.py   # MODIFY
├── Searcher_person.py    # MODIFY
└── Support/
    └── Requests_Search.py # MODIFY
```

## Dev Agent Record
### Agent Model Used
### Completion Notes List
### File List
