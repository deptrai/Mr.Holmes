# Story 4.2: Secrets Migration → `.env` + `python-dotenv`

Status: ready-for-dev

## Story

As a developer,
I want to migrate secrets từ `Configuration.ini` sang `.env` file + `python-dotenv`,
so that credentials không bao giờ bị commit vào git (NFR6: zero plaintext secrets).

## Acceptance Criteria

1. **AC1:** `.env` file cho secrets: SMTP password, email, API keys
2. **AC2:** `.env.example` template (no real values)
3. **AC3:** `.gitignore` includes `.env`
4. **AC4:** `python-dotenv` loads env vars at startup
5. **AC5:** `Configuration.ini` giữ lại cho non-secret settings (display mode, date format)
6. **AC6:** Config module `Core/config/settings.py` — centralized access

## Tasks / Subtasks

- [ ] Task 1 — Audit `Configuration.ini` for secrets
- [ ] Task 2 — Create `.env.example` template
- [ ] Task 3 — Create `Core/config/settings.py` — Settings class
- [ ] Task 4 — Migrate secret access points
- [ ] Task 5 — Update `.gitignore`
- [ ] Task 6 — Unit tests

## Dev Notes

### Current Secrets in `Configuration.ini`
- Email recipient, password, SMTP settings
- Any API keys added in future (Shodan, HIBP)

### Dependencies
- **REQUIRES Story 2.6** — python-dotenv in requirements

### File Structure
```
.env.example        # NEW
.env                # NEW (gitignored)
Core/config/
├── __init__.py     # NEW
└── settings.py     # NEW — Settings class
```

## Dev Agent Record
### Agent Model Used
### Completion Notes List
### File List
