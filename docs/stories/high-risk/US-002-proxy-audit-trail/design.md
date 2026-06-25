# Design

## Domain Model

- `AuditEntry` — value object: timestamp, target_host, proxy_hash, status_code,
  duration_ms, source_module.
- `ProxyHasher` — utility: SHA-256 hash of proxy address, truncated to 16 hex
  chars. Never stores raw IP.
- `RetentionPolicy` — value object: max_age_days (default 30). Computes
  purge cutoff timestamp.

## Application Flow

1. Caller (e.g. `Requests_Search`) completes a proxied request.
2. Caller invokes `Proxy_Audit.log(target_url, proxy_addr, status_code,
   duration_ms, source_module)`.
3. `Proxy_Audit` hashes the proxy address, truncates the target URL to host,
   inserts an `AuditEntry` into SQLite.
4. On every `log()` call, `Proxy_Audit` runs retention purge if
  `max_age_days` has elapsed since last purge (lazy purge, not background
  thread).

## Interface Contract

```python
class Proxy_Audit:
    @staticmethod
    def log(target_url: str, proxy_addr: str, status_code: int,
            duration_ms: int, source_module: str) -> int:
        """Insert audit entry. Returns entry id. Raises on DB error."""

    @staticmethod
    def query(limit: int = 100, source_module: str | None = None) -> list[dict]:
        """Query recent audit entries. Returns list of dicts."""

    @staticmethod
    def purge(max_age_days: int = 30) -> int:
        """Delete entries older than max_age_days. Returns count deleted."""

    @staticmethod
    def count() -> int:
        """Return total entry count."""
```

Errors:
- `ValueError` — invalid input (negative duration, empty target_url).
- `sqlite3.Error` — database operation failure (propagated to caller).

## Data Model

Table `proxy_audit_entries`:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PK AUTOINCREMENT | |
| `timestamp` | TEXT | SQLite `datetime('now')` |
| `target_host` | TEXT | URL host only, max 255 chars |
| `proxy_hash` | TEXT | SHA-256 truncated to 16 hex chars |
| `status_code` | INTEGER | HTTP status or 0 for connection failure |
| `duration_ms` | INTEGER | Non-negative |
| `source_module` | TEXT | Module name, max 100 chars |

Index on `timestamp` for retention purge performance.

Retention: `DELETE FROM proxy_audit_entries WHERE timestamp < ?` where `?` is
the cutoff datetime. Lazy purge runs at most once per session (tracked via
in-memory `_last_purge_at`).

## UI / Platform Impact

- No UI changes. Programmatic API only.
- `proxy_audit.db` is created at repo root, added to `.gitignore`.
- No deployment impact — audit is local-only.

## Observability

- The audit database itself IS the observability layer for proxy usage.
- `Proxy_Audit.query()` provides programmatic access for investigation.
- `Proxy_Audit.count()` for quick health check.
- Errors in audit logging should not crash the caller's request flow —
  callers should wrap `log()` in try/except if audit failure must not
  interrupt OSINT work.

## Alternatives Considered

1. **Automatic interception in Proxies.py** — rejected: too invasive, changes
   existing behavior of all OSINT agents, hard to test in isolation. Opt-in
   `log()` calls are safer and more explicit.

2. **JSON file instead of SQLite** — rejected: no query performance, no
   retention purge efficiency, grows unboundedly. SQLite is already used by
   `PluginCache` in the same project.

3. **Store raw proxy IPs** — rejected: security risk. Hashed form is
   sufficient for correlation ("same proxy used for these requests") without
   exposing the actual proxy address if the audit DB is leaked.

4. **Background thread for purge** — rejected: adds concurrency complexity.
   Lazy purge on `log()` is simpler and sufficient for the expected volume
   (OSINT investigations are not high-throughput).
