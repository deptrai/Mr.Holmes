# Story 7.6: SearxNG OSINT Integration

Status: done

## Story
**As an** OSINT investigator
**I want** to query targets via SearxNG public APIs
**So that** I bypass Captchas when performing automated credential-finding and Dorking operations.

## Acceptance Criteria
- [x] **AC1: Metasearch Plugin Integration.** Must implement `SearxngPlugin` inheriting from `IntelligencePlugin`.
- [x] **AC2: Seamless Fallbacks.** Must default to a public Searx instance (e.g. `https://searx.be/search`) but allow overriding via environment variable `MH_SEARXNG_URL`.
- [x] **AC3: No API Key Required.** `requires_api_key` must be explicitly False, bypassing the Wizard lock logic.
- [x] **AC4: Payload Orchestration.** Must query SearxNG using `"format": "json"` and process the `results[]` array, extracting valid `.url` fields for scraping targets.
- [x] **AC5: Multi-target Formatting.** Target types (IP, EMAIL, USERNAME) map out to OSINT Dorking strings (e.g. `"email_address" password OR leak`).

## Tasks / Subtasks
- [x] Task 1: Create SearxngPlugin (`Core/plugins/searxng.py`)
  - [x] Implement fallbacks to `https://searx.be/search`
  - [x] Define queries dynamically based on target types
- [x] Task 2: Implement SearxNG API call logic
  - [x] Send requests via `aiohttp.ClientSession()` handling HTTP 429
  - [x] Map responses directly to `data["osint_urls"]`
- [x] Task 3: Author Tests (`tests/plugins/test_searxng.py`)
  - [x] Test fallbacks (`test_searxng_init_default`, `test_searxng_init_custom_env`)
  - [x] Test Dork query builder
  - [x] Test API JSON parsing and error handling

## Dev Agent Guardrails & Technical Restrictions
**Architecture Compliance:**
- 🚫 Forbidden to create global variables outside of class scopes.
- 🚫 Cannot use `requests.get()`. Must use `aiohttp.ClientSession()`.
- ✅ Handle HTTP 429 carefully: Since public SearxNG nodes can hit limits arbitrarily, return is_success=False explicitly suggesting the user change the `MH_SEARXNG_URL`.
- ✅ JSON output formatting maps parsed URL/Title objects directly to `data["osint_urls"]`.

**Testing Requirements:**
- Must mock multiple SearxNG response variations using `aioresponses` (200 OK, 429 Limit, 404 Target down).
- Must verify that missing `.env` gracefully falls back to `"https://searx.be/search"`.

## Dev Agent Record
### Agent Model Used: Gemini 3.1 Pro
### Completion Notes List
- Story được developer implement cùng lúc với Story 7.5.
- Code hoàn toàn thỏa mãn ACs: `requires_api_key=False`, payload trả về `osint_urls`, mapping dork string tùy loại target.
- Tests (9/9) passed coverage cho SearxngPlugin. Full regression passed.

### File List
- `Core/plugins/searxng.py` (NEW)
- `tests/plugins/test_searxng.py` (NEW)
- `_bmad-output/implementation-artifacts/7-6-searxng-osint-integration.md` (MODIFIED)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (MODIFIED)

### Change Log
- 2026-03-30: Tests implemented, status → review. 556/556 regression tests passed.
- 2026-03-30: Code review passed (Claude Opus Thinking). 4 patches applied, 2 deferred. Status → done.

### Review Findings
- [x] [Review][Patch] Unused imports `Dict, Any, urllib.parse` [Core/plugins/searxng.py:11-12] — removed
- [x] [Review][Patch] Repeated `import re`/`import asyncio` inside test fns [test_searxng.py] — hoisted to top-level
- [x] [Review][Patch] `results` could be `None` from API → guard `or []` [Core/plugins/searxng.py:95] — fixed
- [x] [Review][Patch] Non-deterministic `set` order in error message → `sorted()` [Core/plugins/searxng.py:62] — fixed
- [x] [Review][Defer] Raw int `timeout=15` [Core/plugins/searxng.py:79] — deferred, pre-existing pattern
- [x] [Review][Defer] No rate limiting mechanism — deferred, by design (AC doesn't require)

## Project Context Reference
- Epic context: Epic 7 - External Intelligence APIs
- System rules: Adhere to concurrent HTTP polling patterns to respect timeouts (max 15s).
