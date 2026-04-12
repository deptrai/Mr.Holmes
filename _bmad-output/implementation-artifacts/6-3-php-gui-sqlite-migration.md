# Story 6.3: PHP GUI SQLite Migration

Status: done

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

- [x] Task 1 — PHP SQLite extension verification
- [x] Task 2 — Database helper class in PHP
- [x] Task 3 — Update investigation list controller
- [x] Task 4 — Update findings detail view
- [x] Task 5 — Add cross-case search endpoint

### Review Findings
- [x] [Review][Patch] CRITICAL: Duplicate Checker() code after `?>` closing tag (lines 625-803) would render as plain text — deleted 180 lines
- [x] [Review][Patch] $created_at unescaped in HTML — wrapped with htmlspecialchars()
- [x] [Review][Patch] XSS in Search.php onclick — added ENT_QUOTES to htmlspecialchars()
- [x] [Review][Patch] Missing $stmt->close() in Sqlite_Helper — added after finalize()

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
### Agent Model Used: Claude Sonnet 4.6 (Thinking)
### Completion Notes List
- Task 1+2: `GUI/Actions/Sqlite_Helper.php` — static class with `isAvailable()`, `getConnection()`, `query()`, `queryOne()`. Uses `SQLite3::OPEN_READONLY`, `busyTimeout(2000)`, prepared statements with positional `?` params.
- AC2: `getInvestigations(subject)` queries investigations table newest-first
- AC3: `getFindings(inv_id, status_filter)` queries findings filtered by investigation_id and optional status
- AC4: `searchInvestigations(query)` + `searchFindings(site_fragment)` for cross-case search via `GUI/Database/Search.php`
- AC5: `isAvailable()` checks `extension_loaded('sqlite3') && file_exists(DB_PATH)` — all paths fall back to flat files when false
- DB path: `GUI/Reports/mrholmes.db` (opened READONLY from GUI side)
- `GUI/Actions/Usernames_Finder.php`: Added `Checker_SQLite()` using SQLite path; `Checker()` now tries SQLite first with fallback
- 463 Python tests pass — no regressions
- PHP CLI not installed on dev machine; syntax reviewed statically
### File List
- GUI/Actions/Sqlite_Helper.php (NEW)
- GUI/Database/Search.php (NEW)
- GUI/Actions/Usernames_Finder.php (MODIFIED: Checker_SQLite + SQLite-first Checker)
