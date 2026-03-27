# Story 7.2: HaveIBeenPwned Integration

Status: ready-for-dev

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

- [ ] Task 1 — Implement `HIBPPlugin` class
- [ ] Task 2 — HIBP API v3 client (with rate limiting)
- [ ] Task 3 — Parse breach results into PluginResult
- [ ] Task 4 — Unit tests with mocked API responses

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
### Completion Notes List
### File List
