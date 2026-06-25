# Overview

## Current Behavior

Mr.Holmes routes HTTP requests through proxies via `Core/Support/Proxies.py`.
Proxy identity is resolved through `ip-api.com`. There is no persistent record
of which proxy was used, when, for which target, or what the response status
was. If a proxy is compromised, misconfigured, or leaks the user's real IP,
there is no audit trail to investigate.

## Target Behavior

A new `Core/Support/Proxy_Audit.py` module records every proxy-assisted
request to a local SQLite database (`proxy_audit.db`) with:

- timestamp
- target URL (host only, path truncated)
- proxy address (anonymized hash, not raw IP)
- response status code
- request duration
- source module that initiated the request

A retention policy purges records older than a configurable number of days
(default 30). The audit database is `.gitignore`d and never transmitted off the
local machine.

## Affected Users

- OSINT investigators who need to verify proxy integrity post-investigation.
- Compliance reviewers who need an audit trail of proxy usage.

## Affected Product Docs

- `docs/decisions/0008-proxy-audit-trail.md` — ADR for audit trail design.
- `docs/stories/high-risk/US-002-proxy-audit-trail/` — this story packet.

## Non-Goals

- Modifying `Core/Support/Proxies.py` request flow — audit is opt-in via
  explicit `Proxy_Audit.log()` calls, not automatic interception.
- Transmitting audit data to any external service.
- Storing raw target URLs or raw proxy IPs — only hashed/anonymized forms.
- User-facing GUI for audit data — this is a programmatic API only.
