# Story 9.3: HolehPlugin

Status: done

## Story

As an OSINT analyst,
I want to check an email against 120+ services via Holehe,
so that I can discover which platforms the target is registered on and extract recovery phone/email for BFS chaining.

## Acceptance Criteria

1. `HolehPlugin` class tại `Core/plugins/holehe.py` implement `IntelligencePlugin` protocol:
   - `name: str = "Holehe"`
   - `requires_api_key: bool = False`
   - `stage: int = 2`
   - `tos_risk: str = "tos_risk"` (Holehe gửi HTTP requests thật tới từng service)

2. `check(target: str, target_type: str) -> PluginResult`:
   - Chỉ xử lý `target_type == "EMAIL"` — return failure PluginResult cho type khác
   - Gọi holehe qua `asyncio.create_subprocess_exec` hoặc bridge qua `asyncio.get_event_loop().run_in_executor`
   - Bridge pattern: `asyncio.run(maincore([email], ...) )` wrapped trong `run_in_executor` để tránh nested event loop
   - Trả về `PluginResult` với `data`:
     ```json
     {
       "registered": ["instagram", "discord", "spotify", ...],
       "recovery_phones": ["+84 *** *** 169"],
       "recovery_emails": ["a***@g***.com"],
       "total_checked": 120,
       "total_registered": 12
     }
     ```

3. Graceful fallback khi holehe không installed:
   - `check()` thử `import holehe` — nếu `ImportError` thì return `PluginResult(is_success=False, error_message="holehe not installed. Run: pip install holehe")`
   - Không raise exception, không crash pipeline

4. Rate limiting:
   - `asyncio.Semaphore(3)` ở class level — max 3 holehe runs đồng thời
   - Holehe internally đã rate-limit requests; plugin không cần thêm delay

5. `extract_clues(result: PluginResult) -> list[tuple[str, str]]`:
   - Method bổ sung (không trong base Protocol) để `StagedProfiler` extract typed clues
   - Parse `result.data["recovery_phones"]` → `[("number", "PHONE"), ...]`
   - Parse `result.data["recovery_emails"]` → `[("email", "EMAIL"), ...]`
   - Bỏ qua partial/masked values (chứa `*`) — chỉ include fully-revealed values

6. Unit tests tại `tests/plugins/test_holehe_plugin.py` ≥ 80% coverage:
   - Test `check()` với mock holehe output → correct PluginResult structure
   - Test `check()` khi holehe không installed (mock `ImportError`) → graceful failure
   - Test `check()` với non-EMAIL target → failure PluginResult
   - Test `extract_clues()` với mixed partial/full values → chỉ full values được include
   - Test `extract_clues()` với empty result → empty list

## Tasks / Subtasks

- [x] Task 1: Tạo `Core/plugins/holehe.py` với skeleton (AC: 1)
  - [x] Class attributes: `name`, `requires_api_key`, `stage`, `tos_risk`
  - [x] Class-level semaphore: `_semaphore = asyncio.Semaphore(3)`

- [x] Task 2: Implement `check()` với holehe bridge (AC: 2, 3, 4)
  - [x] `try: from holehe.core import maincore` — ImportError → graceful failure
  - [x] Chạy holehe qua `loop.run_in_executor(None, sync_holehe_wrapper, target)`
  - [x] Parse holehe response list → registered services + recovery data
  - [x] Build `PluginResult` với cấu trúc data đã định nghĩa

- [x] Task 3: Implement `extract_clues()` (AC: 5)
  - [x] Parse recovery_phones và recovery_emails
  - [x] Filter out masked values (contains `*`)

- [x] Task 4: Viết unit tests (AC: 6)
  - [x] `tests/plugins/test_holehe_plugin.py`
  - [x] Mock `holehe.core.maincore` để tránh thực sự call services

## Dev Notes

### Holehe Library API

Holehe ≥ 1.4.0 sử dụng `trio`/`httpx` internally. Cách bridge sang asyncio:

```python
import asyncio
import concurrent.futures
from functools import partial

# Holehe's maincore is a coroutine that uses trio, NOT asyncio
# Must run in a separate thread with its own event loop
def _run_holehe_sync(email: str) -> list[dict]:
    """Run holehe in a separate thread to avoid event loop conflict."""
    import trio
    from holehe.core import maincore

    results = []

    async def _collect():
        async for result in maincore([email], timeout=10):
            results.append(result)

    trio.run(_collect)
    return results

# In check():
loop = asyncio.get_event_loop()
with concurrent.futures.ThreadPoolExecutor() as pool:
    results = await loop.run_in_executor(pool, _run_holehe_sync, target)
```

**Holehe result format** (list of dicts):
```python
{
    "name": "instagram",         # service name
    "domain": "instagram.com",
    "exists": True,              # registered on this service
    "emailrecovery": "a***@g***.com",  # partial recovery email (optional)
    "phoneNumber": "+84 *** *** 169",  # partial phone (optional)
    "others": None
}
```

### Parsing Recovery Data

```python
recovery_phones = []
recovery_emails = []
for item in results:
    if item.get("exists"):
        phone = item.get("phoneNumber", "")
        if phone and "*" not in phone:  # only fully revealed
            recovery_phones.append(phone)
        email = item.get("emailrecovery", "")
        if email and "*" not in email:
            recovery_emails.append(email)
```

### File Locations

| File | Action |
|------|--------|
| `Core/plugins/holehe.py` | CREATE |
| `tests/plugins/test_holehe_plugin.py` | CREATE |

### Project Structure Notes

- Pattern: follow `hibp.py` cho class structure và `PluginResult` format
- `stage = 2` attribute phải được set (dùng bởi `StageRouter` trong Story 9.2)
- `tos_risk` attribute cần cho Story 9.6 (ToS summary display)
- Plugin auto-discovery trong `PluginManager.discover_plugins()` sẽ tìm thấy class này tự động

### References

- Existing plugin pattern: `Core/plugins/hibp.py`
- Plugin protocol: `Core/plugins/base.py`
- StageRouter (Story 9.2): `Core/engine/stage_router.py`
- holehe library: https://github.com/megadose/holehe
- PRD FR3-FR4 (multi-source coverage, recovery data): `_bmad-output/planning-artifacts/prd-epic9.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No issues encountered. All 16 tests passed on first run.

### Completion Notes List

- Implemented `HolehPlugin` following exact pattern from `hibp.py`
- `_run_holehe_sync()` module-level function bridges holehe's trio-based async to asyncio via `run_in_executor`
- `ImportError` from holehe/trio is caught inside `run_in_executor` and re-raised, then caught in `check()` for graceful fallback
- `extract_clues()` filters masked values (containing `*`) for both phones and emails
- 16 unit tests covering all ACs: class attrs, check() success/failure, non-EMAIL target, ImportError fallback, exception handling, extract_clues() with full/masked/mixed/empty data

### File List

- `Core/plugins/holehe.py` (created)
- `tests/plugins/test_holehe_plugin.py` (created)

### Review Findings

- [x] [Review][Patch] P3: Replace `asyncio.get_event_loop()` with `asyncio.get_running_loop()` to avoid DeprecationWarning [`Core/plugins/holehe.py:79`] — FIXED
