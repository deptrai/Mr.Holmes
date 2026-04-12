# Story 9.8: NumverifyPlugin

Status: done

## Story

As an OSINT analyst,
I want to verify and enrich phone numbers discovered from Holehe recovery data via Numverify,
so that I can confirm phone validity and learn carrier/region information.

## Acceptance Criteria

1. `NumverifyPlugin` class tại `Core/plugins/numverify.py` implement `IntelligencePlugin` protocol:
   - `name: str = "Numverify"`
   - `requires_api_key: bool = True`
   - `stage: int = 3`
   - `tos_risk: str = "safe"`

2. `check(target: str, target_type: str) -> PluginResult`:
   - Chỉ xử lý `target_type == "PHONE"` — return failure PluginResult cho type khác
   - Đọc `MH_NUMVERIFY_API_KEY` từ env — nếu thiếu, return failure với hướng dẫn
   - Normalize phone: strip non-digit chars ngoại trừ leading `+`
   - API call: `GET http://apilayer.net/api/validate?access_key={key}&number={phone}`
   - Trả về `PluginResult` với `data`:
     ```json
     {
       "valid": true,
       "number": "+84928881690",
       "local_format": "0928881690",
       "international_format": "+84928881690",
       "country_prefix": "+84",
       "country_code": "VN",
       "country_name": "Vietnam",
       "location": "Ho Chi Minh City",
       "carrier": "Mobifone",
       "line_type": "mobile"
     }
     ```

3. Graceful handling:
   - `valid: false` từ API → return `PluginResult(is_success=True, data={"valid": false, ...})` — không phải lỗi, là kết quả hợp lệ
   - API error (non-200, rate limit) → return failure PluginResult
   - Free tier giới hạn 100 lookups/month — không retry nếu 429

4. Unit tests tại `tests/plugins/test_numverify_plugin.py` ≥ 80% coverage:
   - Test valid phone → correct data parsed
   - Test invalid phone (API trả `valid: false`) → is_success=True với valid=false
   - Test missing API key → graceful failure
   - Test non-PHONE target type → failure PluginResult
   - Test API error (mock 429) → failure PluginResult

## Tasks / Subtasks

- [x] Task 1: Tạo `Core/plugins/numverify.py` với skeleton (AC: 1)
- [x] Task 2: Implement `check()` với phone normalization (AC: 2, 3)
  - [x] `re.sub(r"[^\d+]", "", phone)` normalization
  - [x] aiohttp GET với timeout
  - [x] Parse JSON response
- [x] Task 3: Viết unit tests (AC: 4)

### Review Findings

- [x] [Review][Patch] P1: Numverify API trả error JSON trong HTTP 200 — `success: false` không được detect, bị cached là success [`numverify.py:104`]
- [x] [Review][Patch] P2: Thiếu test cho non-200/non-429 HTTP status (e.g. 500) [`test_numverify_plugin.py`]
- [x] [Review][Fixed] W1: HTTP plaintext — thêm `logger.warning` cảnh báo user về cleartext [`numverify.py`]
- [x] [Review][Fixed] W2: Shared `aiohttp.ClientSession` — `get_http_session()` helper + PluginManager connection pooling across 6 plugins [`base.py`, `manager.py`, `hibp.py`, `shodan.py`, `github.py`, `leak_lookup.py`, `searxng.py`, `numverify.py`]
- [x] [Review][Fixed] W3: Cache key dùng raw phone — thêm `normalize_target()` hook vào PluginManager [`manager.py`, `numverify.py`]
- [x] [Review][Fixed] W4: `extract_clues()` stub — thêm explicit no-op method [`numverify.py`]
- [x] [Review][Fixed] W5: `discover_plugins()` — thêm `logger.warning` thay `pass` [`manager.py`]
- [x] [Review][Fixed] W6: `_print_progress_summary` — thêm `"stage"` key vào plugin_results (3 locations) [`autonomous_agent.py`]
- [x] [Review][Fixed] W7: Unicode/fullwidth digits — thêm `unicodedata.normalize("NFKC")` [`numverify.py`]
- [x] [Review][Fixed] W8: `detect_seed_type` mismatch — thêm comment documenting intent [`numverify.py`]

## Dev Notes

### Numverify API

```
GET http://apilayer.net/api/validate?access_key={key}&number={phone}&format=1
```

Free tier: 100 lookups/month, HTTP only (HTTPS requires paid). Use HTTP for free tier.

**Phone normalization:**
```python
import re
def _normalize_phone(phone: str) -> str:
    # Keep + prefix, strip everything else except digits
    normalized = re.sub(r"[^\d+]", "", phone.strip())
    return normalized if len(normalized) >= 7 else ""
```

### File Locations

| File | Action |
|------|--------|
| `Core/plugins/numverify.py` | CREATE |
| `tests/plugins/test_numverify_plugin.py` | CREATE |

### References

- Plugin pattern: `Core/plugins/hibp.py`
- StageRouter: stage=3 → PHONE type
- PRD FR9: xác minh SĐT từ Holehe recovery

## Dev Agent Record

### Agent Model Used

claude-opus-4-6

### Debug Log References

- `_normalize_phone("(+84)...")` → bug: `+` không ở đầu string khi có `(` prefix. Fix: dùng `re.sub(r"[^\d+]", "", ...)` rồi reconstruct leading `+`.
- Test `test_invalid_phone_response_is_success_true` dùng `"0000"` (4 chars, quá ngắn) → reject trước API. Fix: đổi sang `"00000000000"`.

### Completion Notes List

- `NumverifyPlugin` implements `IntelligencePlugin` protocol: `name="Numverify"`, `requires_api_key=True`, `stage=3`, `tos_risk="safe"`
- `_normalize_phone()`: strip all non-digit/non-plus → preserve leading `+` only → min 7 chars
- `check()`: target_type guard → API key guard → normalize → HTTP GET → parse JSON
- `valid=False` từ API → `is_success=True` (kết quả hợp lệ, không phải lỗi)
- 429/non-200 → failure PluginResult (no retry)
- 21 tests, 98% coverage

### File List

- `Core/plugins/numverify.py` (created)
- `tests/plugins/test_numverify_plugin.py` (created)
