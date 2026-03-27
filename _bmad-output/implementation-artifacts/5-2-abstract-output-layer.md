# Story 5.2: Abstract Output Layer

Status: done

## Story

As a developer,
I want to tách presentation logic (print/colors) khỏi business logic (scan/detect),
so that output có thể switch giữa CLI, Rich, JSON, hoặc silent mode.

## Acceptance Criteria

1. **AC1:** `OutputHandler` Protocol tại `Core/cli/output.py`
2. **AC2:** Methods: `found()`, `not_found()`, `error()`, `progress()`, `summary()`
3. **AC3:** `ConsoleOutput` — current print-based output (backward compat)
4. **AC4:** `SilentOutput` — no output (batch/scripting)
5. **AC5:** ScanPipeline accepts OutputHandler — decoupled từ print()

## Tasks / Subtasks

- [x] Task 1 — Define `OutputHandler` Protocol
- [x] Task 2 — Implement `ConsoleOutput` (wraps current print logic)
- [x] Task 3 — Implement `SilentOutput` (no-op)
- [x] Task 4 — Inject OutputHandler into ScanPipeline
- [x] Task 5 — Unit tests

## Dev Notes

### Dependencies
- **REQUIRES Story 1.3** — ScanPipeline
- **REQUIRED BY Story 5.3** — Rich output implements Protocol

### File Structure
```
Core/cli/
└── output.py  # NEW — OutputHandler Protocol + implementations
```

## Dev Agent Record
### Agent Model Used: Claude Sonnet
### Completion Notes List
- `Core/cli/output.py`: `OutputHandler` runtime_checkable Protocol — 5 methods (found, not_found, error, progress, summary). `ConsoleOutput` lazy-imports Font for ANSI colors, falls back to plain text. `SilentOutput` no-op, routes errors to logger.debug only.
- `Core/engine/scan_pipeline.py`: Added `output_handler` kwarg to `__init__()` (defaults ConsoleOutput). `handle_results()` calls `self.output.found()` per URL and `self.output.summary()` at end.
- `Core/cli/runner.py`: `BatchRunner._run_username_scan()` passes `SilentOutput()` so pipeline doesn’t print per-URL noise; runner’s own `_emit_output()` owns final formatting.
- `tests/cli/test_output.py`: 34 tests — all ACs covered. Full suite: 408/408 passing.
### File List
- Core/cli/output.py (NEW)
- Core/cli/__init__.py (MODIFY)
- Core/engine/scan_pipeline.py (MODIFY)
- Core/cli/runner.py (MODIFY)
- tests/cli/test_output.py (NEW)
