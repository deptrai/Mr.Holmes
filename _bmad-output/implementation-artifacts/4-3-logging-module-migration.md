# Story 4.3: Logging Module Migration — `print()` → `logging`

Status: done

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

- [x] Task 1 — Create logging config
- [x] Task 2 — Define level mapping: `[!]` → warning, `[v]` → info, `[I]` → debug, `[N]` → warning
- [x] Task 3 — Replace print calls in `scan_pipeline.py` (21 calls migrated)
- [x] Task 4 — Replace print calls in `Searcher.py`
- [x] Task 5 — Gradual migration cho remaining modules

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
Gemini 2.5 Pro
### Completion Notes List
- Tạo `Core/config/logging_config.py`: `setup_logging()` (AC1, AC2, AC4) + `get_logger()` (AC5).
- Console handler: stderr (không pollute stdout OSINT output) (AC3).
- File handler: optional qua `enable_file=True` hoặc `MH_LOG_FILE=true` env var (AC4).
- Auto-configure từ `MH_LOG_LEVEL` env var nếu `setup_logging()` chưa được gọi.
- Migrate 21 `print()` trong `scan_pipeline.py` theo level mapping (AC6).
- Cập nhật `Core/config/__init__.py` để export `get_logger`, `setup_logging`.
- 10 tests mới, 322 tổng tests PASS.
### File List
- `[NEW] Core/config/logging_config.py` — logging setup + get_logger()
- `[MODIFIED] Core/config/__init__.py` — export get_logger, setup_logging
- `[MODIFIED] Core/engine/scan_pipeline.py` — 21 print() → logger calls
- `[NEW] tests/config/test_logging_config.py` — 10 unit tests
