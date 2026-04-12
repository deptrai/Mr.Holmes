# Story 9.17: Deferred Review Improvements

Status: done

## Story

As an OSINT analyst,
I want the profiling system to handle edge cases better (bot filtering, input validation, error clarity, clue propagation),
so that I get cleaner, more complete data from the autonomous profiler pipeline.

## Acceptance Criteria

1. **Bot filter expansion** — `_check_username` and `_check_email` in `Core/plugins/github.py` filter bot names beyond just `[bot]` suffix:
   - Case-insensitive check for `[bot]` suffix
   - Known bot patterns: `github-actions`, `dependabot`, `renovate`, `snyk`, `codecov`
   - Extracted to reusable `_is_bot_name(name)` static method

2. **GitHub 403 error differentiation** — `GitHubPlugin` parses 403 response body JSON to differentiate "rate limit exceeded" vs "access denied":
   - If body contains `"rate limit"` → message says "Rate limit exceeded"
   - Otherwise → message says "Access denied"
   - Graceful fallback if body is not parseable JSON

3. **`detect_seed_type` supports IP/DOMAIN** — `detect_seed_type()` in `Core/autonomous_cli.py` detects:
   - IP addresses (IPv4 pattern `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`) → `"IP"`
   - Domain names (contains `.` but no `@`, not an IP) → `"DOMAIN"`
   - Existing EMAIL/PHONE/USERNAME detection unchanged

4. **`extract_clues` propagates real_names** — `GitHubPlugin.extract_clues()` returns `("name", "USERNAME")` tuples for each `real_names` entry in addition to email clues. `StagedProfiler` already calls `plugin.extract_clues()` and feeds results into BFS graph.

5. **StagedProfiler routing test** — Unit test in `tests/engine/test_staged_profiler.py` (or `tests/test_autonomous_cli.py`) verifying `_run_async` routes to `StagedProfiler` when plugins have `stage >= 2`, and to `RecursiveProfiler` when all plugins are stage 1.

6. **`_build_profile_entity` extracts emails** — `_build_profile_entity()` in `Core/autonomous_cli.py` extracts `emails` from GitHub plugin data (`data["emails"]`) into `entity.emails` as `SourcedField` entries.

7. Unit tests for all changes with ≥ 80% coverage on modified code.

## Tasks / Subtasks

- [x] Task 1: Expand bot filter in GitHubPlugin (AC: 1)
  - [x] Create `_is_bot_name(name)` static method with known patterns
  - [x] Replace `endswith("[bot]")` calls in `_check_username` and `_check_email`
  - [x] Add tests for bot name variants
- [x] Task 2: Differentiate GitHub 403 errors (AC: 2)
  - [x] Parse 403 response body in `_check_username` and `_check_email`
  - [x] Add tests for rate-limit vs access-denied 403
- [x] Task 3: Extend `detect_seed_type` for IP/DOMAIN (AC: 3)
  - [x] Add IP regex pattern check
  - [x] Add DOMAIN detection (has `.`, no `@`, not IP)
  - [x] Add tests for IP, DOMAIN, edge cases
- [x] Task 4: Propagate real_names in `extract_clues` (AC: 4)
  - [x] Return `("name", "USERNAME")` for each `real_names` entry
  - [x] Add tests
- [x] Task 5: StagedProfiler routing test (AC: 5)
  - [x] Test `_run_async` routes to StagedProfiler vs RecursiveProfiler
- [x] Task 6: Extract emails in `_build_profile_entity` (AC: 6)
  - [x] Parse `data["emails"]` from plugin results into `entity.emails`
  - [x] Add tests
- [x] Task 7: Run full regression suite (AC: 7)

### Review Findings

- [x] [Review][Patch] P1: `_IPV4_RE` không validate octet range — `999.999.999.999` classified là IP [`autonomous_cli.py:80`]
- [x] [Review][Patch] P2: `_check_username` profile `name` không filter qua `_is_bot_name` [`github.py:229`]
- [x] [Review][Patch] P3: `_is_bot_name` thiếu type guard cho non-string input [`github.py:81`]
- [x] [Review][Patch] P4: `_parse_403_message` — `message` field có thể là dict/list [`github.py:90`]
- [x] [Review][Patch] P5: `_build_profile_entity` email value thiếu isinstance check [`autonomous_cli.py:218`]
- [x] [Review][Defer] W1: `X-RateLimit-Reset` non-integer value uncaught [`github.py:119`] — deferred, pre-existing 9.7
- [x] [Review][Defer] W2: Commit author/item type guards missing [`github.py:234`] — deferred, pre-existing 9.7
- [x] [Review][Defer] W3: `_check_email` trả input email không filter noreply [`github.py:326`] — deferred, feature scope
- [x] [Review][Defer] W4: `_BOT_PATTERNS` incomplete — thiếu web-flow, semantic-release-bot [`github.py:78`] — deferred, incremental
- [x] [Review][Defer] W5: `real_names` → `USERNAME` type có thể gây BFS misroute [`github.py:149`] — deferred, spec-level design

## Dev Notes

### Origin

All items originate from code review deferred findings:
- AC1, AC2, AC4: from `deferred-work.md` § "code review of story 9-7"
- AC3, AC5, AC6: from `deferred-work.md` § "code review of story 9-6"

### File Locations

| File | Action |
|------|--------|
| `Core/plugins/github.py` | MODIFY (AC1, AC2, AC4) |
| `Core/autonomous_cli.py` | MODIFY (AC3, AC6) |
| `tests/plugins/test_github_plugin.py` | MODIFY (AC1, AC2, AC4) |
| `tests/test_autonomous_cli.py` | MODIFY (AC3, AC5, AC6) |

### Architecture Notes

- `extract_clues` return type is `list[tuple[str, str]]` — tuples of `(value, type)`. Adding `("real_name", "USERNAME")` follows existing convention.
- `StagedProfiler` already calls `plugin.extract_clues()` at line ~444 of `autonomous_agent.py` — no changes needed there.
- `detect_seed_type` is called from `_InputFlow.collect()` — `_VALID_TYPES` already includes `"IP"` and `"DOMAIN"`.
- `_build_profile_entity` iterates `plugin_results` — GitHub results have `data["emails"]` list.

### Excluded Deferred Items (too large for this story)

- **Session reuse across plugins** — requires `IntelligencePlugin` protocol change + all plugin refactors
- **`asyncio.run()` refactor** — architectural change affecting Menu.py integration pattern
- **Option 16 lang file label** — language files (`english.json` etc.) not found in expected location; needs investigation

### References

- Plugin pattern: `Core/plugins/github.py`
- Clue extraction: `Core/engine/autonomous_agent.py:_extract_clues_from_result`
- ProfileEntity: `Core/models/profile_entity.py`
- Deferred items: `_bmad-output/implementation-artifacts/deferred-work.md`

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Debug Log References
N/A — all 36 new tests passed GREEN on first implementation run.

### Completion Notes List
- AC1: `_is_bot_name()` static method with `[bot]` suffix (case-insensitive) + 5 known patterns
- AC2: `_parse_403_message()` parses response body, differentiates "Rate limit exceeded" vs "Access denied"
- AC3: `_IPV4_RE` regex + DOMAIN fallback added to `detect_seed_type()`
- AC4: `extract_clues()` now returns both `(email, "EMAIL")` and `(name, "USERNAME")` tuples
- AC5: 2 routing tests added — `StagedProfiler` when stage≥2, `RecursiveProfiler` when all stage==1
- AC6: `_build_profile_entity()` extracts `data["emails"]` into `entity.emails` as `SourcedField` entries
- Regression: 239 pass in relevant test scope (1 pre-existing searxng failure unrelated)

### File List
- `Core/plugins/github.py` (modified)
- `Core/autonomous_cli.py` (modified)
- `tests/plugins/test_github_plugin.py` (modified)
- `tests/test_autonomous_cli.py` (modified)
