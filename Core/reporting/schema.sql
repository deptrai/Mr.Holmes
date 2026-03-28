-- Core/reporting/schema.sql
-- Mr.Holmes OSINT Database Schema
-- Story 6.1 — Normalized SQLite schema (3NF)
-- Supports: dual-write alongside text reports, PHP GUI, cross-case querying

-- AC2, AC3: investigations table
CREATE TABLE IF NOT EXISTS investigations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    subject         TEXT    NOT NULL,
    subject_type    TEXT    NOT NULL CHECK(subject_type IN ('USERNAME','PHONE','EMAIL','WEBSITE','PERSON')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    proxy_used      BOOLEAN DEFAULT FALSE,
    total_sites     INTEGER,
    total_found     INTEGER
);

-- AC2, AC4: findings table — one row per site checked
CREATE TABLE IF NOT EXISTS findings (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    investigation_id  INTEGER NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    site_name         TEXT    NOT NULL,
    url               TEXT,
    -- F7: NULL status = scan in-progress / result pending
    status            TEXT    CHECK(status IN ('found','not_found','blocked','rate_limited','captcha','error','timeout')),
    is_scrapable      BOOLEAN DEFAULT FALSE,
    scraped           BOOLEAN DEFAULT FALSE,
    raw_response      TEXT,
    error_type        TEXT,
    -- F1: Temporal ordering of individual findings within an investigation
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- AC2: tags lookup table (normalized)
CREATE TABLE IF NOT EXISTS tags (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT UNIQUE NOT NULL
);

-- AC2: many-to-many bridge: findings ↔ tags
CREATE TABLE IF NOT EXISTS finding_tags (
    finding_id  INTEGER NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
    tag_id      INTEGER NOT NULL REFERENCES tags(id)    ON DELETE CASCADE,
    PRIMARY KEY (finding_id, tag_id)
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_findings_investigation ON findings(investigation_id);
CREATE INDEX IF NOT EXISTS idx_findings_status        ON findings(status);
CREATE INDEX IF NOT EXISTS idx_investigations_subject ON investigations(subject);
