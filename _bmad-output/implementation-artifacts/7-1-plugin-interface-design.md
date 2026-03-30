# Story 7.1: Plugin Interface Design

Status: done

## Story

As a developer,
I want to tạo Plugin Interface chuẩn cho external API integrations,
so that adding new intelligence sources (HIBP, Shodan, etc.) chỉ cần implement 1 interface.

## Acceptance Criteria

1. **AC1:** `IntelligencePlugin` Protocol tại `Core/plugins/base.py`
2. **AC2:** Methods: `name()`, `requires_api_key()`, `check(target, target_type) → PluginResult`
3. **AC3:** `PluginManager` — discover, load, execute plugins
4. **AC4:** Plugin results integrated vào ScanResultCollector
5. **AC5:** API key management via `.env`

## Tasks / Subtasks

- [ ] Task 1 — Define `IntelligencePlugin` Protocol
- [ ] Task 2 — Define `PluginResult` dataclass
- [ ] Task 3 — Implement `PluginManager`
- [ ] Task 4 — API key injection from Settings
- [ ] Task 5 — Unit tests with mock plugin

## Dev Notes

### Plugin Interface
```python
class IntelligencePlugin(Protocol):
    @property
    def name(self) -> str: ...
    @property
    def requires_api_key(self) -> bool: ...
    async def check(self, target: str, target_type: str) -> PluginResult: ...
```

### Dependencies
- **REQUIRES Story 4.2** — .env for API keys
- **REQUIRED BY Stories 7.2, 7.3, 7.4**

### File Structure
```
Core/plugins/
├── __init__.py   # NEW
├── base.py       # NEW — Protocol + PluginResult
└── manager.py    # NEW — PluginManager
```

## Dev Agent Record
### Agent Model Used
### Completion Notes List
### File List

### Review Findings
- [x] [Review][Patch] Status mapping bug — `is_success=True, data={}` maps to NOT_FOUND [Core/engine/result_collector.py:79]
- [x] [Review][Patch] `get_plugin_key` doesn't sanitize hyphens/dots → invalid env var names [Core/config/settings.py:186]
- [x] [Review][Patch] Duplicate plugin registration allowed — no dedup check [Core/plugins/manager.py:25]
- [x] [Review][Patch] `_safe_execute` — `plugin.name` can throw in error handler [Core/plugins/manager.py:44]
- [x] [Review][Patch] Redundant ternary `result.data if result.data else {}` [Core/engine/result_collector.py:80]
- [x] [Review][Patch] Unused `MagicMock` import [tests/plugins/test_plugins.py:9]
- [x] [Review][Patch] AC3: `discover_plugins()` method missing per spec [Core/plugins/manager.py]
- [x] [Review][Patch] Thin test coverage — add edge case tests for _safe_execute, empty plugins, status mapping [tests/plugins/test_plugins.py]
- [x] [Review][Defer] No logging in `_safe_execute` error path [Core/plugins/manager.py:44] — deferred, enhancement
- [x] [Review][Defer] Import coupling: result_collector ↔ plugins.base [Core/engine/result_collector.py:24] — deferred, architectural
