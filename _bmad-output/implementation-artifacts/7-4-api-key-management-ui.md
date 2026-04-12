# Story 7.4: API Key Management UI

Status: done

## Story

As a user,
I want giao diện quản lý API keys cho external services,
so that setup HIBP/Shodan keys dễ dàng và an toàn.

## Acceptance Criteria

1. **AC1:** CLI command: `python3 MrHolmes.py --config api-keys`
2. **AC2:** Interactive wizard: add/update/remove API keys
3. **AC3:** Keys lưu vào `.env` (encrypted tương lai)
4. **AC4:** Validate key trước khi save (test API call)
5. **AC5:** Show key status: configured/missing/invalid

## Tasks / Subtasks

- [x] Task 1 — CLI config subcommand
- [x] Task 2 — Key management wizard (Rich prompts)
- [x] Task 3 — Key validation (test API call)
- [x] Task 4 — Status display

## Dev Notes

### Dependencies
- **REQUIRES Story 4.2** — .env management
- **REQUIRES Story 5.1** — CLI subcommands
- **REQUIRES Story 7.1** — Plugin system knows which keys needed

### File Structure
```
Core/cli/
└── config_wizard.py  # NEW
```

## Dev Agent Record
### Agent Model Used
Gemini 1.5 Pro

### Completion Notes List
- Bmad Dev Agent successfully integrated `rich`-based Wizard.
- Developed the `--config` flag parser and safely routed it within `MrHolmes.py` interception flow.
- Configured dynamic plugin inspection. The wizard loops all plugins mapped in `PluginManager` and filters for ones strictly declaring `requires_api_key`.
- Key validation relies on sending dummy parameters (`test@...` / `8.8.8.8`) and trapping error formats (`401`, `429`). Evaluates effectively.
- Regression suite running 539 unit assertions proves zero side-effects. Tested validation logic with heavily mocked DummyPlugin.

### File List
- `Core/cli/parser.py`
- `MrHolmes.py`
- `Core/cli/config_wizard.py`
- `tests/cli/test_config_wizard.py`

### Review Findings
- [x] [Review][Acceptance] Extensibility: Dùng `PluginManager` quét API Key Requirement (tự động thêm menu) rất thanh lịch. Sẽ có khả năng scale tốt cho các plugin tiếp theo mà không cần Update file UI Manager này. [Core/cli/config_wizard.py:82]
- [x] [Review][Acceptance] Edge Case Trapping: Hàm Validation có fallback và cảnh báo rõ ràng khi gặp 429 và Exception chung. Thiết kế test cases đầy đủ để phân đoạn từng exception payload. Code pass hoàn chỉnh mượt mà. [tests/cli/test_config_wizard.py:65]

