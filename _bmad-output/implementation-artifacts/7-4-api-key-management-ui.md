# Story 7.4: API Key Management UI

Status: ready-for-dev

## Story

As a user,
I want giao diện quản lý API keys cho external services,
so that setup HIBP/Shodan keys dễ dàng và an toàn.

## Acceptance Criteria

1. **AC1:** CLI command: `python3 MrHolmes.py --config api-keys`
2. **AC2:** Interactive wizard: add/update/remove API keys
3. **AC3:** Keys lưu vào `.env` (encrypted tương lai)
4. **AC4:** Validate key trước khi save (test API call)
5. **AC5:** Show key status: configured/missing/invalid

## Tasks / Subtasks

- [ ] Task 1 — CLI config subcommand
- [ ] Task 2 — Key management wizard (Rich prompts)
- [ ] Task 3 — Key validation (test API call)
- [ ] Task 4 — Status display

## Dev Notes

### Dependencies
- **REQUIRES Story 4.2** — .env management
- **REQUIRES Story 5.1** — CLI subcommands
- **REQUIRES Story 7.1** — Plugin system knows which keys needed

### File Structure
```
Core/cli/
└── config_wizard.py  # NEW
```

## Dev Agent Record
### Agent Model Used
### Completion Notes List
### File List
