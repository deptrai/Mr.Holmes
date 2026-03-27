# Story 6.2: Dual-Write ReportWriter

Status: ready-for-dev

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

- [ ] Task 1 — Implement ReportWriter class
- [ ] Task 2 — Flat file writer (match current format exactly)
- [ ] Task 3 — SQLite writer (insert records)
- [ ] Task 4 — Error handling — SQLite failure doesn't block file output
- [ ] Task 5 — Integration into ScanPipeline
- [ ] Task 6 — Unit tests

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
### Agent Model Used
### Completion Notes List
### File List
