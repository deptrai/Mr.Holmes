# Story 5.1: Argparse CLI Interface

Status: ready-for-dev

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

- [ ] Task 1 — Create `Core/cli/parser.py` — argparse definition
- [ ] Task 2 — Create `Core/cli/runner.py` — batch execution logic
- [ ] Task 3 — Modify `MrHolmes.py` entry point
  - [ ] If args provided → batch mode
  - [ ] If no args → interactive mode (current)
- [ ] Task 4 — Integration tests

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
### Agent Model Used
### Completion Notes List
### File List
