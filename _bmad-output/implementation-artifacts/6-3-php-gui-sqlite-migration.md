# Story 6.3: PHP GUI SQLite Migration

Status: ready-for-dev

## Story

As a user,
I want PHP GUI đọc kết quả từ SQLite thay vì chỉ flat files,
so that GUI có thể filter, search, và display results hiệu quả hơn.

## Acceptance Criteria

1. **AC1:** PHP controllers có thể query SQLite database
2. **AC2:** Investigation list page — query `investigations` table
3. **AC3:** Findings detail page — query `findings` filtered by investigation_id
4. **AC4:** Cross-case search — query across multiple investigations
5. **AC5:** Backward compat — still reads flat files if SQLite unavailable

## Tasks / Subtasks

- [ ] Task 1 — PHP SQLite extension verification
- [ ] Task 2 — Database helper class in PHP
- [ ] Task 3 — Update investigation list controller
- [ ] Task 4 — Update findings detail view
- [ ] Task 5 — Add cross-case search endpoint

## Dev Notes

### Dependencies
- **REQUIRES Story 6.1** — SQLite schema
- **REQUIRES Story 6.2** — data actually in SQLite

### File Structure
```
GUI/
└── Controllers/  # MODIFY — add SQLite reads
```

## Dev Agent Record
### Agent Model Used
### Completion Notes List
### File List
