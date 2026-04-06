# Story 9.7: GitHubPlugin

Status: done

## Story

As an OSINT analyst,
I want to look up real names and emails from GitHub profiles and commit history,
so that I can confirm identity with high confidence using publicly verifiable data.

## Acceptance Criteria

1. `GitHubPlugin` class tại `Core/plugins/github.py` implement `IntelligencePlugin` protocol:
   - `name: str = "GitHub"`
   - `requires_api_key: bool = False` (public API; token optional, boosts rate limit)
   - `stage: int = 2`
   - `tos_risk: str = "safe"`

2. `check(target: str, target_type: str) -> PluginResult`:
   - Hỗ trợ `"USERNAME"` → query `GET /users/{username}` + `GET /users/{username}/events/public`
   - Hỗ trợ `"EMAIL"` → query `GET /search/commits?q=author-email:{email}` (requires `Accept: application/vnd.github.cloak-preview`)
   - Trả về `PluginResult` với `data`:
     ```json
     {
       "username": "deptraidapxichlo",
       "profile_url": "https://github.com/deptraidapxichlo",
       "real_names": ["Nguyen Van A"],
       "emails": ["user@example.com"],
       "bio": "Python developer",
       "avatar_url": "https://avatars.github.com/...",
       "location": "Ho Chi Minh City",
       "company": "FPT Software",
       "public_repos": 12,
       "followers": 45
     }
     ```
   - Return failure PluginResult cho type khác (IP, DOMAIN, PHONE)

3. Authentication:
   - Đọc `MH_GITHUB_TOKEN` từ env — nếu có, thêm `Authorization: Bearer {token}` header
   - Không có token → vẫn chạy, nhưng rate limit là 60 req/hour
   - 403 Forbidden hoặc rate limit → return failure với clear message

4. Rate limiting:
   - Check `X-RateLimit-Remaining` response header
   - Nếu `remaining == 0` → sleep đến `X-RateLimit-Reset` timestamp rồi retry (1 lần)
   - Max wait: 60 giây — nếu reset time > 60s, return failure thay vì block

5. `extract_clues(result: PluginResult) -> list[tuple[str, str]]`:
   - Extract emails từ `result.data["emails"]` → `[("email", "EMAIL"), ...]`

6. Unit tests tại `tests/plugins/test_github_plugin.py` ≥ 80% coverage:
   - Test USERNAME lookup → correct profile data parsed
   - Test EMAIL search → commit author names/emails extracted
   - Test rate limit handling (mock 403 + `X-RateLimit-Reset` header)
   - Test without API token → still runs, correct auth header omitted
   - Test unsupported target type → failure PluginResult

## Tasks / Subtasks

- [x] Task 1: Tạo `Core/plugins/github.py` với skeleton (AC: 1)
- [x] Task 2: Implement `check()` cho USERNAME path (AC: 2)
  - [x] `GET /users/{username}` — extract name, bio, location, company, avatar_url
  - [x] `GET /users/{username}/events/public` — scan PushEvents cho commit emails
- [x] Task 3: Implement `check()` cho EMAIL path (AC: 2)
  - [x] `GET /search/commits?q=author-email:{email}` — extract author names
- [x] Task 4: Auth + rate limit handling (AC: 3, 4)
- [x] Task 5: Implement `extract_clues()` (AC: 5)
- [x] Task 6: Viết unit tests (AC: 6)

## Dev Notes

### GitHub API Endpoints

```python
BASE_URL = "https://api.github.com"

# USERNAME path
profile_url = f"{BASE_URL}/users/{username}"
events_url  = f"{BASE_URL}/users/{username}/events/public?per_page=100"

# EMAIL path — requires special Accept header
search_url  = f"{BASE_URL}/search/commits?q=author-email:{email}&per_page=10"
headers["Accept"] = "application/vnd.github.cloak-preview+json"
```

**Events parsing** (tìm real names từ commit history):
```python
for event in events:
    if event.get("type") == "PushEvent":
        for commit in event.get("payload", {}).get("commits", []):
            author = commit.get("author", {})
            name = author.get("name", "")
            email = author.get("email", "")
            if name and not name.endswith("[bot]"):
                names.add(name)
            if email and "@" in email and "noreply" not in email:
                emails.add(email)
```

### File Locations

| File | Action |
|------|--------|
| `Core/plugins/github.py` | CREATE |
| `tests/plugins/test_github_plugin.py` | CREATE |

### References

- Plugin pattern: `Core/plugins/hibp.py`
- GitHub REST API docs: https://docs.github.com/en/rest
- PRD FR8: tên thật từ GitHub commit history

## Dev Agent Record

### Agent Model Used
claude-sonnet-4-6

### Debug Log References
No issues. All 28 tests passed on first implementation run.

### Completion Notes List

- `GitHubPlugin` class implements `IntelligencePlugin` protocol: `name="GitHub"`, `requires_api_key=False`, `stage=2`, `tos_risk="safe"`
- `check("user", "USERNAME")` → fetches `/users/{username}` profile + `/users/{username}/events/public` for commit emails/names
- `check("email@x.com", "EMAIL")` → fetches `/search/commits?q=author-email:{email}` with `vnd.github.cloak-preview` Accept header
- Bot names (ending `[bot]`) and `noreply` emails filtered from output
- Token: `api_key` param → `MH_GITHUB_TOKEN` env → unauthenticated (60 req/hr)
- Rate limit: X-RateLimit-Remaining=0 → sleep until reset (if ≤60s), else return failure
- `extract_clues()` → `[(email, "EMAIL"), ...]` from `result.data["emails"]`

### Review Findings

- [x] [Review][Patch] P1: Rate limit retry chỉ trên 429, không vứt response 200 ✅ Fixed
- [x] [Review][Patch] P2: Giữ CIMultiDictProxy cho case-insensitive header lookup ✅ Fixed
- [x] [Review][Patch] P3: `response.json(content_type=None)` chống ContentTypeError ✅ Fixed
- [x] [Review][Patch] P4: `aiohttp.ClientTimeout(total=30)` trên mọi request ✅ Fixed
- [x] [Review][Patch] P5: `urllib.parse.quote(email)` trong search URL ✅ Fixed
- [x] [Review][Patch] P6: Check events status, gắn `_events_partial` flag khi rate-limited ✅ Fixed
- [x] [Review][Patch] P7: noreply filter check `_NOREPLY_DOMAINS` frozenset ✅ Fixed
- [x] [Review][Patch] P8: +4 tests: EMAIL 403, network exception USERNAME/EMAIL ✅ Fixed
- [x] [Review][Defer] D1: Bot filter endswith("[bot]") — matches spec sample code — deferred
- [x] [Review][Defer] D2: Mỗi check tạo ClientSession mới — pre-existing pattern — deferred
- [x] [Review][Defer] D3: extract_clues chỉ extract emails — AC5 chỉ yêu cầu email — deferred
- [x] [Review][Defer] D4: 403 message ghép chung rate limit + access denied — deferred, minor UX

### File List
- `Core/plugins/github.py` (created)
- `tests/plugins/test_github_plugin.py` (created)
