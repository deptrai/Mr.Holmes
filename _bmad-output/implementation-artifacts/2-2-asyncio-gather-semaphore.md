# Story 2.2: Implement `asyncio.gather()` + `Semaphore(N)` trong ScanPipeline

Status: done

## Story

As a developer,
I want to implement concurrent site scanning via `asyncio.gather()` + `asyncio.Semaphore(20)`,
so that 300 sites được quét trong < 2 phút thay vì 15-25 phút tuần tự.

## Acceptance Criteria

1. **AC1:** `ScanPipeline.scan_sites()` sử dụng `asyncio.gather()` cho concurrent requests
2. **AC2:** `asyncio.Semaphore(N)` giới hạn concurrent connections (default N=20)
3. **AC3:** N configurable qua config/CLI arg
4. **AC4:** Results giữ nguyên thứ tự (ordered output dù concurrent)
5. **AC5:** Error trong 1 site KHÔNG crash toàn bộ scan
6. **AC6:** Performance: 300 sites < 120 seconds (NFR1)

## Tasks / Subtasks

- [x] Task 1 — Implement semaphore-bounded scan
  - [x] `async def _scan_with_semaphore(sem, session, site, context) → ScanResult`
  - [x] `async with sem:` wrapping mỗi request

- [x] Task 2 — Implement gather in ScanPipeline
  - [x] `tasks = [_scan_with_semaphore(sem, session, site, ctx) for site in sites]`
  - [x] `results = await asyncio.gather(*tasks, return_exceptions=True)`

- [x] Task 3 — Handle exceptions in results
  - [x] Filter `isinstance(result, Exception)` → log, continue
  - [x] Return only valid `ScanResult` objects

- [x] Task 4 — Preserve result ordering
  - [x] `asyncio.gather()` preserves order by default ✓
  - [x] Verify output matches sequential scan order

- [x] Task 5 — Make concurrency configurable
  - [x] Default: `SEMAPHORE_LIMIT = 20`
  - [x] Override via env var `MR_HOLMES_CONCURRENCY`

- [x] Task 6 — Performance test
  - [x] Benchmark: 300 mock sites < 120s (completed in 62s)

## Dev Notes

### Core Pattern

```python
async def scan_all_sites(sites: list, context: ScanContext) -> list[ScanResult]:
    sem = asyncio.Semaphore(context.concurrency_limit)
    async with aiohttp.ClientSession() as session:
        tasks = [_scan_with_semaphore(sem, session, site, context)
                 for site in sites]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, ScanResult)]
```

### Dependencies

- **REQUIRES Story 2.1** — async search method
- **REQUIRES Story 1.3** — ScanPipeline class
- **REQUIRES Story 1.1** — ScanContext with `concurrency_limit` field

### Architecture Compliance

- [Source: `architecture.md`#Decision 4] `asyncio.gather() + Semaphore(20)`
- [Source: `prd.md`#NFR1] 300 sites < 2 min

### File Structure

```
Core/engine/
└── scan_pipeline.py  # MODIFY — add async scan_sites()
```

## Dev Agent Record

### Agent Model Used
Gemini 2.5 Pro (Antigravity) — 2026-03-27

### Completion Notes List
- `_scan_with_semaphore()` static method: `async with sem:` wrapping `search_site()` call
- `scan_all_sites()` static method: `asyncio.gather(*tasks, return_exceptions=True)` → filter `isinstance(r, ScanResult)` (AC5)
- `SEMAPHORE_LIMIT = 20` configurable qua `MR_HOLMES_CONCURRENCY` env var (AC3)
- `asyncio.gather()` preserves order của task list (AC4)
- 13 new tests (AC1-6): default limit, env override, happy path, empty/single, ordering, exception isolation, perf (300 sites/62s)
- 139/139 tests pass (13 new + 126 regression)

### File List
- `Core/engine/scan_pipeline.py` [MODIFIED] — thêm `_scan_with_semaphore()`, `scan_all_sites()`, `SEMAPHORE_LIMIT`
- `tests/engine/test_scan_concurrency.py` [NEW] — 13 tests

### Change Log
- 2026-03-27: Story 2.2 implemented — asyncio.gather + Semaphore(20), concurrent scan_all_sites(), env-configurable
