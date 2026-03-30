# Story 5.1: Argparse CLI Interface

Status: done

## Story

As a user,
I want to chạy Mr.Holmes non-interactive qua command-line arguments,
so that scans có thể automated / scripted / chạy trong CI.

## Acceptance Criteria

1. **AC1:** `python3 MrHolmes.py --username <name>` — scan without interactive prompts
2. **AC2:** Flags: `--username`, `--phone`, `--email`, `--website`, `--proxy`, `--nsfw`, `--output`
3. **AC3:** Backward compatible — no args → interactive mode (current behavior)
4. **AC4:** `--help` shows usage
5. **AC5:** `--output json|txt|csv` — format selection

## Tasks / Subtasks

- [x] Task 1 — Create `Core/cli/parser.py` — argparse definition
- [x] Task 2 — Create `Core/cli/runner.py` — batch execution logic
- [x] Task 3 — Modify `MrHolmes.py` entry point
  - [x] If args provided → batch mode
  - [x] If no args → interactive mode (current)
- [x] Task 4 — Integration tests

## Dev Notes

### CLI Design
```bash
# Batch mode:
python3 MrHolmes.py --username johndoe --proxy --nsfw --output json

# Interactive mode (unchanged):
python3 MrHolmes.py
```

### Dependencies
- **REQUIRES Story 1.3** — ScanPipeline (batch mode calls pipeline directly)
- **BENEFITS FROM Story 4.3** — logging for batch output

### File Structure
```
Core/cli/
├── __init__.py   # NEW
├── parser.py     # NEW — argparse
└── runner.py     # NEW — batch execution
MrHolmes.py       # MODIFY — add arg detection
```

## Dev Agent Record
### Agent Model Used: Claude Sonnet
### Completion Notes List
- Created `Core/cli/parser.py` — `build_parser()` and `parse_args()` via argparse; mutually exclusive scan target group; `--proxy`, `--nsfw`, `--output json|txt|csv`
- Created `Core/cli/runner.py` — `BatchRunner` dispatches to ScanPipeline (username) or legacy modules (phone/email/website); `ScanResult` output container; json/txt/csv formatting
- Modified `MrHolmes.py` — arg parsing before interactive mode; `has_batch_target()` gate; `SystemExit` instead of bare `exit()`
- 45 new tests in `tests/cli/test_parser.py` and `tests/cli/test_runner.py`; 374/374 total passing
### File List
- Core/cli/__init__.py (NEW)
- Core/cli/parser.py (NEW)
- Core/cli/runner.py (NEW)
- MrHolmes.py (MODIFY)
- tests/cli/__init__.py (NEW)
- tests/cli/test_parser.py (NEW)
- tests/cli/test_runner.py (NEW)
