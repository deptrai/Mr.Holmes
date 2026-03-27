# Story 5.2: Abstract Output Layer

Status: ready-for-dev

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

- [ ] Task 1 — Define `OutputHandler` Protocol
- [ ] Task 2 — Implement `ConsoleOutput` (wraps current print logic)
- [ ] Task 3 — Implement `SilentOutput` (no-op)
- [ ] Task 4 — Inject OutputHandler into ScanPipeline
- [ ] Task 5 — Unit tests

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
### Agent Model Used
### Completion Notes List
### File List
