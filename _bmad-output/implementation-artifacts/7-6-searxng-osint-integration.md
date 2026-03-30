# Story 7.6: SearxNG OSINT Integration

Status: in-progress

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

## Dev Agent Guardrails & Technical Restrictions
**Architecture Compliance:**
- 🚫 Forbidden to create global variables outside of class scopes.
- 🚫 Cannot use `requests.get()`. Must use `aiohttp.ClientSession()`.
- ✅ Handle HTTP 429 carefully: Since public SearxNG nodes can hit limits arbitrarily, return is_success=False explicitly suggesting the user change the `MH_SEARXNG_URL`.
- ✅ JSON output formatting maps parsed URL/Title objects directly to `data["osint_urls"]`.

**Testing Requirements:**
- Must mock multiple SearxNG response variations using `aioresponses` (200 OK, 429 Limit, 404 Target down).
- Must verify that missing `.env` gracefully falls back to `"https://searx.be/search"`.

## Project Context Reference
- Epic context: Epic 7 - External Intelligence APIs
- System rules: Adhere to concurrent HTTP polling patterns to respect timeouts (max 15s).
