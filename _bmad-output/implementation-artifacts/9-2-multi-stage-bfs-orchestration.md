# Story 9.2: Multi-Stage BFS Orchestration

Status: done

## Story

As the BFS engine,
I want to route clues to the correct enrichment stage so that plugins run in the right order (identity expansion before deep enrichment),
so that Epic 9's multi-stage pipeline can discover more data per seed than the flat single-stage BFS from Epic 8.

## Acceptance Criteria

1. `StageRouter` class tại `Core/engine/stage_router.py`:
   - `route(target_type: str) -> int` — returns stage number:
     - `"EMAIL"` → `2`
     - `"USERNAME"` → `2`
     - `"PHONE"` → `3`
     - `"DOMAIN"` → `3`
     - `"IP"` → `3`
     - Any unknown type → `1` (fallback, not skipped)
   - `filter_plugins(plugins, stage: int) -> list[IntelligencePlugin]` — returns plugins whose `stage` attribute matches (or plugins without `stage` attribute default to stage `1`)

2. `IntelligencePlugin` protocol extended tại `Core/plugins/base.py`:
   - Thêm optional property `stage: int` với default `1` (backward compat — existing plugins không implement sẽ default về stage 1)
   - Existing plugins (HIBP, LeakLookup, Shodan, SearxNG) không cần sửa — chúng default về stage 1 và vẫn chạy trong flat mode

3. `StagedProfiler` class tại `Core/engine/autonomous_agent.py`:
   - `run_staged(seed_target: str, seed_type: str, plugins: list[IntelligencePlugin]) -> dict[str, Any]`
   - **Phase A — Stage 2:** Chạy tất cả stage-2 plugins trên seed target (nếu seed_type match stage 2), async/parallel qua `asyncio.gather`
   - **Phase B — Clue extraction:** Extract clues từ Phase A results; gom PHONE + DOMAIN clues cho Stage 3
   - **Phase C — Stage 3:** Chạy tất cả stage-3 plugins trên PHONE/DOMAIN clues discovered ở Phase A, async/parallel
   - **Phase D — Stage 1 fallback:** Chạy stage-1 plugins (existing Epic 8 plugins) trên seed qua existing `RecursiveProfiler.run_profiler()` logic
   - Returns combined `ProfileGraph.to_dict()` — same schema as Epic 8 output

4. Backward compatibility — `RecursiveProfiler.run_profiler()` không bị thay đổi:
   - `autonomous_cli.py` chỉ gọi `StagedProfiler.run_staged()` khi có staged plugins (stage 2 hoặc 3)
   - Nếu tất cả plugins là stage 1, fallback hoàn toàn về `RecursiveProfiler.run_profiler()` — đảm bảo Epic 8 behavior unchanged

5. Plugin failure isolation — 1 plugin fail không crash stage:
   - Mỗi plugin được wrap bởi `_safe_plugin_run()` (tái sử dụng từ `RecursiveProfiler`)
   - Stage có thể hoàn thành với partial results

6. `_run_async()` tại `Core/autonomous_cli.py` updated:
   - Phát hiện staged plugins (có plugin nào có `stage >= 2` không?)
   - Nếu có: dùng `StagedProfiler.run_staged()`
   - Nếu không: dùng `RecursiveProfiler.run_profiler()` (unchanged Epic 8 path)

7. Integration test tại `tests/engine/test_staged_profiler.py`:
   - Mock stage-2 plugin trả về EMAIL + PHONE clues
   - Mock stage-3 plugin nhận PHONE clue từ stage-2
   - Verify stage-3 plugin được gọi với phone number discovered ở stage-2
   - Verify stage-2 plugin không được gọi với PHONE targets (wrong stage)
   - Verify `RecursiveProfiler.run_profiler()` vẫn chạy được độc lập (backward compat test)

## Tasks / Subtasks

- [x] Task 1: Extend `IntelligencePlugin` protocol (AC: 2)
  - [x] Thêm `stage: int` property với default `1` vào `Core/plugins/base.py`
  - [x] Verify existing plugins (HIBP, LeakLookup, Shodan, SearxNG) không cần sửa (dùng `getattr(plugin, 'stage', 1)` khi check)

- [x] Task 2: Tạo `StageRouter` (AC: 1)
  - [x] `Core/engine/stage_router.py` — mới hoàn toàn
  - [x] `route(target_type) -> int` mapping
  - [x] `filter_plugins(plugins, stage) -> list` dùng `getattr(plugin, 'stage', 1)`

- [x] Task 3: Implement `StagedProfiler` (AC: 3, 4, 5)
  - [x] Add class `StagedProfiler` vào `Core/engine/autonomous_agent.py` (file hiện có)
  - [x] `run_staged()` — 4-phase pipeline (A: stage-2, B: clue extract, C: stage-3, D: stage-1 fallback)
  - [x] Tái sử dụng `_safe_plugin_run()` và `_extract_clues_from_result()` từ `RecursiveProfiler`
  - [x] Gộp kết quả tất cả phases vào 1 `ProfileGraph` object

- [x] Task 4: Update `autonomous_cli.py` (AC: 6)
  - [x] Detect staged plugins: `any(getattr(p, 'stage', 1) >= 2 for p in plugins)`
  - [x] Route to `StagedProfiler.run_staged()` hoặc `RecursiveProfiler.run_profiler()`

- [x] Task 5: Viết integration tests (AC: 7)
  - [x] `tests/engine/test_staged_profiler.py`
  - [x] Mock plugins với `stage=2` và `stage=3`
  - [x] Test stage routing, clue passing, failure isolation, backward compat — 19/19 pass

## Dev Notes

### Existing Patterns to Follow

- `RecursiveProfiler._safe_plugin_run()` (`Core/engine/autonomous_agent.py:298`) — tái sử dụng cho `StagedProfiler`, không duplicate code
- `_extract_clues_from_result()` (`Core/engine/autonomous_agent.py:91`) — tái sử dụng để extract clues sau Stage 2
- `_SEMAPHORE_LIMIT = 5` — dùng cùng semaphore limit cho `StagedProfiler`
- `ProfileGraph.to_dict()` (`Core/engine/autonomous_agent.py:65`) — output schema phải giữ nguyên để `autonomous_cli.py` không cần sửa output handling

### Key Design Decisions

**`getattr` thay vì Protocol enforcement cho `stage`:**
```python
# Trong StageRouter.filter_plugins():
stage_num = getattr(plugin, 'stage', 1)  # Default 1 nếu plugin không có attribute
```
Điều này đảm bảo Epic 8 plugins (HIBP, LeakLookup, Shodan, SearxNG) hoạt động mà không cần sửa.

**Stage detection trong `autonomous_cli.py`:**
```python
has_staged_plugins = any(getattr(p, 'stage', 1) >= 2 for p in plugins)
if has_staged_plugins:
    profiler = StagedProfiler(max_depth=max_depth)
    graph_data = await profiler.run_staged(target, target_type, plugins)
else:
    profiler = RecursiveProfiler(max_depth=max_depth)
    graph_data = await profiler.run_profiler(target, target_type, plugins)
```

**`StagedProfiler.run_staged()` pipeline:**
```python
async def run_staged(self, seed_target, seed_type, plugins):
    graph = ProfileGraph()
    router = StageRouter()
    semaphore = asyncio.Semaphore(self._SEMAPHORE_LIMIT)

    # Phase A: Stage 2 (identity expansion)
    stage2_plugins = router.filter_plugins(plugins, stage=2)
    if stage2_plugins and router.route(seed_type) == 2:
        tasks = [self._safe_plugin_run(p, seed_target, seed_type, semaphore)
                 for p in stage2_plugins]
        stage2_results = await asyncio.gather(*tasks)
        # record results, extract clues...

    # Phase B: collect PHONE/DOMAIN from stage2_results
    stage3_targets = []  # (target, type) tuples for stage 3

    # Phase C: Stage 3 (deep enrichment on discovered clues)
    stage3_plugins = router.filter_plugins(plugins, stage=3)
    for clue_target, clue_type in stage3_targets:
        if router.route(clue_type) == 3 and stage3_plugins:
            tasks = [self._safe_plugin_run(p, clue_target, clue_type, semaphore)
                     for p in stage3_plugins]
            # ...

    # Phase D: Stage 1 (existing Epic 8 plugins, flat BFS)
    stage1_plugins = router.filter_plugins(plugins, stage=1)
    if stage1_plugins:
        flat_profiler = RecursiveProfiler(max_depth=self.max_depth)
        flat_result = await flat_profiler.run_profiler(seed_target, seed_type, stage1_plugins)
        # merge flat_result into graph...

    return graph.to_dict()
```

**Không thêm `USERNAME` extraction vào Stage 2 clue pass-down** — việc đó đã được handle bởi `RecursiveProfiler`'s `auto:email-prefix` edge (Phase D). Avoid duplication.

### File Locations

| File | Action |
|------|--------|
| `Core/engine/stage_router.py` | CREATE |
| `Core/engine/autonomous_agent.py` | MODIFY — thêm `StagedProfiler` class, không sửa `RecursiveProfiler` |
| `Core/plugins/base.py` | MODIFY — thêm optional `stage: int` property vào Protocol (với comment backward compat) |
| `Core/autonomous_cli.py` | MODIFY — detect staged plugins, route to appropriate profiler |
| `tests/engine/test_staged_profiler.py` | CREATE |

### Project Structure Notes

- `StagedProfiler` đặt trong cùng file `autonomous_agent.py` (không tạo file mới) để tái sử dụng module-level helpers
- `StageRouter` đặt trong file riêng `stage_router.py` — logic routing thuần, dễ test độc lập
- Import order: `autonomous_agent.py` import `StageRouter` từ `stage_router.py`

### References

- Existing BFS engine: `Core/engine/autonomous_agent.py#RecursiveProfiler` (line 156-296)
- Plugin protocol: `Core/plugins/base.py#IntelligencePlugin`
- CLI orchestration: `Core/autonomous_cli.py#_run_async`
- PRD FR14-FR18 (clue extraction, stage routing, dedup, async, graceful failure): `_bmad-output/planning-artifacts/prd-epic9.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

_none_

### Completion Notes List

- `StageRouter` cố ý KHÔNG import từ `base.py` để tránh circular dependency — dùng `getattr(p, 'stage', 1)` duck typing thay vì Protocol check
- `StagedProfiler._safe_plugin_run()` là copy của `RecursiveProfiler._safe_plugin_run()` (không thể kế thừa vì không muốn thay đổi `RecursiveProfiler`)
- `_extract_clues_from_result()` được tái sử dụng trực tiếp (module-level function)
- Phase D (stage-1 fallback) dùng `RecursiveProfiler` hoàn toàn riêng biệt với `max_depth` giống nhau
- 19/19 tests pass, 0 regression

### File List

- `Core/engine/stage_router.py` (created)
- `Core/engine/autonomous_agent.py` (modified — added `StagedProfiler`, import `StageRouter`)
- `Core/plugins/base.py` (modified — added doc comment về optional `stage` attribute)
- `Core/autonomous_cli.py` (modified — staged routing detection + `StagedProfiler` route)
- `tests/engine/test_staged_profiler.py` (created)

### Review Findings

- [x] [Review][Patch] P1 CRITICAL: `StagedProfiler` Phase B missing `plugin.extract_clues()` calls — stage-3 PHONE clues from Holehe never reached pipeline [`Core/engine/autonomous_agent.py`] — FIXED
- [x] [Review][Patch] P4: `_safe_plugin_run` duplicated between `RecursiveProfiler` and `StagedProfiler` — extracted to module-level function [`Core/engine/autonomous_agent.py`] — FIXED
