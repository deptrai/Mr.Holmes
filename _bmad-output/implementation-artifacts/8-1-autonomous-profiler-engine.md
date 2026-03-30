# Story 8.1: Thiết kế Lõi Đệ Quy (Recursive Profiling Engine)

Status: review

## Story
**As an** OSINT Investigator
**I want** to input a single piece of information (a seed like an email or IP) and have the system automatically cross-trigger all relevant modules recursively up to a specified depth
**So that** I don't have to manually copy and paste newfound information into other modules to build a full profile.

## Acceptance Criteria
- [x] Implement `Core/engine/autonomous_agent.py` containing a `RecursiveProfiler` class.
- [x] The engine must accept a starting target, target type (Email, IP, Domain, Username), and a maximum `depth` (integer).
- [x] The engine uses a BFS (Breadth-First-Search) queue or similar traversal to process targets.
- [x] For a given target, the engine automatically discovers and calls appropriate `IntelligencePlugin` instances (e.g., LeakLookup, Shodan, SearxNG).
- [x] New clues extracted from plugin results (e.g., finding an IP from a domain) are automatically added to the queue for the next Depth Layer.
- [x] Implement a deduplication mechanism to ensure the same target is not scanned twice (preventing infinite loops).
- [x] Rate limits safe-guard: Engine must throttle concurrent tasks avoiding overwhelming APIs like SearxNG and LeakLookup (or HIBP).
- [x] Final output of the engine should be a massive structured JSON object collecting all artifacts and the node-edge relationship connections.

## Project Context Reference
- Epic context: Epic 8 - Autonomous Profiler (Deep OSINT Agent)
- Architecture alignment: Uses `asyncio` and `IntelligencePlugin` protocols established in Epic 2 and Epic 7.
- Integration dependencies: Depends on all `Core/plugins/` (from Epic 7) and `Core/Support/Requests_Search.py` (Epic 2).

## Implementation Sandbox
### Tóm tắt tài liệu & Phương pháp tiếp cận
- Khái niệm: **Breadth-First Search Queue** (`asyncio.Queue` is optimal). 
- State Tracker: Maintain `visited = set()`.
- Data structure: 
  - `Node`: Represents an entity (e.g. `admin@facebook.com` - EMAIL).
  - `Edge`: Created by a plugin linking two nodes (e.g., Shodan finding an IP for a Domain).
- Depth Layering: Traversal should stop when traversing deeper than the globally provided `max_depth` (default 2).
- Throttling: Re-use `asyncio.Semaphore` mechanism or simply process layers iteratively with bounded concurrency.

### API Contracts / Specs
Input signature draft:
```python
async def run_profiler(seed_target: str, seed_type: str, max_depth: int = 2) -> Dict[str, Any]:
    # implementation here
```

Giao tiếp liên module (Inter-module communication):
Cần parse the `data` chunk returned by Plugins. Example: standardizing data output format across plugins so the deduplication logic can extract IP/Emails/Usernames reliably using Regex or fixed dictionary keys.

## File List
- `Core/engine/autonomous_agent.py` [NEW] — RecursiveProfiler BFS engine with clue extraction
- `tests/engine/test_autonomous_agent.py` [NEW] — 13 unit tests (import, output, dedup, depth, resilience)

## Dev Agent Record

### Implementation Plan
- BFS via `current_layer` list iterating depth-by-depth
- `visited: set[tuple[str, str]]` ensures no target/type combo is scanned twice
- `asyncio.Semaphore(5)` throttles concurrent plugin calls
- Clue extraction via regex (`_EMAIL_RE`, `_IP_RE`) + explicit dict keys (`emails`, `hostnames`)
- `ProfileGraph.to_dict()` serialises to plain dict for downstream JSON/PDF/HTML use
- `_safe_plugin_run` catches all exceptions — engine never crashes from bad plugin

### Completion Notes
- 13/13 new tests PASS (RED → GREEN → REFACTOR cycle completed)
- 556/556 existing tests still pass (zero regressions)
- max_depth=1: scans only seed. max_depth=2: scans seed + 1 level of discovered clues

## Change Log
- 2026-03-30: Story 8.1 implemented by AI Developer. Status → review.
