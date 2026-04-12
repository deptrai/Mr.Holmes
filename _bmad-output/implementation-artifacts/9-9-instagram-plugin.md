# Story 9.9: InstagramPlugin

Status: ready-for-dev

## Story

As an OSINT analyst,
I want to extract Instagram bio, avatar, and geo-tagged post data via Instaloader (opt-in),
so that I can enrich Golden Record with location and visual identity data.

## Acceptance Criteria

1. `InstagramPlugin` class tại `Core/plugins/instagram.py` implement `IntelligencePlugin` protocol:
   - `name: str = "Instagram"`
   - `requires_api_key: bool = False`
   - `stage: int = 2`
   - `tos_risk: str = "ban_risk"` — Instaloader gửi authenticated requests, ban risk cao

2. Opt-in gate:
   - Plugin chỉ chạy nếu env `MH_INSTAGRAM_ENABLED=1` được set
   - Nếu không: return `PluginResult(is_success=False, error_message="Instagram plugin disabled. Set MH_INSTAGRAM_ENABLED=1 to enable.")`
   - Story 9.6 CLI sẽ hỏi user confirmation trước khi set enabled — plugin không tự prompt

3. `check(target: str, target_type: str) -> PluginResult`:
   - Chỉ xử lý `target_type == "USERNAME"` — return failure cho type khác
   - Chạy Instaloader qua subprocess: `instaloader --no-pictures --no-videos --no-metadata-json --no-captions {username}`
   - Timeout: 120 giây
   - Parse stdout/stderr để extract profile info
   - Trả về `PluginResult` với `data`:
     ```json
     {
       "username": "target_user",
       "full_name": "Nguyen Van A",
       "bio": "DJ/Producer | Ho Chi Minh City",
       "avatar_url": "https://instagram.com/...",
       "followers": 1234,
       "following": 456,
       "post_count": 89,
       "is_private": false,
       "locations": ["Ho Chi Minh City", "Hanoi"],
       "profile_url": "https://instagram.com/target_user"
     }
     ```
   - Private account → return partial data với `"is_private": true`

4. Graceful fallback:
   - `shutil.which("instaloader")` không tìm thấy → return failure với install hint
   - 429 / rate limit trong subprocess stderr → stop immediately, return partial data + warning
   - Subprocess timeout → return partial data nếu có, failure nếu không

5. Rate limit safety:
   - Class-level `asyncio.Semaphore(1)` — max 1 Instagram request tại một thời điểm
   - Nếu request fails với rate limit pattern trong stderr → set class-level flag `_rate_limited = True` và skip future calls trong session

6. Unit tests tại `tests/plugins/test_instagram_plugin.py` ≥ 80% coverage:
   - Test với `MH_INSTAGRAM_ENABLED` không set → graceful disabled
   - Test Instaloader not installed → graceful failure
   - Test non-USERNAME target → failure PluginResult
   - Test successful parse (mock subprocess output)
   - Test private account detection

## Tasks / Subtasks

- [ ] Task 1: Tạo `Core/plugins/instagram.py` với skeleton + opt-in gate (AC: 1, 2)
- [ ] Task 2: Implement `check()` với subprocess (AC: 3, 4)
  - [ ] `shutil.which("instaloader")` check
  - [ ] `asyncio.create_subprocess_exec` với timeout
  - [ ] Parse stdout cho profile data
- [ ] Task 3: Rate limit safety (AC: 5)
  - [ ] Class-level semaphore và `_rate_limited` flag
- [ ] Task 4: Viết unit tests (AC: 6)

## Dev Notes

### Instaloader Command & Output

```bash
instaloader --no-pictures --no-videos --no-metadata-json --no-captions --no-compress-json {username}
```

Output thường là text đến stdout/stderr. Parse defensively — format có thể thay đổi theo version.

**Alternative: Instaloader Python API** (tránh subprocess, nhưng phức tạp hơn vì blocking):
```python
import instaloader
L = instaloader.Instaloader()
profile = instaloader.Profile.from_username(L.context, username)
# profile.full_name, profile.biography, profile.followers, profile.is_private
```
Nếu dùng Python API: wrap trong `loop.run_in_executor` để tránh blocking event loop.

**Recommendation:** Dùng Python API trực tiếp qua `run_in_executor` — reliable hơn subprocess, dễ parse hơn.

### Rate Limit Detection

Instaloader thường raise `instaloader.exceptions.QueryReturnedBadRequestException` hoặc log "429 Too Many Requests" khi bị rate limit.

### File Locations

| File | Action |
|------|--------|
| `Core/plugins/instagram.py` | CREATE |
| `tests/plugins/test_instagram_plugin.py` | CREATE |

### References

- Plugin pattern: `Core/plugins/maigret.py` (subprocess pattern)
- Instaloader docs: https://instaloader.github.io/
- PRD FR10, FR33: Instagram opt-in, ban risk

## Dev Agent Record

### Agent Model Used
### Debug Log References
### Completion Notes List
### File List
- `Core/plugins/instagram.py` (created)
- `tests/plugins/test_instagram_plugin.py` (created)
