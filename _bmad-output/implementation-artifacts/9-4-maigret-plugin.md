# Story 9.4: MaigretPlugin

Status: done

## Story

As an OSINT analyst,
I want to scan a username across 3000+ sites via Maigret,
so that I can discover profiles and extract real names, bios, and avatar URLs for Golden Record enrichment.

## Acceptance Criteria

1. `MaigretPlugin` class tại `Core/plugins/maigret.py` implement `IntelligencePlugin` protocol:
   - `name: str = "Maigret"`
   - `requires_api_key: bool = False`
   - `stage: int = 2`
   - `tos_risk: str = "safe"` (chỉ kiểm tra URL existence, không gửi dữ liệu)

2. `check(target: str, target_type: str) -> PluginResult`:
   - Chỉ xử lý `target_type == "USERNAME"` — return failure PluginResult cho type khác
   - Chạy maigret qua `asyncio.create_subprocess_exec` với JSON output
   - Command: `maigret {username} --json {output_file} --timeout 30 --no-color`
   - Parse JSON output → list of discovered profiles
   - Subprocess timeout: 300 giây (maigret quét 3000+ sites → chậm)
   - Trả về `PluginResult` với `data`:
     ```json
     {
       "profiles": [
         {
           "site": "GitHub",
           "url": "https://github.com/username",
           "name": "Nguyen Van A",
           "bio": "Python developer",
           "avatar_url": "https://avatars.github.com/...",
           "email": "user@example.com"
         }
       ],
       "total_found": 45,
       "total_checked": 3000
     }
     ```

3. Graceful fallback khi maigret không installed / timeout:
   - Kiểm tra `shutil.which("maigret")` — nếu không có, return `PluginResult(is_success=False, error_message="maigret not found. Run: pip install maigret")`
   - Subprocess timeout → return partial results nếu có, hoặc failure với message "Maigret timed out after 300s"
   - Non-zero exit code → return failure PluginResult với stderr excerpt

4. Temporary file management:
   - Tạo temp file với `tempfile.mktemp(suffix='.json')` cho JSON output
   - Cleanup trong `finally` block — xóa temp file dù thành công hay fail

5. `extract_clues(result: PluginResult) -> list[tuple[str, str]]`:
   - Parse `result.data["profiles"]` → extract `email` field từ mỗi profile
   - Return `[("email@example.com", "EMAIL"), ...]` — bỏ qua empty/None emails

6. Unit tests tại `tests/plugins/test_maigret_plugin.py` ≥ 80% coverage:
   - Test `check()` với mock subprocess output (valid JSON) → correct PluginResult
   - Test `check()` khi maigret không installed (`shutil.which` returns None) → graceful failure
   - Test `check()` với subprocess timeout → failure PluginResult
   - Test `check()` với non-USERNAME target → failure PluginResult
   - Test `extract_clues()` → chỉ valid emails được include
   - Test JSON parse error (malformed output) → failure PluginResult, no exception propagated

## Tasks / Subtasks

- [x] Task 1: Tạo `Core/plugins/maigret.py` với skeleton (AC: 1)
  - [x] Class attributes: `name`, `requires_api_key`, `stage`, `tos_risk`

- [x] Task 2: Implement `check()` với subprocess execution (AC: 2, 3, 4)
  - [x] `shutil.which("maigret")` check → graceful failure nếu không có
  - [x] `tempfile.mktemp(suffix='.json')` cho output path
  - [x] `asyncio.create_subprocess_exec("maigret", ...)` với `asyncio.wait_for` timeout
  - [x] Parse JSON output từ temp file
  - [x] Build `PluginResult` với profiles list
  - [x] `finally: os.unlink(temp_file)` cleanup

- [x] Task 3: Implement `extract_clues()` (AC: 5)
  - [x] Extract emails từ profiles list
  - [x] Filter None/empty strings

- [x] Task 4: Viết unit tests (AC: 6)
  - [x] `tests/plugins/test_maigret_plugin.py`
  - [x] Mock `asyncio.create_subprocess_exec` và `shutil.which`

## Dev Notes

### Maigret Command & JSON Format

```bash
# Recommended invocation
maigret username --json /tmp/output.json --timeout 30 --no-color --folderoutput /tmp/maigret_out
```

**Maigret JSON output format** (thay đổi theo version, parse defensively):
```json
{
  "username": "targetuser",
  "sites": {
    "GitHub": {
      "status": {"status": "Claimed"},
      "url_user": "https://github.com/targetuser",
      "extra": {
        "fullname": "Nguyen Van A",
        "bio": "Python developer",
        "img": "https://avatars.github.com/..."
      }
    }
  }
}
```

**Parsing pattern:**
```python
data = json.loads(output_path.read_text())
sites = data.get("sites", {})
profiles = []
for site_name, site_data in sites.items():
    status = site_data.get("status", {}).get("status", "")
    if status == "Claimed":
        extra = site_data.get("extra", {}) or {}
        profiles.append({
            "site": site_name,
            "url": site_data.get("url_user", ""),
            "name": extra.get("fullname", ""),
            "bio": extra.get("bio", ""),
            "avatar_url": extra.get("img", ""),
            "email": extra.get("email", ""),
        })
```

### Subprocess Execution Pattern

```python
import asyncio
import shutil
import tempfile
import os
import json
from pathlib import Path

async def check(self, target, target_type):
    if target_type.upper() != "USERNAME":
        return PluginResult(plugin_name=self.name, is_success=False, data={},
                            error_message=f"Maigret only supports USERNAME, got {target_type}")

    if not shutil.which("maigret"):
        return PluginResult(plugin_name=self.name, is_success=False, data={},
                            error_message="maigret not found. Run: pip install maigret")

    tmp = tempfile.mktemp(suffix='.json')
    try:
        proc = await asyncio.create_subprocess_exec(
            "maigret", target, "--json", tmp, "--timeout", "30", "--no-color",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        except asyncio.TimeoutError:
            proc.kill()
            return PluginResult(plugin_name=self.name, is_success=False, data={},
                                error_message="Maigret timed out after 300s")

        if proc.returncode != 0:
            return PluginResult(plugin_name=self.name, is_success=False, data={},
                                error_message=f"maigret exit {proc.returncode}: {stderr.decode()[:200]}")

        # Parse JSON output
        output_data = json.loads(Path(tmp).read_text())
        profiles = _parse_maigret_output(output_data)
        return PluginResult(plugin_name=self.name, is_success=True, data={
            "profiles": profiles,
            "total_found": len(profiles),
        })
    except json.JSONDecodeError as e:
        return PluginResult(plugin_name=self.name, is_success=False, data={},
                            error_message=f"Failed to parse maigret JSON output: {e}")
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
```

### Python Version Note

Maigret yêu cầu Python ≥ 3.10 nhưng Mr.Holmes hỗ trợ 3.9+. Subprocess isolation giải quyết conflict này — maigret chạy trong subprocess với Python version của nó, không conflict với Mr.Holmes process.

Nếu `maigret` CLI không available nhưng user có Python 3.10+ virtualenv, document cách install:
```
pip install maigret  # requires Python >= 3.10
```

### File Locations

| File | Action |
|------|--------|
| `Core/plugins/maigret.py` | CREATE |
| `tests/plugins/test_maigret_plugin.py` | CREATE |

### Project Structure Notes

- Pattern: follow `hibp.py` cho class structure, nhưng dùng subprocess thay vì aiohttp
- `stage = 2` — MaigretPlugin được route bởi `StageRouter` khi seed là USERNAME
- `tos_risk = "safe"` — chỉ check URL existence, no POST requests
- Không cần API key — auto-registered bởi `PluginManager.discover_plugins()`

### References

- Existing plugin pattern: `Core/plugins/hibp.py`
- Plugin protocol: `Core/plugins/base.py`
- StageRouter (Story 9.2): `Core/engine/stage_router.py`
- maigret library: https://github.com/soxoj/maigret
- PRD FR5-FR6 (3000+ site coverage, profile extraction): `_bmad-output/planning-artifacts/prd-epic9.md`

## Dev Agent Record

### Agent Model Used

claude-sonnet-4-6

### Debug Log References

No issues encountered. All 19 tests passed on first run.

### Completion Notes List

- Implemented `MaigretPlugin` as plain class (not Protocol subclass) following `hibp.py` pattern
- Used class-level attributes for `name`, `requires_api_key`, `stage`, `tos_risk`
- `_parse_maigret_output()` extracted as module-level helper for clarity and testability
- `check()` handles: wrong target_type, missing maigret binary, subprocess timeout, non-zero exit code, JSON parse errors, missing output file — all as graceful PluginResult failures
- `extract_clues()` returns empty list for failed results (defensive `data.get("profiles", [])`)
- TDD approach: tests written first, then implementation

### File List

- `Core/plugins/maigret.py` (created)
- `tests/plugins/test_maigret_plugin.py` (created)

### Review Findings

- [x] [Review][Patch] P2 HIGH: Replace `tempfile.mktemp()` (TOCTOU race) with `NamedTemporaryFile(delete=False)` [`Core/plugins/maigret.py:59`] — FIXED
