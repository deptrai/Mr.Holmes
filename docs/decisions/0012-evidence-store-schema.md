# 0012 Evidence Store Schema

Date: 2026-06-26

## Status

Accepted

## Context

Mr.Holmes currently stores investigation results in SQLite via
`Core/reporting/database.py` (a thread-safe singleton) using the schema in
`Core/reporting/schema.sql`. The existing schema has three tables:

- `investigations` — one row per investigation (subject, subject_type,
  created_at, proxy_used, total_sites, total_found)
- `findings` — one row per site checked (investigation_id, site_name, url,
  status, raw_response, created_at)
- `tags` / `finding_tags` — many-to-many tagging for findings

This schema was designed for the legacy batch model: run all plugins on a
target, store one finding per site. It does not support the iterative,
AI-driven investigation model where Claude Code:

1. Calls tools one at a time, in adaptive order.
2. Needs to query past results ("what did we find for this email so
   far?").
3. Forms and tracks hypotheses ("this username likely belongs to the same
   person as this email").
4. Resumes interrupted investigations without re-running tools.
5. Maintains an audit trail of every tool call (which tool, when, with
   what input, success/failure).

The `findings` table is too coarse — it assumes one row per site, but a
single tool call may produce data about multiple entities (e.g., Maigret
finds profiles on 50 sites). There is no concept of evidence provenance
(which tool produced this data), no hypothesis tracking, and no audit log.

Additionally, `Core/cache/plugin_cache.py` provides a separate SQLite
cache for plugin results (TTL 24h), but this is a performance cache, not
an investigation store — it cannot be queried by investigation ID and
does not persist beyond TTL expiry.

## Decision

Extend the existing SQLite schema (`Core/reporting/schema.sql`) with three
new tables, using `CREATE TABLE IF NOT EXISTS` (safe to run repeatedly,
consistent with existing `Database.ensure_schema()` migration approach).

### New tables

**`evidence`** — one row per tool call result:
- `id`, `investigation_id` (FK), `tool_name`, `target`, `target_type`,
  `result_data` (JSON blob), `confidence`, `source_url`, `collected_at`,
  `collected_by` (orchestrator id, default 'claude-code')

**`hypotheses`** — AI-generated investigation hypotheses:
- `id`, `investigation_id` (FK), `statement`, `status`
  (unverified/confirmed/refuted/inconclusive), `confidence`,
  `evidence_ids` (JSON array), `created_at`, `updated_at`

**`audit_log`** — every tool call for traceability:
- `id`, `investigation_id` (FK, nullable), `tool_name`, `input_hash`
  (SHA-256 of input, not raw input — privacy), `success`, `duration_ms`,
  `proxy_used`, `called_at`

### Design principles

1. **Reuse existing infrastructure** — same `Database` singleton, same
   SQLite file (`GUI/Reports/mrholmes.db`), same WAL mode, same
   `ensure_schema()` migration. No new database engine.

2. **JSON blobs for flexible data** — `result_data` stores the full
   `PluginResult.data` dict as JSON. This accommodates the heterogenous
   output of different plugins without requiring a rigid column per
   field. SQLite's JSON functions (`json_extract`) enable querying
   inside blobs when needed.

3. **Provenance tracking** — every evidence row records `tool_name` and
   `collected_by`, so we always know which tool (and which orchestrator)
   produced a finding.

4. **Privacy-conscious audit** — `audit_log` stores `input_hash` (SHA-256)
   not raw input, so the audit trail records that a tool was called with
   some input without retaining the actual target value. This aligns with
   the privacy approach in ADR-0008 (proxy audit trail stores proxy hash,
   not raw IP).

5. **Resume support** — Claude Code can call `get_investigation(id)` to
   load all evidence + hypotheses for an investigation, then continue
   from where it left off. No need to re-run tools.

6. **Separation from cache** — `PluginCache` (TTL 24h) remains for
   performance. `evidence` table is permanent (user-controlled delete).
   Cache prevents redundant API calls within a session; evidence store
   preserves investigation history across sessions.

## Alternatives Considered

1. **PostgreSQL** — More powerful (better JSON indexing, full-text search),
   but adds infrastructure requirements (server, auth, connection pool).
   Mr.Holmes is a single-user tool — SQLite is sufficient and zero-config.

2. **DuckDB** — Excellent for analytical queries on JSON data, but less
   mature ecosystem for Python async and adds a new dependency. SQLite
   with JSON functions is adequate for our query patterns.

3. **Separate evidence database (new .db file)** — Considered to avoid
   schema coupling with the legacy `findings` table. Rejected because
   `evidence` references `investigations.id` (FK), and splitting across
   databases prevents foreign key enforcement. One database is simpler.

4. **Store evidence as JSON files on disk** — Simple, but no queryability.
   Claude Code would need to load all files to query. SQLite is a better
   fit for structured querying.

5. **Use the existing `findings` table with new columns** — The `findings`
   table assumes one row per site, with site-specific columns
   (`site_name`, `is_scrapable`, `scraped`). Evidence is more general
   (one row per tool call, arbitrary result data). Overloading `findings`
   would require nullable columns and break existing queries.

## Consequences

Positive:

- Queryable investigation history — Claude Code can ask "what evidence do
  we have for this email?" via `query_evidence` MCP tool.
- Resume capability — interrupted investigations can be continued without
  re-running tools.
- Hypothesis tracking — Claude Code's reasoning is persisted and
  auditable, not lost when the conversation ends.
- Audit trail — every tool call is logged with timestamp, duration, and
  success status (extends ADR-0008's proxy audit to all tool calls).
- No new infrastructure — same SQLite, same `Database` singleton, same
  migration approach.
- Backward compatible — existing `investigations`, `findings`, `tags`
  tables are untouched. New tables are additive.

Tradeoffs:

- JSON blobs are less queryable than normalized columns. Complex queries
  require `json_extract()` which is slower than column access. Acceptable
  given our query volume (single-user, dozens of evidence rows per
  investigation, not millions).
- No full-text search on evidence content. Could add SQLite FTS5 virtual
  table later if needed.
- Schema migration is additive only — no `ALTER TABLE` on existing tables.
  If we later need to change `findings` schema, a separate migration
  strategy is needed.
- `input_hash` in audit_log means we can prove a tool was called but
  cannot recover the exact input from the audit trail alone (by design —
  privacy). The `evidence` table does store the raw `target` for
  investigation purposes.

## Follow-Up

- Add the three new tables to `Core/reporting/schema.sql`.
- Implement evidence store MCP tools: `create_investigation`,
  `save_evidence`, `query_evidence`, `get_investigation`,
  `create_hypothesis`, `update_hypothesis`.
- Auto-save evidence when `investigation_id` is passed to any OSINT tool.
- Add audit logging to the MCP tool wrapper layer (every tool call →
  `audit_log` row).
- Configure retention policy: audit_log 90 days (env
  `MH_AUDIT_RETENTION_DAYS`), evidence permanent (user delete only).
- Add `consent_accepted` column to `investigations` table for ethics
  tracking (see architecture.md §8.1).
