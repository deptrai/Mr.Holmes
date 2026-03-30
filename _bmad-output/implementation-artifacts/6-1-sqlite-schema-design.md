# Story 6.1: SQLite Schema Design

Status: done

## Story

As a developer,
I want to design normalized SQLite schema cho OSINT findings,
so that results có thể lưu trữ, query cross-case, và serve cho PHP GUI.

## Acceptance Criteria

1. **AC1:** Schema file `Core/reporting/schema.sql`
2. **AC2:** Tables: `investigations`, `findings`, `tags`, `finding_tags` (normalized)
3. **AC3:** `investigations`: id, subject, subject_type, created_at, proxy_used
4. **AC4:** `findings`: id, investigation_id, site_name, url, status, error_type, raw_response
5. **AC5:** Schema migration script — create tables if not exist
6. **AC6:** Database singleton `Core/reporting/database.py`

## Tasks / Subtasks

- [ ] Task 1 — Design schema (normalized 3NF)
- [ ] Task 2 — Create `schema.sql`
- [ ] Task 3 — Implement `Database` class (sqlite3 connection management)
- [ ] Task 4 — Migration method: `ensure_schema()`
- [ ] Task 5 — Unit tests — create/drop/query

## Dev Notes

### Schema Design
```sql
CREATE TABLE investigations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    subject_type TEXT NOT NULL CHECK(subject_type IN ('USERNAME','PHONE','EMAIL','WEBSITE','PERSON')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    proxy_used BOOLEAN DEFAULT FALSE,
    total_sites INTEGER,
    total_found INTEGER
);

CREATE TABLE findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id INTEGER REFERENCES investigations(id),
    site_name TEXT NOT NULL,
    url TEXT,
    status TEXT CHECK(status IN ('found','not_found','blocked','rate_limited','captcha','error','timeout')),
    is_scrapable BOOLEAN DEFAULT FALSE,
    scraped BOOLEAN DEFAULT FALSE
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE finding_tags (
    finding_id INTEGER REFERENCES findings(id),
    tag_id INTEGER REFERENCES tags(id),
    PRIMARY KEY (finding_id, tag_id)
);
```

### Dependencies
- Independent — CAN start anytime
- **REQUIRED BY Story 6.2** — ReportWriter uses schema

### Architecture Compliance
- [Source: `architecture.md`#Decision 6] Normalized SQLite, dual-write

### File Structure
```
Core/reporting/
├── __init__.py    # NEW
├── schema.sql     # NEW
└── database.py    # NEW — Database singleton
```

## Dev Agent Record
### Agent Model Used: Claude Sonnet 4.6 (Thinking)
### Completion Notes List
- Schema created in Core/reporting/schema.sql (normalized 3NF, all 4 tables)
- Database singleton in Core/reporting/database.py with WAL mode, FK enforcement, context-manager
- ensure_schema() is idempotent (CREATE TABLE IF NOT EXISTS)
- 17 unit tests across: schema creation, migration, singleton, data integrity, FK cascades
- Config path resolved to absolute — immune to CWD changes
### File List
- Core/reporting/__init__.py (NEW)
- Core/reporting/schema.sql (NEW)
- Core/reporting/database.py (NEW)
- tests/reporting/__init__.py (NEW)
- tests/reporting/test_database.py (NEW)
