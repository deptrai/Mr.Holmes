# Story 3.3: CAPTCHA/Block Detection

Status: done

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

- [x] Task 1 — Extend `ScanResult` với `status` enum
  - [x] `ScanStatus`: FOUND, NOT_FOUND, BLOCKED, RATE_LIMITED, CAPTCHA, ERROR, TIMEOUT
- [x] Task 2 — Implement detection logic trong async_search
  - [x] Check status code: 403 → BLOCKED, 429 → RATE_LIMITED
  - [x] Check body for CAPTCHA keywords
- [x] Task 3 — Update result collector summary
- [x] Task 4 — Unit tests với mock responses

### Review Findings
- [x] [Review][Patch] Redundant local imports — FIXED (removed inline imports)
- [x] [Review][Patch] Duplicate CAPTCHA ScanResult — FIXED (`_captcha_result()` helper extracted)
- [x] [Review][Patch] `block_summary()` lock inconsistency — FIXED (single lock acquisition)
- [x] [Review][Patch] Missing test RESPONSE_URL + 429 — FIXED (test added)
- [x] [Review][Defer] No CAPTCHA check for RESPONSE_URL strategy — deferred
- [x] [Review][Defer] False positive substring matching risk — deferred

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
Gemini 2.5 Pro
### Completion Notes List
- `ScanStatus` enum đã có từ trước (AC4): FOUND, NOT_FOUND, BLOCKED, RATE_LIMITED, CAPTCHA, ERROR, TIMEOUT.
- Thêm `CAPTCHA_INDICATORS` tuple và `_detect_captcha(body)` helper vào `async_search.py`.
- Refactor `_evaluate_response()`: 403/429 check universal trước strategy evaluation.
- Thêm CAPTCHA body scan cho STATUS_CODE và MESSAGE strategies (200 responses).
- Thêm `blocked_count`, `rate_limited_count`, `captcha_count`, `block_summary()` vào `ScanResultCollector`.
- `to_dict()` giờ include blocked/rate_limited/captcha counts.
- 23 TDD tests + 285 regression tests PASS.
### File List
- `[MODIFY] Core/engine/async_search.py` — CAPTCHA_INDICATORS, _detect_captcha, refactored _evaluate_response
- `[MODIFY] Core/engine/result_collector.py` — blocked_count, rate_limited_count, captcha_count, block_summary
- `[NEW] tests/engine/test_captcha_detection.py` — 23 TDD tests

## Change Log
- Story 3-3 implemented: universal block/rate-limit/CAPTCHA detection với TDD. (2026-03-27)
