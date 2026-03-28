# Story 6.5: CSV Export

Status: review

## Story

As a user,
I want to export findings ra CSV cho data analysis tools (Excel, pandas, etc.),
so that results có thể processed, filtered, và visualized bằng external tools.

## Acceptance Criteria

1. **AC1:** CSV export: `python3 MrHolmes.py --export csv --investigation <id>`
2. **AC2:** Columns: site_name, url, status, tags, found_at
3. **AC3:** UTF-8 encoding với BOM cho Excel compatibility
4. **AC4:** Multi-investigation export supported

## Tasks / Subtasks

- [x] Task 1 — Implement CSV exporter (`csv` stdlib)
- [x] Task 2 — CLI integration
- [x] Task 3 — Unit tests

## Dev Notes

### Dependencies
- **REQUIRES Story 6.1** — SQLite data source
- stdlib `csv` module — no extra dependencies

### File Structure
```
Core/reporting/
└── csv_export.py  # NEW
```

## Dev Agent Record
### Agent Model Used: Claude Sonnet 4.6 (Thinking)
### Completion Notes List
- Task 1: `Core/reporting/csv_export.py` — CsvExporter with `export_to_string()` + `export()`. UTF-8-sig (BOM) encoding via `open(..., encoding='utf-8-sig')`. CAST timestamps to TEXT (same fix as 6.4). Tags joined with `;`.
- AC4 multi-investigation: `export(None)` = all, `export([1,2,3])` = specific IDs
- Task 2: Extended `--export choices` to `["pdf", "csv"]`. Changed `--investigation` from `type=int` to `str` for comma-separated support. Added `parse_investigation_ids()` helper. Updated dispatch in MrHolmes.py to route pdf/csv. Updated warning message to mention `all`.
- Task 3: 21 unit tests in `tests/reporting/test_csv_export.py` — 21/21 pass. Also fixed 2 pre-existing PDF tests that assumed `investigation==int`. Full suite: 500 passed.
- Smoke test: `--export csv --investigation 1` ✔, `--export csv --investigation all` ✔
### File List
- Core/reporting/csv_export.py (NEW)
- Core/cli/parser.py (MODIFIED: csv choice, str type, parse_investigation_ids)
- MrHolmes.py (MODIFIED: format-aware dispatch)
- tests/reporting/test_csv_export.py (NEW)
- tests/reporting/test_pdf_export.py (MODIFIED: 2 tests updated for str type)
