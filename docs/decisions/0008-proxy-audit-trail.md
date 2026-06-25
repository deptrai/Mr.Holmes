# 0008 Proxy Audit Trail

Date: 2026-06-26

## Status

Accepted

## Context

Mr.Holmes routes HTTP requests through proxies via `Core/Support/Proxies.py`
for anonymization during OSINT investigations. There is no persistent record
of which proxy was used, when, for which target, or what the response status
was. If a proxy is compromised, misconfigured, or leaks the user's real IP,
there is no audit trail to investigate after the fact.

This is an audit/security gap: proxy usage metadata is sensitive and should
be traceable for post-investigation review without exposing raw proxy
addresses or full target URLs.

## Decision

Add `Core/Support/Proxy_Audit.py` — a local SQLite audit trail that records
proxy-assisted requests with:

- Timestamp
- Target host (URL truncated to host, no path)
- Proxy address hash (SHA-256 truncated to 16 hex chars — never raw IP)
- HTTP status code
- Request duration in milliseconds
- Source module name

Retention policy: entries older than 30 days (configurable) are purged
lazily on the next `log()` call.

The audit is opt-in: callers must explicitly call `Proxy_Audit.log()`. No
automatic interception of `Proxies.py` request flow.

The audit database (`proxy_audit.db`) is local-only, `.gitignore`d, and
never transmitted off the machine.

## Alternatives Considered

1. **Automatic interception in Proxies.py** — rejected: too invasive, changes
   existing behavior of all OSINT agents, hard to test in isolation.

2. **JSON file instead of SQLite** — rejected: no query performance, no
   retention purge efficiency, grows unboundedly. SQLite is already used by
   `PluginCache` in the same project.

3. **Store raw proxy IPs** — rejected: security risk. Hashed form is
   sufficient for correlation without exposing actual proxy addresses if the
   audit DB is leaked.

4. **Background thread for purge** — rejected: adds concurrency complexity.
   Lazy purge on `log()` is simpler and sufficient for expected volume.

## Consequences

Positive:

- Post-investigation audit trail for proxy usage.
- Anonymized form protects proxy addresses if audit DB is leaked.
- Opt-in design means no risk to existing request flow.
- Reuses SQLite pattern already established by `PluginCache`.

Tradeoffs:

- Callers must explicitly call `log()` — audit coverage depends on caller
  adoption.
- Hashed proxy addresses cannot be reversed to identify the actual proxy
  without re-hashing known addresses.
- Lazy purge means the first `log()` call after the retention period may be
  slightly slower.

## Follow-Up

- Integrate `Proxy_Audit.log()` calls into `Requests_Search` in a future
  story.
- Consider adding a CLI command to query/export audit data.
- Consider encryption at rest if audit DB contains highly sensitive metadata.
