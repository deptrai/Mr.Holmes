# Story 4.2: Secrets Migration → `.env` + `python-dotenv`

Status: done

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

- [x] Task 1 — Audit `Configuration.ini` for secrets
- [x] Task 2 — Create `.env.example` template
- [x] Task 3 — Create `Core/config/settings.py` — Settings class
- [x] Task 4 — Migrate secret access points
- [x] Task 5 — Update `.gitignore`
- [x] Task 6 — Unit tests

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
Gemini 2.5 Pro
### Completion Notes List
- Audit: [Smtp] (email/password/destination/server/port/status) và [Settings].api_key là secrets.
- `.gitignore` đã có `.env` từ trước (AC3 ✅).
- Tạo `.env.example` với tất cả secret vars (AC2).
- Tạo `.env` local (gitignored) với các giá trị mặc định an toàn (AC1).
- Tạo `Core/config/settings.py`: Settings class, secrets từ env vars, non-secrets từ .ini (AC4, AC5, AC6).
- Fail-soft: hoạt động khi python-dotenv chưa install (import try/except).
- 17 tests mới, 310 tổng tests PASS.
### File List
- `[NEW] .env.example` — secret env template
- `[NEW] .env` — local secrets (gitignored)
- `[NEW] Core/config/__init__.py` — package init
- `[NEW] Core/config/settings.py` — Settings class + singleton
- `[NEW] tests/config/__init__.py`
- `[NEW] tests/config/test_settings.py` — 17 unit tests
