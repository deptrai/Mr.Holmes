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
