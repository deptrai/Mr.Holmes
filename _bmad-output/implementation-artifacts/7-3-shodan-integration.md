# Story 7.3: Shodan Integration

Status: done

## Story

As a user,
I want to query Shodan cho IP/port intelligence,
so that network exposure data bổ sung vào OSINT investigation.

## Acceptance Criteria

1. **AC1:** `ShodanPlugin` implements `IntelligencePlugin`
2. **AC2:** Host lookup: open ports, services, banners
3. **AC3:** Query types: IP lookup, domain resolve, port search
4. **AC4:** Free tier support (limited queries) + paid tier
5. **AC5:** Results include: open ports, services, vulnerabilities (CVEs)

## Tasks / Subtasks

- [x] Task 1 — Implement `ShodanPlugin` class
- [x] Task 2 — Shodan REST API client
- [x] Task 3 — Parse host info into PluginResult
- [x] Task 4 — Unit tests

## Dev Notes

### Shodan API
- Endpoint: `https://api.shodan.io/shodan/host/{ip}?key={key}`
- Free tier: limited lookups

### Dependencies
- **REQUIRES Story 7.1** — Plugin Interface

### File Structure
```
Core/plugins/
└── shodan.py  # NEW — ShodanPlugin
```

## Dev Agent Record
### Agent Model Used
Gemini 1.5 Pro

### Completion Notes List
- Bmad Dev Agent designed and shipped `ShodanPlugin` conforming to `IntelligencePlugin` protocol.
- Shodan Rate limiting enforcement successfully migrated to use the `asyncio.Lock()` non-blocking abstraction.
- Built host lookup parser designed for endpoint `/shodan/host/{ip}` (AC1 & AC2).
- Data extracted effectively, deduplicating banners into vulnerabilities & CVEs lists (AC5).
- Exception logic handles edge cases natively, yielding correctly mapped 404, 401, 429 errors.
- Tests (9 unit validations) created via `aioresponses` mocked backend.
- Regression checked maintaining 100% green integrity at 532 asserts.

### File List
- `Core/plugins/shodan.py`
- `tests/plugins/test_shodan.py`

### Review Findings
- [x] [Review][Defer] ClientSession is re-created for every API call instead of using global connection pooling. This matches behavior of `HIBPPlugin` and represents a broader architectural constraint of the IntelligencePlugin interface design. Marked deferred pending Epic-wide session standard. [Core/plugins/shodan.py:94]
- [x] [Review][Acceptance] Excellent foresight on vulnerability payload structure parsing (handling both dicts and arrays depending on Shodan banner payload iteration). No patches needed. [Core/plugins/shodan.py:127]
