# Story 7.3: Shodan Integration

Status: ready-for-dev

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

- [ ] Task 1 — Implement `ShodanPlugin` class
- [ ] Task 2 — Shodan REST API client
- [ ] Task 3 — Parse host info into PluginResult
- [ ] Task 4 — Unit tests

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
### Completion Notes List
### File List
