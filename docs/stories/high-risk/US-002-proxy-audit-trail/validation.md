# Validation

## Proof Strategy

All acceptance criteria must be verified by passing unit tests. Integration
tests verify SQLite schema creation and retention purge against a temporary
database. No E2E or platform tests needed — module is a library, not a CLI
or GUI surface.

## Test Plan

| Layer | Cases |
| --- | --- |
| Unit | `log()` inserts entry with correct fields; `log()` hashes proxy address; `log()` truncates URL to host; `log()` raises ValueError on negative duration; `log()` raises ValueError on empty target_url; `query()` returns entries in reverse chronological order; `query()` filters by source_module; `count()` returns correct count |
| Integration | Schema creation on first call; `purge()` deletes entries older than cutoff; `purge()` returns count deleted; `purge()` leaves recent entries intact; lazy purge runs at most once per session |
| E2E | n/a — library module |
| Platform | n/a — local SQLite only |
| Performance | n/a — OSINT volume is low |
| Logs/Audit | The audit DB itself is the audit artifact; `query()` and `count()` serve as self-verification |

## Fixtures

- Temporary SQLite database via `tmp_path` pytest fixture (unique per test).
- Mock proxy addresses: `203.0.113.1:8080`, `198.51.100.5:3128`.
- Mock target URLs: `https://example.com/path/to/page`, `http://test.invalid`.

## Commands

```text
python3.10 -m pytest tests/support/test_proxy_audit.py -v
```

## Acceptance Evidence

To be filled after `story verify US-002` passes.
