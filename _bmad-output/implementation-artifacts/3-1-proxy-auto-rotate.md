# Story 3.1: Proxy Auto-Rotate khi Proxy Chết

Status: ready-for-dev

## Story

As a user,
I want proxy tự động rotate sang proxy khác khi proxy hiện tại chết,
so that scan không bị gián đoạn vì proxy failure.

## Acceptance Criteria

1. **AC1:** `ProxyManager.rotate()` method tự động switch sang proxy tiếp theo trong pool
2. **AC2:** Proxy pool configurable — load từ file hoặc list
3. **AC3:** Khi proxy chết (`ProxyDeadError`) → auto-rotate + retry request
4. **AC4:** Khi hết proxy pool → fallback direct connection + warning
5. **AC5:** Rotation strategy: round-robin (default), random (optional)

## Tasks / Subtasks

- [ ] Task 1 — Extend ProxyManager (Story 1.5) với proxy pool
  - [ ] `load_proxy_pool(source: str | list)` — load từ file/list
  - [ ] `rotate() → dict | None` — next proxy in pool
  - [ ] `mark_dead(proxy_url)` — remove from active pool

- [ ] Task 2 — Implement round-robin rotation
- [ ] Task 3 — Integrate with async search — catch `ProxyDeadError` → rotate
- [ ] Task 4 — Fallback khi pool exhausted
- [ ] Task 5 — Unit tests

## Dev Notes

### Dependencies
- **REQUIRES Story 1.5** — ProxyManager base class
- **REQUIRES Story 2.4** — ProxyDeadError exception

### Architecture Compliance
- [Source: `architecture.md`#ProxyManager Pattern]
- [Source: `prd.md`#FR6] Auto-rotate proxy

### File Structure
```
Core/proxy/
└── manager.py  # MODIFY — add pool, rotate(), mark_dead()
```

## Dev Agent Record
### Agent Model Used
### Completion Notes List
### File List
