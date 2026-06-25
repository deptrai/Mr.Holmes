# Exec Plan

## Goal

Provide a local, persistent, anonymized audit trail for proxy-assisted HTTP
requests in Mr.Holmes, with automatic retention purge.

## Scope

In scope:

- `Core/Support/Proxy_Audit.py` — new module with `log`, `query`, `purge`,
  `count` static methods.
- `tests/support/test_proxy_audit.py` — unit + integration tests.
- `docs/decisions/0008-proxy-audit-trail.md` — ADR.
- `.gitignore` — add `proxy_audit.db` entry.
- Durable story + decision records in harness.db.

Out of scope:

- Modifying `Core/Support/Proxies.py` to auto-log.
- GUI for audit data visualization.
- Encrypting the audit database at rest.
- Exporting audit data to external SIEM/compliance systems.

## Risk Classification

Risk flags:

- Audit/security — logs proxy usage patterns, target hosts. Sensitive metadata.
- Data model — new SQLite schema, retention deletion.
- External systems — proxy infrastructure, ip-api.com context.
- Existing behavior — new audit layer conceptually touches proxy flow.

Hard gates:

- Audit/security — must not store raw proxy IPs or full target URLs.
- Data loss — retention purge deletes records; must be bounded and explicit.

## Work Phases

1. **Discovery** — read existing `Proxies.py`, `PluginCache` patterns, test
   conventions. ✅ Done during intake.
2. **Design** — write `design.md` with domain model, interface contract, data
   model, alternatives. ✅ Done.
3. **Validation planning** — write `validation.md` with test plan and
   acceptance criteria. ✅ Done.
4. **Implementation** — write `Proxy_Audit.py` with schema init, log, query,
   purge, count.
5. **Verification** — write tests, run `story verify`, fix red/green cycle.
6. **Harness update** — record ADR, durable decision, trace, audit.

## Stop Conditions

Pause for human confirmation if:

- Product behavior is ambiguous — e.g. whether to hash or encrypt proxy IPs.
- Data migration or deletion risk appears — e.g. if purge logic could delete
  unintended rows.
- Validation requirements need to be weakened.
- Architecture direction changes — e.g. switching from SQLite to JSON.

Current status: no stop conditions triggered. Design decisions are clear:
hash (not encrypt), SQLite (not JSON), opt-in log (not auto-intercept).
