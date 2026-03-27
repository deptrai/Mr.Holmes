# Story 4.5: GitHub Actions CI

Status: review

## Story

As a developer,
I want to setup GitHub Actions CI pipeline auto-run tests on every PR,
so that regressions được phát hiện tự động trước khi merge.

## Acceptance Criteria

1. **AC1:** `.github/workflows/ci.yml` — trigger on push/PR to main
2. **AC2:** Matrix: Python 3.9, 3.10, 3.11
3. **AC3:** Steps: install deps → lint → test → coverage report
4. **AC4:** Fail PR nếu tests fail
5. **AC5:** Coverage badge optional

## Tasks / Subtasks

- [ ] Task 1 — Create `.github/workflows/ci.yml`
- [ ] Task 2 — Configure matrix strategy
- [ ] Task 3 — Add lint step (flake8 hoặc ruff)
- [ ] Task 4 — Test + coverage step
- [ ] Task 5 — Verify with test PR

## Dev Notes

### Dependencies
- **REQUIRES Story 4.1** — pytest framework
- **REQUIRES Story 2.6** — requirements files

### File Structure
```
.github/
└── workflows/
    └── ci.yml  # NEW
```

## Dev Agent Record
### Agent Model Used
### Completion Notes List
### File List
