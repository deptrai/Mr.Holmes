# Story 3.3: CAPTCHA/Block Detection

Status: ready-for-dev

## Story

As a user,
I want Mr.Holmes tự detect khi bị CAPTCHA hoặc block bởi target site,
so that kết quả false-negative giảm và user được thông báo rõ ràng.

## Acceptance Criteria

1. **AC1:** Detect HTTP 403 (Forbidden) → mark as "blocked"
2. **AC2:** Detect HTTP 429 (Too Many Requests) → mark as "rate-limited"
3. **AC3:** Detect CAPTCHA trong HTML body (keywords: "captcha", "recaptcha", "hcaptcha", "challenge")
4. **AC4:** `ScanResult.status` phân biệt: found / not_found / blocked / rate_limited / captcha
5. **AC5:** Summary report cuối scan: X blocked, Y rate-limited, Z captcha

## Tasks / Subtasks

- [ ] Task 1 — Extend `ScanResult` với `status` enum
  - [ ] `ScanStatus`: FOUND, NOT_FOUND, BLOCKED, RATE_LIMITED, CAPTCHA, ERROR, TIMEOUT
- [ ] Task 2 — Implement detection logic trong async_search
  - [ ] Check status code: 403 → BLOCKED, 429 → RATE_LIMITED
  - [ ] Check body for CAPTCHA keywords
- [ ] Task 3 — Update result collector summary
- [ ] Task 4 — Unit tests với mock responses

## Dev Notes

### CAPTCHA Detection Keywords
```python
CAPTCHA_INDICATORS = [
    "captcha", "recaptcha", "hcaptcha", "cf-challenge",
    "challenge-platform", "challenge-form", "turnstile"
]
```

### Dependencies
- **REQUIRES Story 2.1** — async search
- **REQUIRES Story 2.3** — result collector for summary

### File Structure
```
Core/engine/
└── async_search.py  # MODIFY — add detection logic
Core/models/
└── scan_result.py   # MODIFY — add ScanStatus enum
```

## Dev Agent Record
### Agent Model Used
### Completion Notes List
### File List
