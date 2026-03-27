# Story 6.5: CSV Export

Status: ready-for-dev

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

- [ ] Task 1 — Implement CSV exporter (`csv` stdlib)
- [ ] Task 2 — CLI integration
- [ ] Task 3 — Unit tests

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
### Agent Model Used
### Completion Notes List
### File List
