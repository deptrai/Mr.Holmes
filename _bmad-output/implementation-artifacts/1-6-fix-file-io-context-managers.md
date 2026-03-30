# Story 1.6: Fix File I/O → Context Managers

Status: done

## Story

As a developer,
I want to thay thế tất cả unsafe `f = open()` / `f.close()` patterns bằng `with open()` context managers,
so that file handles luôn được đóng đúng cách ngay cả khi exception xảy ra.

## Acceptance Criteria

1. **AC1:** Tất cả `f = open()` ... `f.close()` → `with open() as f:`
2. **AC2:** Tất cả `f = open()` WITHOUT close → wrapped in `with`
3. **AC3:** Files affected: `Requests_Search.py`, `Searcher.py`, và any other files dùng pattern này
4. **AC4:** No file handles leaked — verify bằng grep cho `= open(` without `with`
5. **AC5:** Behavior KHÔNG đổi

## Tasks / Subtasks

- [ ] Task 1 — Audit all `open()` calls across codebase
  - [ ] Grep `= open(` across `Core/` directory
  - [ ] Identify: already safe (with), unsafe (no close), unsafe (manual close)

- [ ] Task 2 — Fix `Requests_Search.py`
  - [ ] Line 26: `f = open(report, "a")` — NO close() in scope → wrap in `with`
  - [ ] Lines 124-138: Multiple `open()` calls → wrap each in `with`

- [ ] Task 3 — Fix `Searcher.py`
  - [ ] Line 276: `f = open(report, "a")` → `with open()`
  - [ ] Line 101: `f = open(nomefile,)` → `with open()`

- [ ] Task 4 — Fix any other files found in audit

- [ ] Task 5 — Verification grep
  - [ ] `grep -rn "= open(" Core/` → 0 results without `with`

## Dev Notes

### Known Unsafe Patterns

**`Requests_Search.py` line 26:**
```python
f = open(report, "a")          # OPENED here
# ... 100+ lines of logic ...
# f.close() NOT CALLED in any branch!
```
→ File handle leaked on EVERY call.

**`Requests_Search.py` lines 124-138:**
```python
d = open(json_file2, "w")
d.write('''{ "Names":[] }''')
d.close()                       # Manual close — risky if write() throws

f = open(json_file, "w")
f.write('''{ "List":[] }''')
f.close()                       # Same risk
```

**`Searcher.py` line 101:**
```python
f = open(nomefile,)            # JSON site list opened
data = json.loads(f.read())    # Read all
# f.close() NEVER CALLED
```

### Dependencies

- Independent — CAN run in parallel with any story
- No dataclass or architectural dependencies

### File Structure

```
Core/Support/
└── Requests_Search.py   # MODIFY
Core/
└── Searcher.py           # MODIFY
# + any other files found in audit
```

## Dev Agent Record

### Agent Model Used
### Completion Notes List
### File List
