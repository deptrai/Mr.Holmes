# Story 9.13: YouTubePlugin

Status: ready-for-dev

## Story

As an OSINT analyst,
I want to analyze a YouTube channel by username to extract content themes, upload frequency, and bio data,
so that I can enrich the Golden Record with content creator identity signals.

## Acceptance Criteria

1. `YouTubePlugin` class tại `Core/plugins/youtube.py` implement `IntelligencePlugin` protocol:
   - `name: str = "YouTube"`
   - `requires_api_key: bool = True` (YouTube Data API v3)
   - `stage: int = 2`
   - `tos_risk: str = "safe"`

2. Credentials: `MH_YOUTUBE_API_KEY` từ env — nếu thiếu, return failure

3. `check(target: str, target_type: str) -> PluginResult`:
   - Chỉ xử lý `"USERNAME"` — failure cho type khác
   - Search channel: `GET /search?part=snippet&q={username}&type=channel&maxResults=5`
   - Lấy channel details: `GET /channels?part=snippet,statistics&id={channel_id}`
   - Trả về `PluginResult` với `data`:
     ```json
     {
       "channel_name": "Nguyen Van A",
       "channel_id": "UCxxxxxx",
       "description": "DJ/Producer from Vietnam",
       "subscriber_count": 12500,
       "view_count": 450000,
       "video_count": 89,
       "country": "VN",
       "custom_url": "@nguyenvana",
       "topics": ["Music", "Entertainment"],
       "channel_url": "https://youtube.com/channel/UCxxxxxx"
     }
     ```
   - Nếu không tìm thấy channel → `is_success=True, data={"found": false}`

4. Chỉ query 2 API calls per target (search + channel details) — tránh quota exhaustion (YouTube API có quota 10,000 units/day)

5. Unit tests tại `tests/plugins/test_youtube_plugin.py` ≥ 80% coverage:
   - Test channel found → correct data parsed
   - Test channel not found → `{"found": false}`
   - Test missing API key → graceful failure
   - Test non-USERNAME type → failure PluginResult

## Tasks / Subtasks

- [ ] Task 1: Tạo `Core/plugins/youtube.py` (AC: 1, 2)
- [ ] Task 2: Implement `check()` với YouTube Data API (AC: 3, 4)
  - [ ] Search channel by username
  - [ ] Fetch channel details
  - [ ] Parse statistics + snippet
- [ ] Task 3: Viết unit tests (AC: 5)

## Dev Notes

### YouTube Data API v3

```
Base: https://www.googleapis.com/youtube/v3

# Step 1: Find channel ID
GET /search?part=snippet&q={username}&type=channel&maxResults=5&key={api_key}

# Step 2: Get channel details
GET /channels?part=snippet,statistics,topicDetails&id={channel_id}&key={api_key}
```

**Topics** từ `topicDetails.topicCategories` — URLs như `https://en.wikipedia.org/wiki/Music` → extract last path segment.

### File Locations

| File | Action |
|------|--------|
| `Core/plugins/youtube.py` | CREATE |
| `tests/plugins/test_youtube_plugin.py` | CREATE |

### References

- Plugin pattern: `Core/plugins/hibp.py`
- YouTube Data API: https://developers.google.com/youtube/v3
- PRD FR13: YouTube channel analysis

## Dev Agent Record

### Agent Model Used
### Debug Log References
### Completion Notes List
### File List
- `Core/plugins/youtube.py` (created)
- `tests/plugins/test_youtube_plugin.py` (created)
