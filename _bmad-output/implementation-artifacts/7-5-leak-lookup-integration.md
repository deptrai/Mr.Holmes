# Story 7.5: Leak-Lookup Backup Intelligence Integration

Status: done

## Story
**As an** OSINT investigator
**I want** to query the Leak-Lookup public API
**So that** I have a working and free alternative to HaveIBeenPwned for email and IP address breach verification.

## Acceptance Criteria
- [x] **AC1: Plugin Integration.** Must implement `LeakLookupPlugin` inheriting from `IntelligencePlugin`.
- [x] **AC2: Configuration.** Must flag `requires_api_key = True` to integrate seamlessly into the CLI Config Wizard.
- [x] **AC3: Rate Limiting compliance.** Must throttle requests to 1 request per second globally to respect the free API tier.
- [x] **AC4: Payload Parsing.** Must accurately parse the JSON `{"error": "false", "message": {...}}` response to extract breach DB names into `vulnerabilities`.
- [x] **AC5: Edge Cases.** Must handle HTTP 429 correctly and catch custom JSON payloads stating `"Invalid API Key"` (transforming to 401).

## Tasks / Subtasks
- [x] Task 1: Implement `LeakLookupPlugin` class in `Core/plugins/leak_lookup.py`
  - [x] Inherit from `IntelligencePlugin`, implement `name` and `requires_api_key` properties
  - [x] Implement `__init__(api_key)` and `SUPPORTED_TYPES` mapping
  - [x] Implement `check()` method with `aiohttp.ClientSession` POST requests
- [x] Task 2: Implement rate limiting and error handling
  - [x] Class-level `asyncio.Lock()` + `_last_request_time` 1s throttle
  - [x] Handle HTTP 429 (rate limit), HTTP != 200, JSON `error: true`, timeout, network errors
  - [x] Transform "Invalid API Key" JSON error → "401 Unauthorized" message
- [x] Task 3: Write unit tests in `tests/plugins/test_leak_lookup.py`
  - [x] test_leak_lookup_init
  - [x] test_leak_lookup_no_api_key
  - [x] test_leak_lookup_wrong_target_type
  - [x] test_leak_lookup_found_breaches
  - [x] test_leak_lookup_not_found
  - [x] test_leak_lookup_invalid_key
  - [x] test_leak_lookup_rate_limit_http_429
  - [x] test_leak_lookup_rate_limit_throttle

## Dev Agent Guardrails & Technical Restrictions
**Architecture Compliance:**
- 🚫 Forbidden to use `requests.get()`. Must use `aiohttp.ClientSession()`.
- 🚫 Forbidden to create global module mutable states except for `asyncio.Lock()`.
- ✅ Must place the plugin file inside `Core/plugins/leak_lookup.py`.
- ✅ Must hook into the existing generic `PluginResult` data model.

**Testing Requirements:**
- Must use `aioresponses` to mock `https://leak-lookup.com/api/search`.
- Must explicitly cover the API key mismatch error.

## Dev Agent Record
### Agent Model Used: Claude Sonnet (Thinking)
### Completion Notes List
- Story đã được implement đầy đủ trước khi vào `bmad-dev-story` workflow.
- Code đã khớp toàn bộ ACs: plugin hiện diện, key guard, rate-limit class lock, payload parsing, error mapping.
- 8/8 unit tests pass. Full regression 547 passed, 5 skipped — zero regressions.
- Kiểu `data["message"] = ""` (no results) được xử lý gracefully bởi `isinstance(leak_dict, dict)` guard.
- Rate-limit throttle test xác nhận độ trễ ≥ 1.0s giữa 2 lần gọi API.

### File List
- `Core/plugins/leak_lookup.py` (NEW — LeakLookupPlugin implementation)
- `tests/plugins/test_leak_lookup.py` (NEW — 8 unit tests)
- `_bmad-output/implementation-artifacts/7-5-leak-lookup-integration.md` (MODIFIED — story tracking)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (MODIFIED — status in-progress)
- `_bmad-output/planning-artifacts/prd.md` (MODIFIED — FR25 thêm vào)
- `_bmad-output/planning-artifacts/epics.md` (MODIFIED — Story 7.5 thêm vào Epic 7)

### Change Log
- 2026-03-30: Story 7.5 LeakLookupPlugin implemented and all tests passing (547/547). Status → review.
- 2026-03-30: Code review passed (Claude Opus Thinking). 1 patch applied (unused imports). 2 deferred (pre-existing patterns). Status → done.

### Review Findings
- [x] [Review][Patch] Unused imports `Dict, Any` [Core/plugins/leak_lookup.py:11] — removed
- [x] [Review][Defer] Raw int `timeout=10` thay vì `aiohttp.ClientTimeout` [Core/plugins/leak_lookup.py:91] — deferred, pre-existing pattern across all plugins
- [x] [Review][Defer] Class-level `asyncio.Lock()` trước event loop [Core/plugins/leak_lookup.py:24] — deferred, pre-existing pattern

## Project Context Reference
- Epic context: Epic 7 - External Intelligence APIs
- System rules: Follow BMad OSINT concurrent engine standards.
