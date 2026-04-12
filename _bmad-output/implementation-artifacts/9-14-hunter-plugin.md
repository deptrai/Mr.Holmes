# Story 9.14: HunterPlugin

Status: ready-for-dev

## Story

As an OSINT analyst,
I want to discover email addresses associated with a domain via Hunter.io,
so that I can find corporate email patterns and potential contacts for identity verification.

## Acceptance Criteria

1. `HunterPlugin` class tại `Core/plugins/hunter.py` implement `IntelligencePlugin` protocol:
   - `name: str = "Hunter"`
   - `requires_api_key: bool = True`
   - `stage: int = 3`
   - `tos_risk: str = "safe"`

2. Credentials: `MH_HUNTER_API_KEY` từ env — nếu thiếu, return failure

3. `check(target: str, target_type: str) -> PluginResult`:
   - Chỉ xử lý `"DOMAIN"` — failure cho type khác
   - API: `GET https://api.hunter.io/v2/domain-search?domain={domain}&api_key={key}&limit=10`
   - Trả về `PluginResult` với `data`:
     ```json
     {
       "domain": "fpt.com.vn",
       "organization": "FPT Corporation",
       "email_pattern": "{first}.{last}@fpt.com.vn",
       "emails": [
         {"value": "nguyen.vana@fpt.com.vn", "confidence": 87, "type": "personal"},
         {"value": "info@fpt.com.vn", "confidence": 100, "type": "generic"}
       ],
       "total_emails_found": 45
     }
     ```
   - Free tier: 25 searches/month — không retry trên rate limit

4. `extract_clues(result: PluginResult) -> list[tuple[str, str]]`:
   - Extract email values với confidence ≥ 70 → `[("email", "EMAIL"), ...]`
   - Bỏ qua generic emails (`info@`, `contact@`, `admin@`, `support@`)

5. Unit tests tại `tests/plugins/test_hunter_plugin.py` ≥ 80% coverage:
   - Test domain search → correct emails extracted
   - Test `extract_clues()` filters generic emails + low confidence
   - Test missing API key → graceful failure
   - Test non-DOMAIN type → failure PluginResult

## Tasks / Subtasks

- [ ] Task 1: Tạo `Core/plugins/hunter.py` (AC: 1, 2)
- [ ] Task 2: Implement `check()` (AC: 3)
- [ ] Task 3: Implement `extract_clues()` (AC: 4)
- [ ] Task 4: Viết unit tests (AC: 5)

## Dev Notes

### Generic Email Filter

```python
_GENERIC_PREFIXES = {"info", "contact", "admin", "support", "hello",
                     "team", "sales", "help", "noreply", "no-reply"}

def _is_generic(email: str) -> bool:
    prefix = email.split("@")[0].lower()
    return prefix in _GENERIC_PREFIXES
```

### File Locations

| File | Action |
|------|--------|
| `Core/plugins/hunter.py` | CREATE |
| `tests/plugins/test_hunter_plugin.py` | CREATE |

### References

- Plugin pattern: `Core/plugins/hibp.py`
- Hunter.io API: https://hunter.io/api-documentation
- PRD FR12: email discovery từ domain

## Dev Agent Record

### Agent Model Used
### Debug Log References
### Completion Notes List
### File List
- `Core/plugins/hunter.py` (created)
- `tests/plugins/test_hunter_plugin.py` (created)
