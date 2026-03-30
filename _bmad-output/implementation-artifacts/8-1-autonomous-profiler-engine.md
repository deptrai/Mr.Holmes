# Story 8.1: Thiết kế Lõi Đệ Quy (Recursive Profiling Engine)

Status: ready-for-dev

## Story
**As an** OSINT Investigator
**I want** to input a single piece of information (a seed like an email or IP) and have the system automatically cross-trigger all relevant modules recursively up to a specified depth
**So that** I don't have to manually copy and paste newfound information into other modules to build a full profile.

## Acceptance Criteria
- [ ] Implement `Core/engine/autonomous_agent.py` containing a `RecursiveProfiler` class.
- [ ] The engine must accept a starting target, target type (Email, IP, Domain, Username), and a maximum `depth` (integer).
- [ ] The engine uses a BFS (Breadth-First-Search) queue or similar traversal to process targets.
- [ ] For a given target, the engine automatically discovers and calls appropriate `IntelligencePlugin` instances (e.g., LeakLookup, Shodan, SearxNG).
- [ ] New clues extracted from plugin results (e.g., finding an IP from a domain) are automatically added to the queue for the next Depth Layer.
- [ ] Implement a deduplication mechanism to ensure the same target is not scanned twice (preventing infinite loops).
- [ ] Rate limits safe-guard: Engine must throttle concurrent tasks avoiding overwhelming APIs like SearxNG and LeakLookup (or HIBP).
- [ ] Final output of the engine should be a massive structured JSON object collecting all artifacts and the node-edge relationship connections.

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

## Developer Worklog
*(Để trống - Developer sẽ ghi nhận các design changes và PR notes tại đây trong quá trình code)*
