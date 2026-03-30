# Story 7.2: HaveIBeenPwned Integration

Status: done

## Story

As a user,
I want to check email addresses against HaveIBeenPwned database,
so that data breach exposure được phát hiện trong OSINT investigation.

## Acceptance Criteria

1. **AC1:** `HIBPPlugin` implements `IntelligencePlugin`
2. **AC2:** API v3 integration — requires API key ($3.50/month)
3. **AC3:** Returns: breach count, breach names, breach dates, data classes exposed
4. **AC4:** Rate limit respect: 1 request per 1.5 seconds (HIBP requirement)
5. **AC5:** Graceful handling when no API key configured

## Tasks / Subtasks

- [x] Task 1 — Implement `HIBPPlugin` class
- [x] Task 2 — HIBP API v3 client (with rate limiting)
- [x] Task 3 — Parse breach results into PluginResult
- [x] Task 4 — Unit tests with mocked API responses

## Dev Notes

### HIBP API
- Endpoint: `https://haveibeenpwned.com/api/v3/breachedaccount/{email}`
- Header: `hibp-api-key: {key}`
- Rate limit: 1 req / 1500ms

### Dependencies
- **REQUIRES Story 7.1** — Plugin Interface

### File Structure
```
Core/plugins/
└── hibp.py  # NEW — HIBPPlugin
```

## Dev Agent Record
### Agent Model Used
Gemini 1.5 Pro

### Completion Notes List
- Bmad Dev Agent successfully implemented `HIBPPlugin` complying with the OSINT platform `IntelligencePlugin` pattern.
- Robust, global async rate limitation handling constructed using `asyncio.Lock()` enforcing the required API v3 1500ms delay.
- Exhaustive API mocking and exception trapping covering endpoints states: 404, 401, 429, general networking drops.
- Test coverage hits all structural constraints. Full suite regression 100% green (523 tests).

### File List
- `Core/plugins/hibp.py`
- `tests/plugins/test_hibp.py`

### Review Findings
- [x] [Review][Patch] Lock is held during network request, creating bottleneck. Move `ClientSession` out of `async with lock:` [Core/plugins/hibp.py:75]
- [x] [Review][Defer] ClientSession created per request instead of pooling. Minor performance hit, acceptable for now without global session changes. — deferred, architectural
