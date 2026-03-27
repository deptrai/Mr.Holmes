# Story 3.2: Proxy Health-Check trước Session

Status: ready-for-dev

## Story

As a user,
I want proxy được health-check trước khi bắt đầu scan session,
so that scan không bắt đầu với dead proxy — tiết kiệm thời gian.

## Acceptance Criteria

1. **AC1:** `ProxyManager.health_check()` async method test proxy connectivity
2. **AC2:** Health-check gửi request tới known endpoint (httpbin.org hoặc ip-api.com)
3. **AC3:** Timeout: 5s per proxy check
4. **AC4:** Report: healthy count / total count trước khi scan
5. **AC5:** Auto-remove dead proxies từ pool

## Tasks / Subtasks

- [ ] Task 1 — Implement `async health_check(proxy_pool) → HealthReport`
- [ ] Task 2 — Concurrent health-check tất cả proxies (asyncio.gather)
- [ ] Task 3 — HealthReport dataclass: healthy, dead, total
- [ ] Task 4 — Auto-prune dead proxies
- [ ] Task 5 — Integration into scan startup flow
- [ ] Task 6 — Unit tests with mocked endpoints

## Dev Notes

### Dependencies
- **REQUIRES Story 1.5** — ProxyManager
- **REQUIRES Story 2.1** — aiohttp for async checks

### File Structure
```
Core/proxy/
└── manager.py  # MODIFY — add health_check()
```

## Dev Agent Record
### Agent Model Used
### Completion Notes List
### File List
