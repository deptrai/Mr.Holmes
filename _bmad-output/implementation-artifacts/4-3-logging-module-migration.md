# Story 4.3: Logging Module Migration — `print()` → `logging`

Status: ready-for-dev

## Story

As a developer,
I want to thay thế tất cả `print()` calls bằng Python `logging` module,
so that output có log levels, configurable filters, và structured format.

## Acceptance Criteria

1. **AC1:** Logger setup tại `Core/config/logging_config.py`
2. **AC2:** Log levels: DEBUG, INFO, WARNING, ERROR theo severity
3. **AC3:** Console handler với Rich formatting (prep cho Story 5.3)
4. **AC4:** File handler optional — write to `logs/mrholmes.log`
5. **AC5:** Mỗi module dùng `logger = logging.getLogger(__name__)`
6. **AC6:** Tất cả `print(Font.Color.RED + "[!]"...)` → `logger.error(...)`

## Tasks / Subtasks

- [ ] Task 1 — Create logging config
- [ ] Task 2 — Define level mapping: `[!]` → ERROR, `[v]` → INFO, `[I]` → DEBUG, `[N]` → WARNING
- [ ] Task 3 — Replace print calls in `Requests_Search.py` (highest impact)
- [ ] Task 4 — Replace print calls in `Searcher.py`
- [ ] Task 5 — Gradual migration cho remaining modules

## Dev Notes

### Print-to-Log Level Mapping
| Pattern | Current | → Level |
|---------|---------|---------|
| `[!]` RED | Error/not found | `logger.warning()` |
| `[v]` YELLOW | Found/success | `logger.info()` |
| `[I]` BLUE | Info/status | `logger.debug()` |
| `[N]` BLUE | Connection issue | `logger.warning()` |
| `[+]` GREEN | Progress/setup | `logger.info()` |

### Dependencies
- Independent — CAN run in parallel

### File Structure
```
Core/config/
└── logging_config.py  # NEW
```

## Dev Agent Record
### Agent Model Used
### Completion Notes List
### File List
