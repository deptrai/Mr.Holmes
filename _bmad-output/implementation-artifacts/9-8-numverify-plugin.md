# Story 9.8: NumverifyPlugin

Status: ready-for-dev

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

- [ ] Task 1: Tạo `Core/plugins/numverify.py` với skeleton (AC: 1)
- [ ] Task 2: Implement `check()` với phone normalization (AC: 2, 3)
  - [ ] `re.sub(r"[^\d+]", "", phone)` normalization
  - [ ] aiohttp GET với timeout
  - [ ] Parse JSON response
- [ ] Task 3: Viết unit tests (AC: 4)

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
### Debug Log References
### Completion Notes List
### File List
- `Core/plugins/numverify.py` (created)
- `tests/plugins/test_numverify_plugin.py` (created)
