# Deferred Work

Items deferred from code reviews. Not blockers — tracked for future attention.

## Deferred from: code review of story 1-1 (2026-03-27)

- **D1:** Path fields (`report_path`, `json_output_path`, `json_names_path`) dùng `str` thay vì `pathlib.Path` → Deferred to Story 1.3
- **D2:** Không có `__post_init__` validation trên dataclasses (empty target, invalid subject_type, negative concurrency_limit) → Deferred to Story 1.7
- **D3:** Exception chaining (`raise ... from original_error`) chưa được implement trong OSINTError hierarchy → Deferred to Story 2.4
- **D4:** `exceptions.py` đạt 160 LOC, gần giới hạn 200 LOC → Split nếu cần thêm exceptions ở stories sau

## Deferred from: code review of story 1-2 (2026-03-27)

- **D1:** JSON output O(n²) write pattern (re-open/re-dump mỗi element) → Story 3.x refactor JSON output
- **D2:** `open(report, "a")` không specify encoding → Story 1.6 context managers

## Deferred from: code review of story 1-5 (2026-03-27)

- **D1:** ip-api.com rate limiting (45 req/min free tier) — pre-existing, cần rate-limit/cache ở Epic 3
- **D2:** `Proxies.py` class-level side-effects — `random.choice` chạy at import time, không thể refresh proxy → Epic 3 ProxyManager rotation
- **D3:** Empty proxy config file → `random.choice([])` raises `IndexError` at import time → Epic 3 validation

## Deferred from: code review of story 9-6 (2026-04-05)

- **D1:** `detect_seed_type()` không nhận IP/DOMAIN — chỉ detect EMAIL/PHONE/USERNAME per AC1. Cần mở rộng khi có plugin cho IP/DOMAIN seed.
- **D2:** `asyncio.run()` trong existing event loop — pre-existing pattern từ Story 8.4. Cần refactor nếu embed vào async framework.
- **D3:** Option 16 thiếu label trong `english.json` / lang files — Menu.py route `sce==16` hoạt động, nhưng lang file chưa updated.
- **D4:** `_build_profile_entity()` không extract emails/phones — chưa có plugin nào trả email/phone data mới. Thêm khi có plugin phù hợp (e.g., Story 9.14 Hunter).
- **D5:** Thiếu unit test cho StagedProfiler routing trong `_run_async()` — routing logic đã covered trong Story 9.2 test suite.

## Deferred from: code review of story 9-7 (2026-04-05)

- **D1:** Bot filter `endswith("[bot]")` — spec sample code dùng cùng pattern. Mở rộng khi cần cover thêm bot variants (renovate, snyk, codecov).
- **D2:** Mỗi `check()` call tạo `aiohttp.ClientSession` mới — pre-existing pattern chung cho tất cả plugins (HIBP cũng vậy). Refactor khi có session pooling story.
- **D3:** `extract_clues()` chỉ extract emails — AC5 chỉ yêu cầu email. Thêm `real_names` clue type khi base protocol hỗ trợ.
- **D4:** 403 error message ghép chung "rate limit or access denied" — cần parse response body để differentiate. Minor UX improvement.

## Deferred from: code review of story 9-17 (2026-04-06)

- **D1:** `X-RateLimit-Reset` header non-integer → `int()` raises `ValueError` uncaught trong `_get_json`. Pre-existing từ 9.7.
- **D2:** Commit `author` / `item["commit"]` có thể không phải dict nếu GitHub API trả malformed JSON → AttributeError. Pre-existing từ 9.7.
- **D3:** `_check_email` trả input email trong `data["emails"]` mà không filter noreply domains. Feature scope.
- **D4:** `_BOT_PATTERNS` chưa cover `web-flow`, `semantic-release-bot`, `allcontributors[bot]`. Mở rộng incremental khi cần.
- **D5:** `extract_clues` map `real_names` → `"USERNAME"` type — full names như "Alice Smith" có thể bị BFS route vào username plugins và 404. Cần review BFS clue type design.
