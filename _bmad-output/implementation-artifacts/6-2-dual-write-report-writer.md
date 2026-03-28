# Story 6.2: Dual-Write ReportWriter

Status: review

## Story

As a developer,
I want to implement `ReportWriter` ghi kết quả đồng thời vào flat files (backward compat) VÀ SQLite,
so that PHP GUI vẫn đọc được files cũ + có thể query SQLite cho features mới.

## Acceptance Criteria

1. **AC1:** `ReportWriter` class tại `Core/reporting/writer.py`
2. **AC2:** `write(investigation, results)` → ghi `.txt` + `.json` + SQLite
3. **AC3:** Flat file format identical với current output
4. **AC4:** SQLite insert investigation + findings records
5. **AC5:** Atomic — nếu SQLite fail, flat files vẫn được ghi (graceful degradation)

## Tasks / Subtasks

- [x] Task 1 — Implement ReportWriter class
- [x] Task 2 — Flat file writer (match current format exactly)
- [x] Task 3 — SQLite writer (insert records)
- [x] Task 4 — Error handling — SQLite failure doesn't block file output
- [x] Task 5 — Integration into ScanPipeline
- [x] Task 6 — Unit tests

### Review Findings
- [x] [Review][Patch] Uncaught OSError during directory creation — `mkdir(parents=True)` in `_write_json` and `_write_txt` is outside the try-catch block and can crash the pipeline if permission is denied. [Core/reporting/writer.py:94,112]

## Dev Notes

### Dependencies
- **REQUIRES Story 6.1** — SQLite schema
- **REQUIRES Story 1.1** — ScanResult dataclass
- **REQUIRES Story 1.3** — ScanPipeline integration point

### Architecture Compliance
- [Source: `architecture.md`#Decision 6] Dual-write strategy
- [Source: `prd.md`#NFR4] Backward compatible

### File Structure
```
Core/reporting/
└── writer.py  # NEW — ReportWriter
```

## Dev Agent Record
### Agent Model Used: Claude Sonnet 4.6 (Thinking)
### Completion Notes List
- ReportWriter at Core/reporting/writer.py with two public methods:
  - write(): full dual-write (txt+json+sqlite) for batch/test scenarios
  - write_json_and_sqlite(): for ScanPipeline where txt already written inline
- AC3: txt format `[SiteName] URL\n` identical to existing _on_progress output
- AC4: SQLite inserts investigation + findings + tags via existing Database singleton
- AC5: _write_sqlite() catches all exceptions and returns None — flat files never blocked
- ScanPipeline: added scan_results accumulator list, populates in _on_progress
- 15 unit tests: AC1-AC5, tags, graceful degradation, pipeline method
- All 463 tests pass
### File List
- Core/reporting/writer.py (NEW)
- Core/engine/scan_pipeline.py (MODIFIED: scan_results accumulator + ReportWriter call)
- tests/reporting/test_writer.py (NEW)
