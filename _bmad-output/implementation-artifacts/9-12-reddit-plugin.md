# Story 9.12: RedditPlugin

Status: ready-for-dev

## Story

As an OSINT analyst,
I want to analyze a Reddit username's post history and subreddit activity via PRAW,
so that I can infer interests, writing style, and behavioral patterns.

## Acceptance Criteria

1. `RedditPlugin` class tại `Core/plugins/reddit.py` implement `IntelligencePlugin` protocol:
   - `name: str = "Reddit"`
   - `requires_api_key: bool = True` (Reddit API credentials required)
   - `stage: int = 2`
   - `tos_risk: str = "safe"` (chỉ đọc public data)

2. Credentials từ env:
   - `MH_REDDIT_CLIENT_ID`, `MH_REDDIT_CLIENT_SECRET`, `MH_REDDIT_USER_AGENT`
   - Nếu thiếu → return failure với hướng dẫn tạo Reddit app

3. `check(target: str, target_type: str) -> PluginResult`:
   - Chỉ xử lý `"USERNAME"` — failure cho type khác
   - Query last 100 submissions + 100 comments
   - Trả về `PluginResult` với `data`:
     ```json
     {
       "username": "u/target",
       "account_age_days": 1823,
       "total_karma": 4521,
       "subreddits": ["r/programming", "r/vietnam", "r/DJs"],
       "top_topics": ["Python", "music production", "Vietnam"],
       "post_times": ["22:00", "23:30", "00:15"],
       "writing_samples": ["sample text 1...", "sample text 2..."],
       "account_deleted": false
     }
     ```
   - `writing_samples`: lấy tối đa 5 đoạn text (body ≥ 50 chars), truncate 200 chars mỗi đoạn

4. PRAW bridge — PRAW sử dụng synchronous API:
   - Wrap trong `loop.run_in_executor(None, sync_fn, username)`

5. Rate limiting: Reddit public API cho phép 60 req/min với OAuth — PRAW tự handle

6. Graceful fallback:
   - `ImportError` cho praw → return failure
   - Deleted/suspended account → return `{"account_deleted": true}`, `is_success=True`

7. Unit tests tại `tests/plugins/test_reddit_plugin.py` ≥ 80% coverage:
   - Mock PRAW Redditor object → correct data extracted
   - Test deleted account detection
   - Test missing credentials → graceful failure
   - Test non-USERNAME type → failure PluginResult

## Tasks / Subtasks

- [ ] Task 1: Tạo `Core/plugins/reddit.py` (AC: 1, 2)
- [ ] Task 2: Implement `check()` với PRAW bridge (AC: 3, 4, 5)
  - [ ] `run_in_executor` wrapper
  - [ ] Parse submissions + comments
  - [ ] Extract subreddits, post times, writing samples
- [ ] Task 3: Graceful fallbacks (AC: 6)
- [ ] Task 4: Viết unit tests (AC: 7)

## Dev Notes

### PRAW Pattern

```python
import praw
import concurrent.futures

def _fetch_reddit_sync(username: str, client_id: str, secret: str, user_agent: str) -> dict:
    reddit = praw.Reddit(client_id=client_id, client_secret=secret, user_agent=user_agent)
    try:
        redditor = reddit.redditor(username)
        # Access any attribute to trigger fetch; raises NotFound if deleted
        _ = redditor.id
    except Exception as e:
        if "NOT_FOUND" in str(e).upper() or "suspended" in str(e).lower():
            return {"account_deleted": True}
        raise

    submissions = list(redditor.submissions.new(limit=100))
    comments = list(redditor.comments.new(limit=100))
    # ...extract and return data
```

### File Locations

| File | Action |
|------|--------|
| `Core/plugins/reddit.py` | CREATE |
| `tests/plugins/test_reddit_plugin.py` | CREATE |
| `requirements.txt` | MODIFY — thêm `praw` |

### References

- Plugin pattern: `Core/plugins/hibp.py`
- PRD FR11: interests + writing patterns từ Reddit

## Dev Agent Record

### Agent Model Used
### Debug Log References
### Completion Notes List
### File List
- `Core/plugins/reddit.py` (created)
- `tests/plugins/test_reddit_plugin.py` (created)
- `requirements.txt` (modified)
