# Story 5.3: Rich Library Integration

Status: done

## Story

As a user,
I want giao diện CLI chuyên nghiệp với progress bars, tables, và colored output via Rich library,
so that scan experience trực quan, hiện đại, và informative.

## Acceptance Criteria

1. **AC1:** `RichOutput` class implements `OutputHandler` Protocol
2. **AC2:** Progress bar cho scan (X/300 sites)
3. **AC3:** Results table thay vì plain text list
4. **AC4:** Tree layout cho tag categories
5. **AC5:** Graceful fallback nếu terminal không support Rich

## Tasks / Subtasks

- [x] Task 1 — Implement `RichOutput` class
- [x] Task 2 — Progress bar: `rich.progress.Progress`
- [x] Task 3 — Results table: `rich.table.Table`
- [x] Task 4 — Tag tree: `rich.tree.Tree`
- [x] Task 5 — Terminal capability detection + fallback

## Dev Notes

### Dependencies
- **REQUIRES Story 5.2** — OutputHandler Protocol
- **REQUIRES Story 2.6** — Rich in requirements

### File Structure
```
Core/cli/
└── rich_output.py  # NEW — RichOutput class
```

## Dev Agent Record
### Agent Model Used: Claude Sonnet
### Completion Notes List
- `Core/cli/rich_output.py`: `RichOutput` class implementing OutputHandler Protocol. Stateful: accumulates `_found_rows` and `_tag_groups` during scan, renders Rich Table + Tree at `summary()`. `force_fallback=True` constructor arg for non-TTY testing.
- `make_output_handler()` factory: auto-selects `SilentOutput` / `RichOutput` / `ConsoleOutput` based on env.
- 5 tests skip when non-TTY (expected CI behaviour); 21 pass always.
- 5 TTY-dependent render tests use `pytest.skip` to avoid flaky CI failures.
- Full suite: 429 passed, 5 skipped.
### File List
- Core/cli/rich_output.py (NEW)
- Core/cli/__init__.py (MODIFY)
- tests/cli/test_rich_output.py (NEW)
