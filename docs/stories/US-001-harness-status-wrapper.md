# US-001 Harness Status Python Wrapper

## Status

in-progress

## Lane

normal

## Product Contract

Provide a Python wrapper `Core/Support/Harness_Status.py` that calls the
`scripts/bin/harness-cli` binary and returns harness operational state
(stats, audit, matrix) as Python dicts so other Mr.Holmes modules can query
harness state without shelling out manually.

## Relevant Product Docs

- `docs/HARNESS.md` — durable layer contract and CLI command reference
- `docs/TOOL_REGISTRY.md` — tool registry query semantics
- `AGENTS.md` — Core/Support module conventions

## Acceptance Criteria

- `Harness_Status.stats()` returns a dict with keys `intakes`, `stories`,
  `decisions`, `backlog_items`, `traces`.
- `Harness_Status.audit()` returns a dict with `entropy_score` and drift
  category counts.
- `Harness_Status.matrix()` returns a list of story proof rows.
- Missing `harness-cli` binary raises `FileNotFoundError` with a clear message.
- CLI failures raise `RuntimeError` with stderr captured.
- Unit tests cover happy path, missing binary, and CLI failure.

## Design Notes

- Commands: wraps `scripts/bin/harness-cli query stats`, `audit`,
  `query matrix --numeric`.
- API: class `Harness_Status` with static methods, mirroring `Core.Support`
  pattern (e.g. `Logs`, `Recap`).
- Tables: reads from `harness.db` via CLI, never opens SQLite directly.
- Domain rules: CLI path resolved relative to repo root via `os.path.dirname`.
- UI surfaces: none — internal support module.

## Validation

When updating durable proof status, use numeric booleans:
`scripts/bin/harness-cli story update --id <id> --unit 1 --integration 1 --e2e 0 --platform 0`.

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/support/test_harness_status.py -v` |
| Integration | n/a (wrapper only) |
| E2E | n/a |
| Platform | n/a |
| Release | n/a |

## Harness Delta

- New story packet `docs/stories/US-001-harness-status-wrapper.md`.
- New module `Core/Support/Harness_Status.py`.
- New test file `tests/support/test_harness_status.py`.

## Evidence

- `scripts/bin/harness-cli story verify US-001` runs the verify command and
  records pass/fail in the durable layer.
